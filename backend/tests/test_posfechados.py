"""Pruebas del envío físico de cheques posfechados al banco."""


def _crear_valija_con_posfechado(client, payload):
    return client.post("/api/valijas", json=payload).json()


def test_pendientes_incluye_posfechado(client, valija_payload):
    _crear_valija_con_posfechado(client, valija_payload)
    pend = client.get("/api/posfechados/pendientes").json()
    # El payload trae un cheque POSFECHADO (PRODUBANCO 300) y uno ESTANDAR.
    assert len(pend) == 1
    assert pend[0]["banco"] == "PRODUBANCO"
    assert pend[0]["monto"] == 300.00


def test_registrar_envio_con_numero_transaccion(client, valija_payload):
    _crear_valija_con_posfechado(client, valija_payload)
    cheque_id = client.get("/api/posfechados/pendientes").json()[0]["id"]

    resp = client.post("/api/posfechados/remesas", json={
        "banco": "PRODUBANCO",
        "cheque_ids": [cheque_id],
        "numero_transaccion_banco": "TRX-99887766",
        "referencia_jde": "671256",
    })
    assert resp.status_code == 201, resp.text
    remesa = resp.json()
    assert remesa["estado"] == "CONFIRMADA"
    assert remesa["numero_transaccion_banco"] == "TRX-99887766"
    assert remesa["referencia_jde"] == "671256"
    assert remesa["total"] == 300.00
    assert remesa["cantidad_cheques"] == 1

    # Ya no debe aparecer como pendiente.
    assert client.get("/api/posfechados/pendientes").json() == []


def test_registrar_sin_numero_queda_registrada_y_luego_confirma(client, valija_payload):
    _crear_valija_con_posfechado(client, valija_payload)
    cheque_id = client.get("/api/posfechados/pendientes").json()[0]["id"]

    remesa = client.post("/api/posfechados/remesas", json={
        "banco": "PRODUBANCO", "cheque_ids": [cheque_id],
    }).json()
    assert remesa["estado"] == "REGISTRADA"
    assert remesa["numero_transaccion_banco"] is None

    # Capturar después el número que devuelve el banco.
    r = client.post(
        f"/api/posfechados/remesas/{remesa['id']}/transaccion",
        json={"numero_transaccion_banco": "DEP-123456"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["estado"] == "CONFIRMADA"
    assert r.json()["numero_transaccion_banco"] == "DEP-123456"


def test_no_se_puede_reenviar_un_cheque(client, valija_payload):
    _crear_valija_con_posfechado(client, valija_payload)
    cheque_id = client.get("/api/posfechados/pendientes").json()[0]["id"]
    client.post("/api/posfechados/remesas", json={
        "banco": "PRODUBANCO", "cheque_ids": [cheque_id],
    })
    # Segundo intento con el mismo cheque falla.
    resp = client.post("/api/posfechados/remesas", json={
        "banco": "PRODUBANCO", "cheque_ids": [cheque_id],
    })
    assert resp.status_code == 422
    assert "ya fue enviado" in resp.json()["detail"]


def test_rechaza_cheque_estandar(client, valija_payload):
    creada = _crear_valija_con_posfechado(client, valija_payload)
    # El cheque ESTANDAR (PICHINCHA) no puede ir en una remesa de posfechados.
    estandar = next(c for c in creada["cheques"] if c["tipo"] == "ESTANDAR")
    resp = client.post("/api/posfechados/remesas", json={
        "banco": "PICHINCHA", "cheque_ids": [estandar["id"]],
    })
    assert resp.status_code == 422
    assert "no es POSFECHADO" in resp.json()["detail"]


def test_listar_remesas(client, valija_payload):
    _crear_valija_con_posfechado(client, valija_payload)
    cheque_id = client.get("/api/posfechados/pendientes").json()[0]["id"]
    client.post("/api/posfechados/remesas", json={
        "banco": "PRODUBANCO", "cheque_ids": [cheque_id],
        "numero_transaccion_banco": "TRX-1",
    })
    remesas = client.get("/api/posfechados/remesas").json()
    assert len(remesas) == 1
    assert remesas[0]["numero_transaccion_banco"] == "TRX-1"
