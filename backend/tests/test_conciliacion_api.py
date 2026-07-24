"""Pruebas de la API de conciliación: perfiles, ejecución y aprobación."""

import pytest
from sqlalchemy.orm import sessionmaker

from app.conciliacion.models import PerfilBanco
from app.conciliacion.seed import seed_perfiles

# CSV de ejemplo (coinciden con docs/ y con los perfiles sembrados).
JDE_CSV = (
    "Fecha,Documento,Descripcion,Monto\n"
    "2026-05-11,DOC1001,Deposito valija VAL-882910,450.00\n"
    "2026-05-10,DOC1002,Deposito valija VAL-109283,830.00\n"
    "2026-05-09,DOC1003,Deposito valija VAL-662510,250.00\n"
    "2026-05-08,DOC1004,Deposito efectivo sucursal,120.00\n"
    "2026-05-07,DOC1005,Nota credito cliente,75.50\n"
).encode()

PICHINCHA_CSV = (
    "FECHA;CONCEPTO;REFERENCIA;DEBITO;CREDITO\n"
    "11/05/2026;DEPOSITO EFECTIVO;DOC1001;0,00;450,00\n"
    "10/05/2026;DEPOSITO EFECTIVO;DOC1002;0,00;830,00\n"
    "08/05/2026;DEPOSITO VENTANILLA;;0,00;120,00\n"
    "06/05/2026;COMISION MANTENIMIENTO;;5,00;0,00\n"
).encode()

PRODUBANCO_CSV = (
    "Date,Description,Doc,Amount\n"
    "05/09/2026,DEPOSITO EFECTIVO,DOC1003,250.00\n"
    "05/05/2026,TRANSFERENCIA RECIBIDA,DOC9999,500.00\n"
).encode()


@pytest.fixture
def perfiles(db_engine):
    S = sessionmaker(bind=db_engine)
    with S() as db:
        seed_perfiles(db)
    with S() as db:
        return {p.nombre: p.id for p in db.query(PerfilBanco).all()}


def _ejecutar(client, perfiles, banco_ids=None):
    files = [
        ("libro_archivo", ("jde.csv", JDE_CSV, "text/csv")),
        ("banco_archivos", ("pichincha.csv", PICHINCHA_CSV, "text/csv")),
        ("banco_archivos", ("produbanco.csv", PRODUBANCO_CSV, "text/csv")),
    ]
    data = {"libro_perfil_id": str(perfiles["JD Edwards (Libro)"]), "tolerancia_dias": "3"}
    if banco_ids is not None:
        data["banco_perfil_ids"] = banco_ids
    return client.post("/api/conciliacion/ejecutar", data=data, files=files)


# ------------------------------ perfiles ---------------------------------- #
def test_inspeccionar_csv(client):
    r = client.post(
        "/api/conciliacion/perfiles/inspeccionar",
        files={"archivo": ("pich.csv", PICHINCHA_CSV, "text/csv")},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["delimitador"] == ";"
    assert "REFERENCIA" in data["columnas"]
    assert data["total_filas"] == 4


def test_crear_perfil_sin_monto_falla(client):
    r = client.post("/api/conciliacion/perfiles", json={
        "nombre": "X", "tipo": "BANCO", "columna_fecha": "F",
    })
    assert r.status_code == 422


def test_seed_perfiles(client, perfiles):
    r = client.get("/api/conciliacion/perfiles")
    nombres = {p["nombre"] for p in r.json()}
    assert {"JD Edwards (Libro)", "Banco Pichincha", "Banco Produbanco"} <= nombres


# ------------------------------ ejecución --------------------------------- #
def test_ejecutar_conciliacion(client, perfiles):
    ids = f"{perfiles['Banco Pichincha']},{perfiles['Banco Produbanco']}"
    r = _ejecutar(client, perfiles, banco_ids=ids)
    assert r.status_code == 200, r.text
    det = r.json()
    res = det["resumen"]

    assert res["total_libro"] == 5
    assert res["total_banco"] == 6
    assert res["conciliados"] == 3          # DOC1001, DOC1002, DOC1003 (por clave)
    assert res["posibles"] == 1             # DOC1004 <-> deposito 120 (monto+fecha)
    assert res["no_conciliados_libro"] == 1  # DOC1005
    assert res["no_conciliados_banco"] == 2  # comision 5 + transferencia 500

    assert res["monto_conciliado"] == 1530.00
    assert res["monto_posible"] == 120.00
    assert res["monto_no_conciliado_libro"] == 75.50
    assert res["monto_no_conciliado_banco"] == 505.00

    # El par posible referencia ambos lados.
    assert len(det["posibles"]) == 1
    par = det["posibles"][0]
    assert par["libro"]["clave"] == "DOC1004"
    assert abs(par["banco"]["monto"]) == 120.00


def test_ejecutar_autodetecta_perfil(client, perfiles):
    # Sin banco_perfil_ids: debe autodetectar por columnas.
    r = _ejecutar(client, perfiles, banco_ids=None)
    assert r.status_code == 200, r.text
    assert r.json()["resumen"]["conciliados"] == 3


def test_aprobar_posible(client, perfiles):
    ids = f"{perfiles['Banco Pichincha']},{perfiles['Banco Produbanco']}"
    det = _ejecutar(client, perfiles, banco_ids=ids).json()
    conc_id = det["resumen"]["id"]
    mov_id = det["posibles"][0]["libro"]["id"]

    r = client.post(f"/api/conciliacion/{conc_id}/movimientos/{mov_id}/aprobar")
    assert r.status_code == 200, r.text
    res = r.json()["resumen"]
    assert res["conciliados"] == 4
    assert res["posibles"] == 0
    assert res["monto_conciliado"] == 1650.00


def test_rechazar_posible(client, perfiles):
    ids = f"{perfiles['Banco Pichincha']},{perfiles['Banco Produbanco']}"
    det = _ejecutar(client, perfiles, banco_ids=ids).json()
    conc_id = det["resumen"]["id"]
    mov_id = det["posibles"][0]["libro"]["id"]

    r = client.post(f"/api/conciliacion/{conc_id}/movimientos/{mov_id}/rechazar")
    assert r.status_code == 200, r.text
    res = r.json()["resumen"]
    assert res["posibles"] == 0
    # El movimiento del libro y el del banco quedan como no conciliados.
    assert res["no_conciliados_libro"] == 2
    assert res["no_conciliados_banco"] == 3


def test_detalle_y_listado(client, perfiles):
    ids = f"{perfiles['Banco Pichincha']},{perfiles['Banco Produbanco']}"
    conc_id = _ejecutar(client, perfiles, banco_ids=ids).json()["resumen"]["id"]

    assert client.get(f"/api/conciliacion/{conc_id}").status_code == 200
    listado = client.get("/api/conciliacion").json()
    assert any(c["id"] == conc_id for c in listado)
