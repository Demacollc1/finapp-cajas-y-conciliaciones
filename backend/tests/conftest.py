"""Configuración de pruebas: base de datos SQLite en memoria y cliente HTTP."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app


@pytest.fixture
def db_engine():
    # SQLite en memoria compartido entre conexiones para toda la prueba.
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session(db_engine):
    TestingSession = sessionmaker(bind=db_engine, autoflush=False, autocommit=False)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_engine):
    TestingSession = sessionmaker(bind=db_engine, autoflush=False, autocommit=False)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def valija_payload():
    """Payload de creación equivalente al JSON de ejemplo del proyecto."""
    return {
        "usuario": "Cajero_01",
        "fecha": "2026-05-11T09:15:32",
        "nomenclaturas": [
            {"denominacion": 20.00, "cantidad": 15},
            {"denominacion": 10.00, "cantidad": 15},
        ],
        "pagos_adicionales": {"tarjeta": 200.00, "de_una": 120.00, "delivery": 85.00},
        "fondo_vuelto": 50.00,
        "cheques": [
            {"banco": "PICHINCHA", "monto": 125.00, "tipo": "ESTANDAR", "referencia": "882012"},
            {"banco": "PRODUBANCO", "monto": 300.00, "tipo": "POSFECHADO", "referencia": "3102"},
        ],
    }
