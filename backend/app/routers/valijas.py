"""Endpoints de valijas: creación, consulta y transiciones de estado."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from .. import schemas, services
from ..database import get_db
from ..enums import EstadoValija
from ..services import NoEncontradaError, ReglaNegocioError

router = APIRouter(prefix="/valijas", tags=["Valijas"])


@router.post(
    "",
    response_model=schemas.ValijaOut,
    status_code=status.HTTP_201_CREATED,
    summary="Crear un cierre de caja (nace en estado ENVIADA)",
)
def crear_valija(datos: schemas.ValijaCreate, db: Session = Depends(get_db)):
    try:
        valija = services.crear_valija(db, datos)
    except ReglaNegocioError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    return schemas.ValijaOut.from_model(valija)


@router.get(
    "",
    response_model=list[schemas.ValijaOut],
    summary="Listar valijas (con filtros por estado, usuario o búsqueda de ID)",
)
def listar_valijas(
    estado: EstadoValija | None = Query(default=None),
    usuario: str | None = Query(default=None),
    buscar: str | None = Query(default=None, description="Búsqueda parcial por ID"),
    db: Session = Depends(get_db),
):
    valijas = services.listar_valijas(db, estado=estado, usuario=usuario, buscar=buscar)
    return [schemas.ValijaOut.from_model(v) for v in valijas]


@router.get(
    "/{valija_id}",
    response_model=schemas.ValijaOut,
    summary="Obtener el detalle de una valija",
)
def obtener_valija(valija_id: str, db: Session = Depends(get_db)):
    try:
        valija = services.obtener_valija(db, valija_id)
    except NoEncontradaError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    return schemas.ValijaOut.from_model(valija)


@router.get(
    "/{valija_id}/qr",
    response_model=schemas.QrPayload,
    summary="Generar el payload QR para el traspaso al mensajero",
)
def obtener_qr(valija_id: str, db: Session = Depends(get_db)):
    try:
        services.obtener_valija(db, valija_id)
    except NoEncontradaError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    return services.qr_payload(valija_id)


@router.get(
    "/{valija_id}/manifiesto",
    response_model=schemas.ManifiestoOut,
    summary="Datos del manifiesto de depósito (papeleta banco + custodia matriz)",
)
def obtener_manifiesto(valija_id: str, db: Session = Depends(get_db)):
    try:
        return services.manifiesto(db, valija_id)
    except NoEncontradaError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc


@router.post(
    "/{valija_id}/custodia",
    response_model=schemas.ValijaOut,
    summary="Traspaso ENVIADA -> CUSTODIA (validación QR del mensajero)",
)
def traspasar_custodia(
    valija_id: str,
    datos: schemas.TraspasoCustodiaIn,
    db: Session = Depends(get_db),
):
    try:
        valija = services.traspasar_a_custodia(db, valija_id, datos)
    except NoEncontradaError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    except ReglaNegocioError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    return schemas.ValijaOut.from_model(valija)


@router.post(
    "/{valija_id}/deposito",
    response_model=schemas.ValijaOut,
    summary="Cierre CUSTODIA -> DEPOSITADA (papeleta sellada + asiento ERP)",
)
def confirmar_deposito(
    valija_id: str,
    datos: schemas.DepositoBancoIn,
    db: Session = Depends(get_db),
):
    try:
        valija = services.confirmar_deposito(db, valija_id, datos)
    except NoEncontradaError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    except ReglaNegocioError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    return schemas.ValijaOut.from_model(valija)
