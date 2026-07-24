"""Configuración de SQLAlchemy: engine, sesión y base declarativa."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import settings

# SQLite necesita ``check_same_thread=False`` para usarse desde FastAPI.
connect_args = (
    {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
)

engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
    pool_pre_ping=True,
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    """Base declarativa de los modelos ORM."""


def get_db() -> Generator[Session, None, None]:
    """Dependencia de FastAPI que provee una sesión de base de datos."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Crea las tablas declaradas si no existen."""
    # Import local para registrar los modelos en la metadata antes de crear.
    from . import models  # noqa: F401
    from .conciliacion import models as conciliacion_models  # noqa: F401

    Base.metadata.create_all(bind=engine)
