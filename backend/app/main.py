"""Punto de entrada de la API FinancePro (FastAPI)."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from . import __version__
from .conciliacion.router import router as conciliacion_router
from .conciliacion.seed import seed_perfiles
from .config import settings
from .database import SessionLocal, init_db
from .routers import integraciones, posfechados, reportes, valijas
from .seed import seed


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Arranque: crear tablas y (opcionalmente) sembrar datos de demostración.
    init_db()
    if settings.seed_on_startup:
        with SessionLocal() as db:
            seed(db)
            seed_perfiles(db)
    yield


app = FastAPI(
    title=settings.app_name,
    version=__version__,
    description=(
        "Backend del sistema de Control de Caja, Valijas y Custodia (FinancePro).\n\n"
        "**Ciclo de estados:** ENVIADA → CUSTODIA (QR mensajero) → DEPOSITADA "
        "(papeleta sellada).\n\n"
        "**Segregación de cheques:** ESTANDAR → banco · POSFECHADO → Matriz.\n\n"
        "**Integraciones:** Tableau (ventas) · ERP (asiento contable con # de valija).\n\n"
        "**Conciliación:** cruce de JD Edwards vs. bancos con perfiles entrenables "
        "y aprobación humana de coincidencias posibles."
    ),
    lifespan=lifespan,
)

# El navegador no permite credenciales junto con orígenes "*"; se habilitan
# solo cuando se listan orígenes explícitos en CORS_ORIGINS.
_allow_credentials = settings.cors_origins != ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers versionados bajo el prefijo de la API.
app.include_router(valijas.router, prefix=settings.api_prefix)
app.include_router(reportes.router, prefix=settings.api_prefix)
app.include_router(integraciones.router, prefix=settings.api_prefix)
app.include_router(posfechados.router, prefix=settings.api_prefix)
app.include_router(conciliacion_router, prefix=settings.api_prefix)


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


# Sirve el front-end de referencia en /app cuando está disponible en el repo
# (en la imagen Docker solo se copia app/, por lo que este montaje se omite).
_frontend_dir = Path(__file__).resolve().parents[2] / "frontend"
if _frontend_dir.is_dir():
    app.mount("/app", StaticFiles(directory=_frontend_dir, html=True), name="frontend")
