"""Pruebas de KPIs y reportes de segregación (banco / matriz)."""


def _crear(client, payload):
    return client.post("/api/valijas", json=payload).json()["valija_id"]


def test_kpis(client, valija_payload):
    _crear(client, valija_payload)
    k = client.get("/api/reportes/kpis").json()
    assert k["total_valijas"] == 1
    assert k["sin_confirmar_banco"] == 1        # está en ENVIADA
    assert k["en_custodia"] == 0
    assert k["efectivo_recibido"] == 450.00
    assert k["caja_vuelto"] == 50.00
    assert k["posfechados_matriz"] == 1         # tiene un cheque posfechado


def test_reporte_banco_suma_efectivo_y_estandar(client, valija_payload):
    _crear(client, valija_payload)
    r = client.get("/api/reportes/banco").json()
    assert r["cantidad_valijas"] == 1
    assert r["total_efectivo"] == 450.00
    assert r["total_cheques_estandar"] == 125.00   # solo el ESTANDAR
    assert r["total_general"] == 575.00
    assert r["detalle"][0]["total_papeleta"] == 575.00


def test_reporte_matriz_solo_posfechados(client, valija_payload):
    _crear(client, valija_payload)
    r = client.get("/api/reportes/matriz").json()
    assert r["cantidad_cheques"] == 1
    assert r["total_posfechado"] == 300.00
    assert r["detalle"][0]["banco"] == "PRODUBANCO"
    assert r["detalle"][0]["referencia"] == "3102"
