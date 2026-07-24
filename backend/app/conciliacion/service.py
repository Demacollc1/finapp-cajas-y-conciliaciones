"""Orquestación de la conciliación: perfiles, ejecución y aprobación."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..enums import EstadoMovimiento, OrigenMovimiento
from . import matcher, parser, schemas
from .models import Conciliacion, MovimientoConciliacion, PerfilBanco


class ConciliacionError(Exception):
    """Error de negocio en el módulo de conciliación."""


class NoEncontrado(Exception):
    """Recurso no encontrado."""


# --------------------------------------------------------------------------- #
#  Perfiles
# --------------------------------------------------------------------------- #
def crear_perfil(db: Session, datos: schemas.PerfilCreate) -> PerfilBanco:
    _validar_perfil(datos)
    if db.execute(select(PerfilBanco).where(PerfilBanco.nombre == datos.nombre)).scalar_one_or_none():
        raise ConciliacionError(f"Ya existe un perfil llamado '{datos.nombre}'.")
    perfil = PerfilBanco(**datos.model_dump())
    db.add(perfil)
    db.commit()
    db.refresh(perfil)
    return perfil


def actualizar_perfil(db: Session, perfil_id: int, datos: schemas.PerfilUpdate) -> PerfilBanco:
    _validar_perfil(datos)
    perfil = obtener_perfil(db, perfil_id)
    otro = db.execute(
        select(PerfilBanco).where(PerfilBanco.nombre == datos.nombre, PerfilBanco.id != perfil_id)
    ).scalar_one_or_none()
    if otro:
        raise ConciliacionError(f"Ya existe otro perfil llamado '{datos.nombre}'.")
    for campo, valor in datos.model_dump().items():
        setattr(perfil, campo, valor)
    db.commit()
    db.refresh(perfil)
    return perfil


def eliminar_perfil(db: Session, perfil_id: int) -> None:
    perfil = obtener_perfil(db, perfil_id)
    db.delete(perfil)
    db.commit()


def obtener_perfil(db: Session, perfil_id: int) -> PerfilBanco:
    perfil = db.get(PerfilBanco, perfil_id)
    if perfil is None:
        raise NoEncontrado(f"Perfil {perfil_id} no encontrado")
    return perfil


def listar_perfiles(db: Session, tipo=None) -> list[PerfilBanco]:
    stmt = select(PerfilBanco).order_by(PerfilBanco.tipo, PerfilBanco.nombre)
    if tipo is not None:
        stmt = stmt.where(PerfilBanco.tipo == tipo)
    return list(db.execute(stmt).scalars().all())


def _validar_perfil(datos: schemas.PerfilBase) -> None:
    if not datos.columna_monto and not (datos.columna_debito or datos.columna_credito):
        raise ConciliacionError(
            "Debe indicar 'columna_monto' o al menos una de 'columna_debito'/'columna_credito'."
        )


# --------------------------------------------------------------------------- #
#  Autodetección de perfil por columnas del archivo
# --------------------------------------------------------------------------- #
def detectar_perfil(db: Session, contenido: bytes, tipo) -> PerfilBanco | None:
    """Elige un perfil cuyas columnas mapeadas existan todas en el archivo."""
    info = parser.inspeccionar(contenido)
    columnas = set(info["columnas"])
    mejor, mejor_puntaje = None, -1
    for perfil in listar_perfiles(db, tipo=tipo):
        requeridas = [
            perfil.columna_fecha, perfil.columna_monto, perfil.columna_debito,
            perfil.columna_credito, perfil.columna_vinculacion, perfil.columna_referencia,
        ]
        requeridas = [c for c in requeridas if c]
        if not requeridas:
            continue
        if all(c in columnas for c in requeridas):
            puntaje = len(requeridas)
            if puntaje > mejor_puntaje:
                mejor, mejor_puntaje = perfil, puntaje
    return mejor


# --------------------------------------------------------------------------- #
#  Ejecución de la conciliación
# --------------------------------------------------------------------------- #
def ejecutar(
    db: Session,
    *,
    libro_bytes: bytes,
    libro_perfil: PerfilBanco,
    bancos: list[tuple[bytes, PerfilBanco]],
    tolerancia_dias: int = 3,
    comparar_absoluto: bool = True,
    descripcion: str | None = None,
) -> Conciliacion:
    mov_libro = parser.normalizar(libro_bytes, libro_perfil)
    mov_banco: list[dict] = []
    fuentes_banco: list[str] = []
    for contenido, perfil in bancos:
        normalizados = parser.normalizar(contenido, perfil)
        mov_banco.extend(normalizados)
        fuentes_banco.extend([perfil.nombre] * len(normalizados))

    resultado = matcher.conciliar(
        mov_libro, mov_banco,
        tolerancia_dias=tolerancia_dias,
        comparar_absoluto=comparar_absoluto,
    )

    conc = Conciliacion(
        descripcion=descripcion,
        fecha_ejecucion=datetime.now(),
        tolerancia_dias=tolerancia_dias,
        comparar_absoluto=comparar_absoluto,
    )
    db.add(conc)
    db.flush()  # obtener id

    # Crear filas de movimientos (libro y banco) y guardar referencias.
    filas_libro: list[MovimientoConciliacion] = []
    for m in mov_libro:
        filas_libro.append(_nuevo_mov(conc.id, OrigenMovimiento.LIBRO, libro_perfil.nombre, m))
    filas_banco: list[MovimientoConciliacion] = []
    for idx, m in enumerate(mov_banco):
        filas_banco.append(_nuevo_mov(conc.id, OrigenMovimiento.BANCO, fuentes_banco[idx], m))

    db.add_all(filas_libro + filas_banco)
    db.flush()  # obtener ids

    # Enlazar pares y fijar estados.
    for par in resultado["pares"]:
        ml = filas_libro[par["libro"]]
        mb = filas_banco[par["banco"]]
        estado = EstadoMovimiento(par["estado"])
        for mov, otro in ((ml, mb), (mb, ml)):
            mov.estado = estado
            mov.match_id = otro.id
            mov.motivo = par["motivo"]
            mov.score = par["score"]

    _recalcular(db, conc)
    db.commit()
    db.refresh(conc)
    return conc


def _nuevo_mov(conc_id, origen, fuente, m) -> MovimientoConciliacion:
    raw = m.get("raw")
    return MovimientoConciliacion(
        conciliacion_id=conc_id,
        origen=origen,
        fuente=fuente,
        fecha=m["fecha"],
        descripcion=(m["descripcion"] or "")[:300],
        referencia=(m["referencia"] or "")[:120],
        clave=(m["clave"] or "")[:120],
        monto=m["monto"],
        estado=EstadoMovimiento.NO_CONCILIADO,
        raw=raw if isinstance(raw, dict) else None,
    )


# --------------------------------------------------------------------------- #
#  Aprobación / rechazo de posibles
# --------------------------------------------------------------------------- #
def obtener_conciliacion(db: Session, conc_id: int) -> Conciliacion:
    conc = db.get(Conciliacion, conc_id)
    if conc is None:
        raise NoEncontrado(f"Conciliación {conc_id} no encontrada")
    return conc


def aprobar(db: Session, conc_id: int, mov_id: int) -> Conciliacion:
    conc = obtener_conciliacion(db, conc_id)
    mov, par = _par_de(db, conc, mov_id, exigir=EstadoMovimiento.POSIBLE)
    for m in (mov, par):
        m.estado = EstadoMovimiento.CONCILIADO
        m.motivo = "Aprobado manualmente"
    _recalcular(db, conc)
    db.commit()
    db.refresh(conc)
    return conc


def rechazar(db: Session, conc_id: int, mov_id: int) -> Conciliacion:
    conc = obtener_conciliacion(db, conc_id)
    mov, par = _par_de(db, conc, mov_id, exigir=EstadoMovimiento.POSIBLE)
    for m in (mov, par):
        m.estado = EstadoMovimiento.NO_CONCILIADO
        m.match_id = None
        m.motivo = "Rechazado manualmente"
        m.score = None
    _recalcular(db, conc)
    db.commit()
    db.refresh(conc)
    return conc


def _par_de(db: Session, conc: Conciliacion, mov_id: int, exigir=None):
    mov = db.get(MovimientoConciliacion, mov_id)
    if mov is None or mov.conciliacion_id != conc.id:
        raise NoEncontrado(f"Movimiento {mov_id} no pertenece a la conciliación {conc.id}")
    if exigir is not None and mov.estado != exigir:
        raise ConciliacionError(
            f"El movimiento {mov_id} no está en estado {exigir.value}."
        )
    if not mov.match_id:
        raise ConciliacionError(f"El movimiento {mov_id} no tiene contraparte.")
    par = db.get(MovimientoConciliacion, mov.match_id)
    if par is None:
        raise ConciliacionError("La contraparte del movimiento no existe.")
    return mov, par


# --------------------------------------------------------------------------- #
#  Recalculo de totales y armado del detalle
# --------------------------------------------------------------------------- #
def _recalcular(db: Session, conc: Conciliacion) -> None:
    movs = list(conc.movimientos)
    libro = [m for m in movs if m.origen == OrigenMovimiento.LIBRO]
    banco = [m for m in movs if m.origen == OrigenMovimiento.BANCO]

    conc.total_libro = len(libro)
    conc.total_banco = len(banco)
    conc.conciliados = sum(
        1 for m in libro if m.estado == EstadoMovimiento.CONCILIADO
    )
    conc.posibles = sum(1 for m in libro if m.estado == EstadoMovimiento.POSIBLE)
    conc.no_conciliados_libro = sum(
        1 for m in libro if m.estado == EstadoMovimiento.NO_CONCILIADO
    )
    conc.no_conciliados_banco = sum(
        1 for m in banco if m.estado == EstadoMovimiento.NO_CONCILIADO
    )

    def suma(items):
        return sum((abs(m.monto) for m in items), Decimal("0"))

    conc.monto_conciliado = suma(
        [m for m in libro if m.estado == EstadoMovimiento.CONCILIADO]
    )
    conc.monto_posible = suma([m for m in libro if m.estado == EstadoMovimiento.POSIBLE])
    conc.monto_no_conciliado_libro = suma(
        [m for m in libro if m.estado == EstadoMovimiento.NO_CONCILIADO]
    )
    conc.monto_no_conciliado_banco = suma(
        [m for m in banco if m.estado == EstadoMovimiento.NO_CONCILIADO]
    )


def construir_detalle(db: Session, conc: Conciliacion) -> schemas.DetalleConciliacion:
    movs = {m.id: m for m in conc.movimientos}
    conciliados, posibles = [], []
    no_libro, no_banco = [], []

    for m in conc.movimientos:
        if m.origen != OrigenMovimiento.LIBRO:
            continue
        if m.estado in (EstadoMovimiento.CONCILIADO, EstadoMovimiento.POSIBLE) and m.match_id:
            banco_mov = movs.get(m.match_id)
            if banco_mov is None:
                continue
            par = schemas.ParConciliado(
                estado=m.estado, motivo=m.motivo, score=m.score,
                libro=schemas.MovimientoOut.model_validate(m),
                banco=schemas.MovimientoOut.model_validate(banco_mov),
            )
            (conciliados if m.estado == EstadoMovimiento.CONCILIADO else posibles).append(par)
        elif m.estado == EstadoMovimiento.NO_CONCILIADO:
            no_libro.append(schemas.MovimientoOut.model_validate(m))

    for m in conc.movimientos:
        if m.origen == OrigenMovimiento.BANCO and m.estado == EstadoMovimiento.NO_CONCILIADO:
            no_banco.append(schemas.MovimientoOut.model_validate(m))

    return schemas.DetalleConciliacion(
        resumen=schemas.ResumenConciliacion.model_validate(conc),
        conciliados=conciliados,
        posibles=posibles,
        no_conciliados_libro=no_libro,
        no_conciliados_banco=no_banco,
    )
