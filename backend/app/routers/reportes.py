"""Endpoints de reportes: KPIs, papeleta bancaria y consolidado de matriz."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from .. import schemas, services
from ..database import get_db
from ..enums import EstadoValija

router = APIRouter(prefix="/reportes", tags=["Reportes"])


@router.get(
    "/kpis",
    response_model=schemas.KpisOut,
    summary="Indicadores del dashboard (efectivo, custodia, posfechados...)",
)
def obtener_kpis(db: Session = Depends(get_db)):
    return services.kpis(db)


@router.get(
    "/banco",
    response_model=schemas.ReporteBancoOut,
    summary="Reporte para el banco: efectivo + cheques ESTANDAR",
)
def reporte_banco(
    estado: EstadoValija | None = Query(
        default=None, description="Filtrar por estado de valija"
    ),
    db: Session = Depends(get_db),
):
    return services.reporte_banco(db, estado=estado)


@router.get(
    "/matriz",
    response_model=schemas.ReporteMatrizOut,
    summary="Consolidado de cheques POSFECHADO para envío a Matriz",
)
def reporte_matriz(db: Session = Depends(get_db)):
    return services.reporte_matriz(db)
