"""Capa de servicios: reglas de negocio sobre valijas, cheques y reportes."""

from __future__ import annotations

import hashlib
import hmac
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import schemas
from .config import settings
from .enums import EstadoValija, TipoCheque, transicion_permitida
from .integrations.erp import erp_client
from .integrations.tableau import tableau_client
from .models import Cheque, RemesaPosfechados, Valija


class ReglaNegocioError(Exception):
    """Error de regla de negocio (se traduce a HTTP 4xx en el router)."""


class NoEncontradaError(Exception):
    """La valija solicitada no existe."""


# --------------------------------------------------------------------------- #
#  Identificadores y QR
# --------------------------------------------------------------------------- #
def generar_valija_id(db: Session) -> str:
    """Genera un ID 'VAL-XXXXXX' incremental y único."""
    ultimo = db.execute(
        select(Valija.id).order_by(Valija.creado_en.desc()).limit(1)
    ).scalar_one_or_none()
    if ultimo and ultimo.startswith("VAL-") and ultimo[4:].isdigit():
        siguiente = int(ultimo[4:]) + 1
    else:
        # Conteo base para no colisionar con la semilla.
        total = db.execute(select(Valija.id)).scalars().all()
        siguiente = 100000 + len(total)
    nuevo = f"VAL-{siguiente:06d}"
    while db.get(Valija, nuevo) is not None:
        siguiente += 1
        nuevo = f"VAL-{siguiente:06d}"
    return nuevo


def _texto_qr(valija_id: str) -> str:
    """Texto embebido en el QR (compatible con el front-end)."""
    return f"CUSTODY-TRANSFER-CONFIRMATION-{valija_id}"


def firmar_qr(valija_id: str) -> str:
    """Token HMAC que autentica el traspaso de custodia."""
    mensaje = _texto_qr(valija_id).encode()
    return hmac.new(settings.qr_secret.encode(), mensaje, hashlib.sha256).hexdigest()


def qr_payload(valija_id: str) -> schemas.QrPayload:
    return schemas.QrPayload(
        valija_id=valija_id,
        texto=_texto_qr(valija_id),
        token=firmar_qr(valija_id),
    )


def validar_qr(valija_id: str, token: str) -> bool:
    return hmac.compare_digest(firmar_qr(valija_id), token)


# --------------------------------------------------------------------------- #
#  Consultas
# --------------------------------------------------------------------------- #
def obtener_valija(db: Session, valija_id: str) -> Valija:
    valija = db.get(Valija, valija_id)
    if valija is None:
        raise NoEncontradaError(f"Valija {valija_id} no encontrada")
    return valija


def listar_valijas(
    db: Session,
    estado: EstadoValija | None = None,
    usuario: str | None = None,
    buscar: str | None = None,
) -> list[Valija]:
    stmt = select(Valija).order_by(Valija.creado_en.desc())
    if estado is not None:
        stmt = stmt.where(Valija.estado == estado)
    if usuario:
        stmt = stmt.where(Valija.usuario == usuario)
    if buscar:
        stmt = stmt.where(Valija.id.ilike(f"%{buscar.upper()}%"))
    return list(db.execute(stmt).scalars().all())


# --------------------------------------------------------------------------- #
#  Creación de valijas
# --------------------------------------------------------------------------- #
def _calcular_efectivo(nomenclaturas: list[schemas.Nomenclatura]) -> Decimal:
    return sum(
        (n.denominacion * n.cantidad for n in nomenclaturas), Decimal("0")
    ).quantize(Decimal("0.01"))


def crear_valija(db: Session, datos: schemas.ValijaCreate) -> Valija:
    """Crea una valija en estado ENVIADA."""
    efectivo_calc = _calcular_efectivo(datos.nomenclaturas)
    efectivo = datos.efectivo_total if datos.efectivo_total is not None else efectivo_calc

    # Si el cliente declara un total, debe cuadrar con el desglose (si lo hay).
    if (
        datos.efectivo_total is not None
        and datos.nomenclaturas
        and Decimal(datos.efectivo_total) != efectivo_calc
    ):
        raise ReglaNegocioError(
            f"efectivo_total ({datos.efectivo_total}) no coincide con la suma "
            f"de nomenclaturas ({efectivo_calc})."
        )

    valija_id = datos.valija_id or generar_valija_id(db)
    if db.get(Valija, valija_id) is not None:
        raise ReglaNegocioError(f"La valija {valija_id} ya existe.")

    valija = Valija(
        id=valija_id,
        fecha=datos.fecha or datetime.now(),
        usuario=datos.usuario,
        efectivo_total=efectivo,
        nomenclaturas=[
            {"denominacion": float(n.denominacion), "cantidad": n.cantidad}
            for n in datos.nomenclaturas
        ],
        pago_tarjeta=datos.pagos_adicionales.tarjeta,
        pago_de_una=datos.pagos_adicionales.de_una,
        pago_delivery=datos.pagos_adicionales.delivery,
        fondo_vuelto=datos.fondo_vuelto,
        estado=EstadoValija.ENVIADA,
        cheques=[
            Cheque(
                banco=c.banco,
                monto=c.monto,
                tipo=c.tipo,
                referencia=c.referencia,
            )
            for c in datos.cheques
        ],
    )
    db.add(valija)
    db.commit()
    db.refresh(valija)
    return valija


# --------------------------------------------------------------------------- #
#  Transiciones de estado
# --------------------------------------------------------------------------- #
def traspasar_a_custodia(
    db: Session, valija_id: str, datos: schemas.TraspasoCustodiaIn
) -> Valija:
    """ENVIADA -> CUSTODIA. Valida el token QR y registra al mensajero."""
    valija = obtener_valija(db, valija_id)
    if not transicion_permitida(valija.estado, EstadoValija.CUSTODIA):
        raise ReglaNegocioError(
            f"No se puede pasar a CUSTODIA desde {valija.estado.value}."
        )
    if not validar_qr(valija_id, datos.qr_token):
        raise ReglaNegocioError("Token QR inválido para el traspaso de custodia.")

    valija.estado = EstadoValija.CUSTODIA
    valija.mensajero = datos.mensajero
    valija.custodia_en = datetime.now()
    db.commit()
    db.refresh(valija)
    return valija


def confirmar_deposito(
    db: Session, valija_id: str, datos: schemas.DepositoBancoIn
) -> Valija:
    """CUSTODIA -> DEPOSITADA. Guarda el comprobante y registra el asiento ERP."""
    valija = obtener_valija(db, valija_id)
    if not transicion_permitida(valija.estado, EstadoValija.DEPOSITADA):
        raise ReglaNegocioError(
            f"No se puede pasar a DEPOSITADA desde {valija.estado.value}."
        )

    valija.estado = EstadoValija.DEPOSITADA
    valija.banco_deposito = datos.banco
    valija.comprobante_deposito = datos.comprobante
    valija.depositada_en = datetime.now()

    if datos.registrar_en_erp:
        resultado = erp_client.registrar_asiento(valija)
        valija.erp_asiento_id = resultado["asiento_id"]

    db.commit()
    db.refresh(valija)
    return valija


# --------------------------------------------------------------------------- #
#  Manifiesto (equivalente al PDF del front-end)
# --------------------------------------------------------------------------- #
def manifiesto(db: Session, valija_id: str) -> schemas.ManifiestoOut:
    v = obtener_valija(db, valija_id)
    return schemas.ManifiestoOut(
        valija_id=v.id,
        usuario=v.usuario,
        fecha=v.fecha,
        efectivo=v.efectivo_total,
        cheques_estandar_cantidad=len(v.cheques_estandar),
        cheques_estandar_total=v.total_estandar,
        monto_deposito_banco=v.monto_deposito_banco,
        cheques_posfechados_cantidad=len(v.cheques_posfechados),
        cheques_posfechados_total=v.total_posfechado,
        monto_custodia_matriz=v.monto_custodia_matriz,
    )


# --------------------------------------------------------------------------- #
#  Reportes y KPIs
# --------------------------------------------------------------------------- #
def kpis(db: Session) -> schemas.KpisOut:
    valijas = list(db.execute(select(Valija)).scalars().all())
    efectivo = sum((v.efectivo_total for v in valijas), Decimal("0"))
    vuelto = sum((v.fondo_vuelto for v in valijas), Decimal("0"))
    en_custodia = sum(1 for v in valijas if v.estado == EstadoValija.CUSTODIA)
    sin_confirmar = sum(1 for v in valijas if v.estado == EstadoValija.ENVIADA)
    posfechados = sum(
        1
        for v in valijas
        if v.estado != EstadoValija.DEPOSITADA
        and any(c.tipo == TipoCheque.POSFECHADO for c in v.cheques)
    )
    return schemas.KpisOut(
        efectivo_recibido=efectivo,
        caja_vuelto=vuelto,
        en_custodia=en_custodia,
        sin_confirmar_banco=sin_confirmar,
        posfechados_matriz=posfechados,
        total_valijas=len(valijas),
    )


def reporte_banco(
    db: Session, estado: EstadoValija | None = None
) -> schemas.ReporteBancoOut:
    """Consolida efectivo + cheques ESTANDAR (papeleta bancaria)."""
    valijas = listar_valijas(db, estado=estado)
    detalle = [
        schemas.LineaReporteBanco(
            valija_id=v.id,
            usuario=v.usuario,
            fecha=v.fecha,
            efectivo=v.efectivo_total,
            cheques_estandar=v.total_estandar,
            total_papeleta=v.monto_deposito_banco,
        )
        for v in valijas
    ]
    total_efectivo = sum((d.efectivo for d in detalle), Decimal("0"))
    total_estandar = sum((d.cheques_estandar for d in detalle), Decimal("0"))
    return schemas.ReporteBancoOut(
        generado_en=datetime.now(),
        cantidad_valijas=len(detalle),
        total_efectivo=total_efectivo,
        total_cheques_estandar=total_estandar,
        total_general=total_efectivo + total_estandar,
        detalle=detalle,
    )


def reporte_matriz(db: Session) -> schemas.ReporteMatrizOut:
    """Consolida los cheques POSFECHADO para envío a Matriz."""
    cheques = list(
        db.execute(
            select(Cheque)
            .where(Cheque.tipo == TipoCheque.POSFECHADO)
            .order_by(Cheque.valija_id)
        )
        .scalars()
        .all()
    )
    detalle = [
        schemas.LineaChequePosfechado(
            valija_id=c.valija_id,
            banco=c.banco,
            monto=c.monto,
            referencia=c.referencia,
        )
        for c in cheques
    ]
    total = sum((d.monto for d in detalle), Decimal("0"))
    return schemas.ReporteMatrizOut(
        generado_en=datetime.now(),
        cantidad_cheques=len(detalle),
        total_posfechado=total,
        detalle=detalle,
    )


# --------------------------------------------------------------------------- #
#  Integraciones
# --------------------------------------------------------------------------- #
def ventas_tableau(dia: date) -> schemas.VentasTableauOut:
    data = tableau_client.ventas_del_dia(dia)
    return schemas.VentasTableauOut(
        fuente=data["fuente"],
        fecha_consulta=data["fecha_consulta"],
        total_ventas=data["total_ventas"],
        ventas=[schemas.VentaTableau(**v) for v in data["ventas"]],
    )


def conciliar_con_tableau(db: Session, dia: date) -> schemas.ConciliacionOut:
    """Compara lo declarado en el día contra las ventas de Tableau."""
    inicio = datetime.combine(dia, datetime.min.time())
    fin = datetime.combine(dia, datetime.max.time())
    valijas = list(
        db.execute(
            select(Valija).where(Valija.fecha >= inicio, Valija.fecha <= fin)
        )
        .scalars()
        .all()
    )
    total_declarado = sum(
        (
            v.efectivo_total
            + v.pago_tarjeta
            + v.pago_de_una
            + v.pago_delivery
            for v in valijas
        ),
        Decimal("0"),
    )
    data = tableau_client.ventas_del_dia(dia)
    total_tableau = Decimal(str(data["total_ventas"]))
    diferencia = (total_declarado - total_tableau).quantize(Decimal("0.01"))
    return schemas.ConciliacionOut(
        fecha=inicio,
        total_declarado=total_declarado,
        total_tableau=total_tableau,
        diferencia=diferencia,
        cuadrado=diferencia == Decimal("0.00"),
    )


def listar_posfechados_pendientes(db: Session) -> list[schemas.ChequePosfechadoPendiente]:
    """Cheques POSFECHADO que aún no se han enviado en una remesa al banco."""
    stmt = (
        select(Cheque)
        .join(Valija, Cheque.valija_id == Valija.id)
        .where(Cheque.tipo == TipoCheque.POSFECHADO, Cheque.remesa_id.is_(None))
        .order_by(Valija.fecha)
    )
    cheques = db.execute(stmt).scalars().all()
    return [
        schemas.ChequePosfechadoPendiente(
            id=c.id,
            valija_id=c.valija_id,
            usuario=c.valija.usuario,
            fecha_valija=c.valija.fecha,
            banco=c.banco,
            monto=c.monto,
            referencia=c.referencia,
        )
        for c in cheques
    ]


def crear_remesa_posfechados(
    db: Session, datos: schemas.RemesaPosfechadosCreate
) -> RemesaPosfechados:
    """Registra el envío físico de cheques posfechados al banco."""
    cheques: list[Cheque] = []
    for cid in datos.cheque_ids:
        cheque = db.get(Cheque, cid)
        if cheque is None:
            raise NoEncontradaError(f"Cheque {cid} no encontrado.")
        if cheque.tipo != TipoCheque.POSFECHADO:
            raise ReglaNegocioError(f"El cheque {cid} no es POSFECHADO.")
        if cheque.remesa_id is not None:
            raise ReglaNegocioError(f"El cheque {cid} ya fue enviado en otra remesa.")
        cheques.append(cheque)

    numero = (datos.numero_transaccion_banco or "").strip() or None
    remesa = RemesaPosfechados(
        banco=datos.banco,
        fecha_envio=datos.fecha_envio or datetime.now(),
        usuario=datos.usuario or "Cajero_01",
        numero_transaccion_banco=numero,
        referencia_jde=(datos.referencia_jde or "").strip() or None,
        estado="CONFIRMADA" if numero else "REGISTRADA",
    )
    db.add(remesa)
    db.flush()
    for cheque in cheques:
        cheque.remesa_id = remesa.id
    db.commit()
    db.refresh(remesa)
    return remesa


def registrar_transaccion_banco(
    db: Session, remesa_id: int, numero: str
) -> RemesaPosfechados:
    """Captura el número de transacción que devuelve el banco."""
    remesa = db.get(RemesaPosfechados, remesa_id)
    if remesa is None:
        raise NoEncontradaError(f"Remesa {remesa_id} no encontrada.")
    remesa.numero_transaccion_banco = numero.strip()
    remesa.estado = "CONFIRMADA"
    db.commit()
    db.refresh(remesa)
    return remesa


def listar_remesas_posfechados(db: Session) -> list[RemesaPosfechados]:
    return list(
        db.execute(
            select(RemesaPosfechados).order_by(RemesaPosfechados.creado_en.desc())
        )
        .scalars()
        .all()
    )


def obtener_remesa_posfechados(db: Session, remesa_id: int) -> RemesaPosfechados:
    remesa = db.get(RemesaPosfechados, remesa_id)
    if remesa is None:
        raise NoEncontradaError(f"Remesa {remesa_id} no encontrada.")
    return remesa


def registrar_asiento_erp(db: Session, valija_id: str) -> schemas.AsientoErpOut:
    """Registra (o re-registra) el asiento contable de una valija en el ERP."""
    valija = obtener_valija(db, valija_id)
    if valija.estado != EstadoValija.DEPOSITADA:
        raise ReglaNegocioError(
            "Solo se registra el asiento de valijas DEPOSITADAS."
        )
    resultado = erp_client.registrar_asiento(valija)
    valija.erp_asiento_id = resultado["asiento_id"]
    db.commit()
    return schemas.AsientoErpOut(
        valija_id=valija.id,
        asiento_id=resultado["asiento_id"],
        estado=resultado["estado"],
        detalle=resultado["detalle"],
    )
