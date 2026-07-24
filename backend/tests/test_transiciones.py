"""Pruebas del ciclo de estados ENVIADA -> CUSTODIA -> DEPOSITADA."""


def _crear(client, payload):
    return client.post("/api/valijas", json=payload).json()["valija_id"]


def test_flujo_completo(client, valija_payload):
    vid = _crear(client, valija_payload)

    # QR firmado por el backend.
    qr = client.get(f"/api/valijas/{vid}/qr").json()
    assert qr["texto"] == f"CUSTODY-TRANSFER-CONFIRMATION-{vid}"

    # ENVIADA -> CUSTODIA
    resp = client.post(
        f"/api/valijas/{vid}/custodia",
        json={"mensajero": "Transportadora XYZ", "qr_token": qr["token"]},
    )
    assert resp.status_code == 200, resp.text
    cust = resp.json()
    assert cust["estado"] == "CUSTODIA"
    assert cust["mensajero"] == "Transportadora XYZ"
    assert cust["custodia_en"] is not None

    # CUSTODIA -> DEPOSITADA (registra asiento ERP)
    resp = client.post(
        f"/api/valijas/{vid}/deposito",
        json={"banco": "PICHINCHA", "comprobante": "data:image/png;base64,AAAA"},
    )
    assert resp.status_code == 200, resp.text
    dep = resp.json()
    assert dep["estado"] == "DEPOSITADA"
    assert dep["banco_deposito"] == "PICHINCHA"
    assert dep["erp_asiento_id"] == f"AST-{vid.replace('VAL-', '')}"


def test_qr_invalido_rechaza_custodia(client, valija_payload):
    vid = _crear(client, valija_payload)
    resp = client.post(
        f"/api/valijas/{vid}/custodia",
        json={"mensajero": "X", "qr_token": "token-falso"},
    )
    assert resp.status_code == 409
    assert "QR" in resp.json()["detail"]


def test_no_se_puede_saltar_a_deposito(client, valija_payload):
    vid = _crear(client, valija_payload)
    # Sigue en ENVIADA: no se permite ir directo a DEPOSITADA.
    resp = client.post(
        f"/api/valijas/{vid}/deposito",
        json={"banco": "PICHINCHA", "comprobante": "x"},
    )
    assert resp.status_code == 409


def test_no_se_repite_custodia(client, valija_payload):
    vid = _crear(client, valija_payload)
    qr = client.get(f"/api/valijas/{vid}/qr").json()
    client.post(
        f"/api/valijas/{vid}/custodia",
        json={"mensajero": "X", "qr_token": qr["token"]},
    )
    # Segundo intento debe fallar (ya no está en ENVIADA).
    resp = client.post(
        f"/api/valijas/{vid}/custodia",
        json={"mensajero": "X", "qr_token": qr["token"]},
    )
    assert resp.status_code == 409
