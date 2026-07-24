# finapp-cajas-y-conciliaciones

**FinancePro** — Sistema de Control de Caja, Valijas y Custodia.

Gestiona el flujo financiero desde el conteo físico en el local hasta la
confirmación del depósito en el banco y el envío de cheques posfechados a la
matriz, con segregación de cheques e integraciones hacia Tableau y el ERP.

## Ciclo operativo

```
 ENVIADA            CUSTODIA                 DEPOSITADA
 (local)   ──QR──▶  (en tránsito,   ──foto──▶ (cierre final en
                     mensajero)      papeleta   el banco)
```

- **Cheques `ESTANDAR`** → van al **reporte del banco** (papeleta: efectivo + estándar).
- **Cheques `POSFECHADO`** → se consolidan para **envío a la Matriz**.

## Conciliación de cuentas

Cruce de **JD Edwards** (libros) contra los **estados de cuenta bancarios**:
cada banco se normaliza con un **perfil entrenable** y el cruce clasifica cada
movimiento en **CONCILIADO** (por campo de vinculación), **POSIBLE** (coincide
monto+fecha, requiere **aprobación humana**) o **NO CONCILIADO**.
Ver [`docs/CONCILIACION.md`](docs/CONCILIACION.md).

## Estructura del repositorio

```
├── backend/     API REST en FastAPI (lógica de negocio + integraciones)  ← ver backend/README.md
├── frontend/    SPA (Tailwind, jsPDF, QRCode.js) que consume la API (sin localStorage)
└── docs/        Manual técnico, JSON de ejemplo y mapeo Front-end ↔ API
```

Con el backend en marcha, el front-end queda disponible en
<http://localhost:8000/app/> (o ábrelo como archivo y apuntará a `localhost:8000`).

## Inicio rápido (backend)

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
# Swagger UI: http://localhost:8000/docs
```

## Documentación

- [`backend/README.md`](backend/README.md) — API, endpoints, configuración y pruebas.
- [`docs/API_FRONTEND.md`](docs/API_FRONTEND.md) — cómo conectar el front-end a la API.
- [`docs/CONCILIACION.md`](docs/CONCILIACION.md) — módulo de conciliación de cuentas.
- [`docs/manual_control_caja.md`](docs/manual_control_caja.md) — manual técnico operativo.
- [`docs/ejemplo_valija.json`](docs/ejemplo_valija.json) — contrato de datos canónico.

## Integraciones

| Sistema  | Propósito                                             | Estado                          |
|----------|-------------------------------------------------------|---------------------------------|
| Tableau  | Traer las ventas del sistema y conciliarlas           | Cliente con modo simulado listo |
| ERP      | Registrar el asiento contable con el número de valija | Cliente con modo simulado listo |

Ambas integraciones funcionan en **modo simulado** sin configuración; al definir
las credenciales correspondientes (`TABLEAU_*` / `ERP_*`) se conmuta al servicio
real (ver `backend/app/integrations/`).
