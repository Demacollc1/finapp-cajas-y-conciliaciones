"""Endpoints del envío físico de cheques posfechados al banco."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import schemas, services
from ..database import get_db
from ..services import NoEncontradaError, ReglaNegocioError

router = APIRouter(prefix="/posfechados", tags=["Posfechados"])


@router.get(
    "/pendientes",
    response_model=list[schemas.ChequePosfechadoPendiente],
    summary="Cheques POSFECHADO pendientes de enviar al banco",
)
def listar_pendientes(db: Session = Depends(get_db)):
    return services.listar_posfechados_pendientes(db)


@router.post(
    "/remesas",
    response_model=schemas.RemesaPosfechadosOut,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar el envío físico de posfechados al banco (nº de transacción)",
)
def crear_remesa(datos: schemas.RemesaPosfechadosCreate, db: Session = Depends(get_db)):
    try:
        remesa = services.crear_remesa_posfechados(db, datos)
    except NoEncontradaError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    except ReglaNegocioError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    return schemas.RemesaPosfechadosOut.from_model(remesa)


@router.get(
    "/remesas",
    response_model=list[schemas.RemesaPosfechadosOut],
    summary="Listar remesas de posfechados enviadas al banco",
)
def listar_remesas(db: Session = Depends(get_db)):
    return [
        schemas.RemesaPosfechadosOut.from_model(r)
        for r in services.listar_remesas_posfechados(db)
    ]


@router.get(
    "/remesas/{remesa_id}",
    response_model=schemas.RemesaPosfechadosOut,
    summary="Detalle de una remesa de posfechados",
)
def obtener_remesa(remesa_id: int, db: Session = Depends(get_db)):
    try:
        remesa = services.obtener_remesa_posfechados(db, remesa_id)
    except NoEncontradaError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    return schemas.RemesaPosfechadosOut.from_model(remesa)


@router.post(
    "/remesas/{remesa_id}/transaccion",
    response_model=schemas.RemesaPosfechadosOut,
    summary="Capturar el número de transacción que devuelve el banco",
)
def registrar_transaccion(
    remesa_id: int, datos: schemas.TransaccionBancoIn, db: Session = Depends(get_db)
):
    try:
        remesa = services.registrar_transaccion_banco(
            db, remesa_id, datos.numero_transaccion_banco
        )
    except NoEncontradaError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    return schemas.RemesaPosfechadosOut.from_model(remesa)
