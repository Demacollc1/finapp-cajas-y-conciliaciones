"""Pruebas de creación y consulta de valijas."""


def test_crear_valija_calcula_efectivo(client, valija_payload):
    resp = client.post("/api/valijas", json=valija_payload)
    assert resp.status_code == 201, resp.text
    data = resp.json()

    assert data["valija_id"].startswith("VAL-")
    assert data["estado"] == "ENVIADA"
    # 15*20 + 15*10 = 450
    assert data["efectivo_total"] == 450.00
    assert data["pagos_adicionales"]["de_una"] == 120.00
    assert len(data["cheques"]) == 2
    # Segregación reflejada en los totales derivados.
    assert data["monto_deposito_banco"] == 450.00 + 125.00
    assert data["monto_custodia_matriz"] == 300.00


def test_crear_valija_efectivo_inconsistente_falla(client, valija_payload):
    valija_payload["efectivo_total"] = 999.00  # no cuadra con el desglose
    resp = client.post("/api/valijas", json=valija_payload)
    assert resp.status_code == 422


def test_listar_y_obtener_valija(client, valija_payload):
    creada = client.post("/api/valijas", json=valija_payload).json()
    vid = creada["valija_id"]

    lista = client.get("/api/valijas").json()
    assert any(v["valija_id"] == vid for v in lista)

    detalle = client.get(f"/api/valijas/{vid}").json()
    assert detalle["valija_id"] == vid


def test_obtener_valija_inexistente_404(client):
    assert client.get("/api/valijas/VAL-000000").status_code == 404


def test_filtro_por_estado(client, valija_payload):
    client.post("/api/valijas", json=valija_payload)
    enviadas = client.get("/api/valijas", params={"estado": "ENVIADA"}).json()
    assert all(v["estado"] == "ENVIADA" for v in enviadas)
    assert client.get("/api/valijas", params={"estado": "DEPOSITADA"}).json() == []


def test_manifiesto(client, valija_payload):
    vid = client.post("/api/valijas", json=valija_payload).json()["valija_id"]
    m = client.get(f"/api/valijas/{vid}/manifiesto").json()
    assert m["monto_deposito_banco"] == 575.00       # 450 efectivo + 125 estándar
    assert m["monto_custodia_matriz"] == 300.00      # posfechado
    assert m["cheques_estandar_cantidad"] == 1
    assert m["cheques_posfechados_cantidad"] == 1
