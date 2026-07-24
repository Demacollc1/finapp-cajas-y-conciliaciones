"""Endpoints de integración con Tableau (ventas) y ERP (asiento contable)."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from .. import schemas, services
from ..database import get_db
from ..services import NoEncontradaError, ReglaNegocioError

router = APIRouter(prefix="/integraciones", tags=["Integraciones"])


@router.get(
    "/tableau/ventas",
    response_model=schemas.VentasTableauOut,
    summary="Traer las ventas del sistema desde Tableau",
)
def ventas_tableau(
    dia: date = Query(default_factory=date.today, description="Fecha a consultar"),
):
    return services.ventas_tableau(dia)


@router.get(
    "/tableau/conciliacion",
    response_model=schemas.ConciliacionOut,
    summary="Conciliar lo declarado en caja contra las ventas de Tableau",
)
def conciliacion_tableau(
    dia: date = Query(default_factory=date.today),
    db: Session = Depends(get_db),
):
    return services.conciliar_con_tableau(db, dia)


@router.post(
    "/erp/asiento/{valija_id}",
    response_model=schemas.AsientoErpOut,
    summary="Registrar el asiento contable de una valija depositada en el ERP",
)
def registrar_asiento(valija_id: str, db: Session = Depends(get_db)):
    try:
        return services.registrar_asiento_erp(db, valija_id)
    except NoEncontradaError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    except ReglaNegocioError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
