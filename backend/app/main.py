"""Punto de entrada de la API FinancePro (FastAPI)."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import __version__
from .config import settings
from .database import SessionLocal, init_db
from .routers import integraciones, reportes, valijas
from .seed import seed


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Arranque: crear tablas y (opcionalmente) sembrar datos de demostración.
    init_db()
    if settings.seed_on_startup:
        with SessionLocal() as db:
            seed(db)
    yield


app = FastAPI(
    title=settings.app_name,
    version=__version__,
    description=(
        "Backend del sistema de Control de Caja, Valijas y Custodia (FinancePro).\n\n"
        "**Ciclo de estados:** ENVIADA → CUSTODIA (QR mensajero) → DEPOSITADA "
        "(papeleta sellada).\n\n"
        "**Segregación de cheques:** ESTANDAR → banco · POSFECHADO → Matriz.\n\n"
        "**Integraciones:** Tableau (ventas) · ERP (asiento contable con # de valija)."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers versionados bajo el prefijo de la API.
app.include_router(valijas.router, prefix=settings.api_prefix)
app.include_router(reportes.router, prefix=settings.api_prefix)
app.include_router(integraciones.router, prefix=settings.api_prefix)


@app.get("/", tags=["Sistema"], summary="Información del servicio")
def raiz():
    return {
        "servicio": settings.app_name,
        "version": __version__,
        "docs": "/docs",
        "estado": "operativo",
    }


@app.get("/health", tags=["Sistema"], summary="Health check")
def health():
    return {"status": "ok"}
