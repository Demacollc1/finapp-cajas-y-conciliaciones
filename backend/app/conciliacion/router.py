"""Endpoints del módulo de conciliación de cuentas."""

from fastapi import (
    APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status,
)
from sqlalchemy.orm import Session

from ..database import get_db
from ..enums import TipoPerfil
from . import parser, schemas, service
from .service import ConciliacionError, NoEncontrado

router = APIRouter(prefix="/conciliacion", tags=["Conciliación"])


# --------------------------------------------------------------------------- #
#  Perfiles (entrenamiento)
# --------------------------------------------------------------------------- #
@router.post(
    "/perfiles/inspeccionar",
    response_model=schemas.InspeccionOut,
    summary="Inspeccionar un CSV para entrenar un perfil (columnas + muestra)",
)
async def inspeccionar_csv(
    archivo: UploadFile = File(...),
    delimitador: str | None = Form(default=None),
    filas_omitir: int = Form(default=0),
):
    contenido = await archivo.read()
    return parser.inspeccionar(
        contenido, delimitador=delimitador or None, filas_omitir=filas_omitir
    )


@router.post(
    "/perfiles",
    response_model=schemas.PerfilOut,
    status_code=status.HTTP_201_CREATED,
    summary="Crear un perfil de mapeo (entrenamiento inicial de un banco/JDE)",
)
def crear_perfil(datos: schemas.PerfilCreate, db: Session = Depends(get_db)):
    try:
        return service.crear_perfil(db, datos)
    except ConciliacionError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc


@router.get("/perfiles", response_model=list[schemas.PerfilOut], summary="Listar perfiles")
def listar_perfiles(
    tipo: TipoPerfil | None = Query(default=None), db: Session = Depends(get_db)
):
    return service.listar_perfiles(db, tipo=tipo)


@router.get("/perfiles/{perfil_id}", response_model=schemas.PerfilOut, summary="Detalle de perfil")
def obtener_perfil(perfil_id: int, db: Session = Depends(get_db)):
    try:
        return service.obtener_perfil(db, perfil_id)
    except NoEncontrado as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc


@router.put("/perfiles/{perfil_id}", response_model=schemas.PerfilOut, summary="Actualizar perfil")
def actualizar_perfil(perfil_id: int, datos: schemas.PerfilUpdate, db: Session = Depends(get_db)):
    try:
        return service.actualizar_perfil(db, perfil_id, datos)
    except NoEncontrado as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    except ConciliacionError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc


@router.delete(
    "/perfiles/{perfil_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar perfil",
)
def eliminar_perfil(perfil_id: int, db: Session = Depends(get_db)):
    try:
        service.eliminar_perfil(db, perfil_id)
    except NoEncontrado as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc


# --------------------------------------------------------------------------- #
#  Ejecución de la conciliación
# --------------------------------------------------------------------------- #
@router.post(
    "/ejecutar",
    response_model=schemas.DetalleConciliacion,
    summary="Cruzar un CSV de JDE contra uno o más CSV de bancos",
)
async def ejecutar_conciliacion(
    libro_archivo: UploadFile = File(..., description="CSV de JD Edwards (libros)"),
    banco_archivos: list[UploadFile] = File(..., description="Uno o más CSV de bancos"),
    libro_perfil_id: int = Form(...),
    banco_perfil_ids: str | None = Form(
        default=None,
        description="IDs de perfil por banco, separados por coma y alineados a los "
                    "archivos. Si se omite, se autodetecta por columnas.",
    ),
    tolerancia_dias: int = Form(default=3),
    comparar_absoluto: bool = Form(default=True),
    descripcion: str | None = Form(default=None),
    db: Session = Depends(get_db),
):
    try:
        libro_perfil = service.obtener_perfil(db, libro_perfil_id)
    except NoEncontrado as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc

    # Resolver el perfil de cada banco (explícito o autodetectado).
    ids_explicitos: list[int] = []
    if banco_perfil_ids:
        try:
            ids_explicitos = [int(x) for x in banco_perfil_ids.split(",") if x.strip()]
        except ValueError as exc:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "banco_perfil_ids debe ser una lista de enteros separados por coma.",
            ) from exc

    bancos: list[tuple[bytes, object]] = []
    for idx, archivo in enumerate(banco_archivos):
        contenido = await archivo.read()
        if idx < len(ids_explicitos):
            try:
                perfil = service.obtener_perfil(db, ids_explicitos[idx])
            except NoEncontrado as exc:
                raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
        else:
            perfil = service.detectar_perfil(db, contenido, TipoPerfil.BANCO)
            if perfil is None:
                raise HTTPException(
                    status.HTTP_422_UNPROCESSABLE_ENTITY,
                    f"No se pudo autodetectar un perfil para el archivo "
                    f"'{archivo.filename}'. Entrénelo o indique banco_perfil_ids.",
                )
        bancos.append((contenido, perfil))

    libro_bytes = await libro_archivo.read()
    try:
        conc = service.ejecutar(
            db,
            libro_bytes=libro_bytes,
            libro_perfil=libro_perfil,
            bancos=bancos,
            tolerancia_dias=tolerancia_dias,
            comparar_absoluto=comparar_absoluto,
            descripcion=descripcion,
        )
    except ConciliacionError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    return service.construir_detalle(db, conc)


# --------------------------------------------------------------------------- #
#  Consulta, aprobación y rechazo
# --------------------------------------------------------------------------- #
@router.get(
    "",
    response_model=list[schemas.ResumenConciliacion],
    summary="Listar corridas de conciliación",
)
def listar_conciliaciones(db: Session = Depends(get_db)):
    from sqlalchemy import select

    from .models import Conciliacion
    filas = db.execute(
        select(Conciliacion).order_by(Conciliacion.creado_en.desc())
    ).scalars().all()
    return list(filas)


@router.get(
    "/{conc_id}",
    response_model=schemas.DetalleConciliacion,
    summary="Detalle de una corrida (conciliados, posibles y no conciliados)",
)
def detalle_conciliacion(conc_id: int, db: Session = Depends(get_db)):
    try:
        conc = service.obtener_conciliacion(db, conc_id)
    except NoEncontrado as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    return service.construir_detalle(db, conc)


@router.post(
    "/{conc_id}/movimientos/{mov_id}/aprobar",
    response_model=schemas.DetalleConciliacion,
    summary="Aprobar una posible conciliación (pasa a CONCILIADO)",
)
def aprobar_posible(conc_id: int, mov_id: int, db: Session = Depends(get_db)):
    try:
        conc = service.aprobar(db, conc_id, mov_id)
    except NoEncontrado as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    except ConciliacionError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    return service.construir_detalle(db, conc)


@router.post(
    "/{conc_id}/movimientos/{mov_id}/rechazar",
    response_model=schemas.DetalleConciliacion,
    summary="Rechazar una posible conciliación (vuelve a NO_CONCILIADO)",
)
def rechazar_posible(conc_id: int, mov_id: int, db: Session = Depends(get_db)):
    try:
        conc = service.rechazar(db, conc_id, mov_id)
    except NoEncontrado as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    except ConciliacionError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    return service.construir_detalle(db, conc)
