"""Pruebas de las integraciones Tableau (ventas) y ERP (asiento)."""


def _crear(client, payload):
    return client.post("/api/valijas", json=payload).json()["valija_id"]


def _depositar(client, vid):
    qr = client.get(f"/api/valijas/{vid}/qr").json()
    client.post(
        f"/api/valijas/{vid}/custodia",
        json={"mensajero": "X", "qr_token": qr["token"]},
    )
    client.post(
        f"/api/valijas/{vid}/deposito",
        json={"banco": "PICHINCHA", "comprobante": "x"},
    )


def test_tableau_ventas_simuladas(client):
    r = client.get("/api/integraciones/tableau/ventas", params={"dia": "2026-05-11"})
    assert r.status_code == 200
    data = r.json()
    assert "SIMULADO" in data["fuente"]
    assert data["total_ventas"] == 855.00       # 450+200+120+85


def test_conciliacion(client, valija_payload):
    _crear(client, valija_payload)
    r = client.get(
        "/api/integraciones/tableau/conciliacion", params={"dia": "2026-05-11"}
    ).json()
    # Declarado = efectivo 450 + tarjeta 200 + de_una 120 + delivery 85 = 855
    assert r["total_declarado"] == 855.00
    assert r["total_tableau"] == 855.00
    assert r["diferencia"] == 0.0
    assert r["cuadrado"] is True


def test_asiento_erp_requiere_deposito(client, valija_payload):
    vid = _crear(client, valija_payload)
    # Aún en ENVIADA: no se puede registrar el asiento.
    assert client.post(f"/api/integraciones/erp/asiento/{vid}").status_code == 409

    _depositar(client, vid)
    r = client.post(f"/api/integraciones/erp/asiento/{vid}").json()
    assert r["asiento_id"] == f"AST-{vid.replace('VAL-', '')}"
    # El asiento debe cuadrar: total debe == total haber.
    # Banco = 450 efectivo + 125 estándar = 575 ; Posfechado = 300 ; Total = 875.
    movs = r["detalle"]["movimientos"]
    total_debe = sum(m["debe"] for m in movs)
    total_haber = sum(m["haber"] for m in movs)
    assert total_debe == total_haber == 875.00
