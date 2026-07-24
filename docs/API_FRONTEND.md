# Mapeo Front-end ↔ API

Guía para conectar el front-end estático (`frontend/index.html`, que hoy usa
`localStorage`) con el backend FastAPI. Cada función JS del front tiene su
endpoint equivalente.

| Acción en el front-end (JS)                     | Endpoint del backend                              |
|-------------------------------------------------|---------------------------------------------------|
| `handleFormSubmission()` (cerrar caja)          | `POST /api/valijas`                               |
| Tabla del dashboard / `renderDashboardTable()`  | `GET /api/valijas`                                |
| KPIs / `updateMetricsKPIs()`                     | `GET /api/reportes/kpis`                          |
| `openDetailModal(id)` (auditar)                 | `GET /api/valijas/{id}`                           |
| `openCourierQRModal(id)` (generar QR)           | `GET /api/valijas/{id}/qr`                        |
| `simulateCourierScan()` (firmar mensajero)      | `POST /api/valijas/{id}/custodia`                 |
| `executeCierreBancoConfirm()` (papeleta banco)  | `POST /api/valijas/{id}/deposito`                 |
| `generatePDFManifiesto(v)` (datos del PDF)      | `GET /api/valijas/{id}/manifiesto`                |
| Reporte de cheques al banco                      | `GET /api/reportes/banco`                         |
| Reporte de posfechados a matriz                  | `GET /api/reportes/matriz`                        |

## Equivalencia de campos

El front-end usa `camelCase` interno (`deUna`, `counts`); la API usa el contrato
canónico en `snake_case`:

| Front-end (JS)          | API (JSON)                              |
|-------------------------|-----------------------------------------|
| `id`                    | `valija_id`                             |
| `cash`                  | `efectivo_total`                        |
| `counts` (array índice) | `nomenclaturas` (`[{denominacion,cantidad}]`) |
| `payments.tarjeta`      | `pagos_adicionales.tarjeta`             |
| `payments.deUna`        | `pagos_adicionales.de_una`              |
| `payments.delivery`     | `pagos_adicionales.delivery`            |
| `vuelto`                | `fondo_vuelto`                          |
| `checks[].amount`       | `cheques[].monto`                       |
| `checks[].bank`         | `cheques[].banco`                       |
| `checks[].ref`          | `cheques[].referencia`                  |
| `status`                | `estado`                                |

## Ejemplo: reemplazar `handleFormSubmission()`

```js
const API = "http://localhost:8000/api";

async function handleFormSubmission() {
  const payload = {
    usuario: state.user,
    nomenclaturas: NOMENCLATURES_DEF
      .map((n, i) => ({ denominacion: n.value, cantidad: state.currentCierre.counts[i] }))
      .filter(n => n.cantidad > 0),
    pagos_adicionales: {
      tarjeta: state.currentCierre.payments.tarjeta || 0,
      de_una: state.currentCierre.payments.deUna || 0,
      delivery: state.currentCierre.payments.delivery || 0,
    },
    fondo_vuelto: state.currentCierre.vuelto || 0,
    cheques: state.currentCierre.checks.map(c => ({
      banco: c.bank, monto: Number(c.amount), tipo: c.type, referencia: String(c.ref),
    })),
  };

  const res = await fetch(`${API}/valijas`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const valija = await res.json();
  showNotification(`Valija ${valija.valija_id} generada como ENVIADA.`);
}
```

## Ejemplo: traspaso de custodia con QR

```js
// 1) Obtener el token firmado y pintarlo en el QR:
const { texto, token } = await (await fetch(`${API}/valijas/${id}/qr`)).json();
new QRCode(container, { text: token });  // el mensajero escanea el token

// 2) Confirmar el traspaso (el mensajero presenta el token):
await fetch(`${API}/valijas/${id}/custodia`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ mensajero: "Prosegur", qr_token: token }),
});
```

> Recuerda añadir el origen del front-end a `CORS_ORIGINS` en el backend.
