# FinancePro — Backend (FastAPI)

Backend del sistema de **Control de Caja, Valijas y Custodia**. Expone una API
REST que implementa la lógica de negocio que el front-end (`/frontend/index.html`)
hoy resuelve en memoria con `localStorage`.

## Características

- **Ciclo de estados** de la valija: `ENVIADA` → `CUSTODIA` → `DEPOSITADA`,
  con transiciones validadas (no se permiten saltos).
- **Traspaso de custodia por QR**: el backend firma un token (HMAC-SHA256) que
  el mensajero debe presentar para pasar la valija a `CUSTODIA`.
- **Segregación de cheques**:
  - `ESTANDAR` → se suman al efectivo en el **reporte del banco** (papeleta).
  - `POSFECHADO` → se consolidan en el **reporte de Matriz** (custodia central).
- **Dashboard / KPIs**: efectivo recibido, caja de vuelto, en custodia, sin
  confirmar banco, posfechados a matriz.
- **Manifiesto de depósito**: mismos totales que el PDF que genera el front-end.
- **Integraciones** (con modo simulado listo para desarrollar):
  - **Tableau** → traer las ventas del sistema y **conciliarlas** contra lo declarado.
  - **ERP** → registrar el **asiento contable** usando el número de valija.

## Stack

FastAPI · SQLAlchemy 2.0 · Pydantic v2 · Uvicorn · pytest.
Base de datos por defecto **SQLite** (portable); conmutable a **PostgreSQL** vía
`DATABASE_URL`.

## Puesta en marcha

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

- API: <http://localhost:8000/api>
- Documentación interactiva (Swagger): <http://localhost:8000/docs>
- Al arrancar se crean las tablas y se cargan 3 valijas de demostración
  (idénticas al estado inicial del front-end).

### Con Docker

```bash
cd backend
docker compose up --build
```

## Variables de entorno

Ver `.env.example`. Las más relevantes:

| Variable            | Descripción                                            | Default              |
|---------------------|--------------------------------------------------------|----------------------|
| `DATABASE_URL`      | Cadena de conexión SQLAlchemy                          | `sqlite:///./financepro.db` |
| `QR_SECRET`         | Clave para firmar los tokens QR de custodia            | *(cambiar en prod)*  |
| `SEED_ON_STARTUP`   | Cargar datos de demostración al arrancar               | `true`               |
| `TABLEAU_BASE_URL`  | Endpoint de Tableau (si se omite, modo simulado)       | —                    |
| `ERP_BASE_URL`      | Endpoint del ERP (si se omite, modo simulado)          | —                    |

## Endpoints

| Método | Ruta                                        | Descripción                                   |
|--------|---------------------------------------------|-----------------------------------------------|
| `POST` | `/api/valijas`                              | Crear cierre de caja (nace `ENVIADA`)         |
| `GET`  | `/api/valijas`                              | Listar (filtros: `estado`, `usuario`, `buscar`) |
| `GET`  | `/api/valijas/{id}`                         | Detalle de valija                             |
| `GET`  | `/api/valijas/{id}/qr`                       | Payload QR firmado para el mensajero          |
| `GET`  | `/api/valijas/{id}/manifiesto`              | Datos del manifiesto (banco + matriz)         |
| `POST` | `/api/valijas/{id}/custodia`                | `ENVIADA` → `CUSTODIA` (valida QR)            |
| `POST` | `/api/valijas/{id}/deposito`                | `CUSTODIA` → `DEPOSITADA` (+ asiento ERP)     |
| `GET`  | `/api/reportes/kpis`                        | KPIs del dashboard                            |
| `GET`  | `/api/reportes/banco`                       | Papeleta bancaria (efectivo + estándar)       |
| `GET`  | `/api/reportes/matriz`                      | Consolidado de posfechados                    |
| `GET`  | `/api/integraciones/tableau/ventas`         | Ventas del sistema (Tableau)                  |
| `GET`  | `/api/integraciones/tableau/conciliacion`   | Conciliación declarado vs. Tableau            |
| `POST` | `/api/integraciones/erp/asiento/{id}`       | Registrar/re-registrar asiento en el ERP      |

## Contrato de datos

El cuerpo de creación y la salida siguen el JSON canónico del proyecto
(`docs/ejemplo_valija.json`):

```json
{
  "usuario": "Cajero_01",
  "fecha": "2026-05-11T09:15:32",
  "nomenclaturas": [{ "denominacion": 20.00, "cantidad": 15 }],
  "pagos_adicionales": { "tarjeta": 200.00, "de_una": 120.00, "delivery": 85.00 },
  "fondo_vuelto": 50.00,
  "cheques": [
    { "banco": "PICHINCHA", "monto": 125.00, "tipo": "ESTANDAR", "referencia": "882012" },
    { "banco": "PRODUBANCO", "monto": 300.00, "tipo": "POSFECHADO", "referencia": "3102" }
  ]
}
```

> `efectivo_total` es opcional al crear: si se omite se calcula desde
> `nomenclaturas`; si se envía, debe cuadrar con el desglose (o se rechaza con 422).

## Pruebas

```bash
source .venv/bin/activate
pytest -q
```

16 pruebas cubren creación/validación, ciclo de estados, segregación de cheques,
KPIs, reportes e integraciones (Tableau/ERP).

## Estructura

```
backend/
├── app/
│   ├── main.py              # App FastAPI, CORS, arranque y semilla
│   ├── config.py            # Settings (pydantic-settings)
│   ├── database.py          # Engine + sesión SQLAlchemy
│   ├── enums.py             # Estados y transiciones válidas
│   ├── models.py            # ORM: Valija, Cheque
│   ├── schemas.py           # Contrato Pydantic (entrada/salida)
│   ├── services.py          # Lógica de negocio
│   ├── seed.py              # Datos de demostración
│   ├── routers/             # valijas · reportes · integraciones
│   └── integrations/        # tableau.py · erp.py (stubs + modo simulado)
└── tests/                   # pytest
```

## Próximos pasos de integración

- **Tableau**: implementar `TableauClient._fetch_remoto` (Tableau REST API) y
  configurar `TABLEAU_BASE_URL`/`TABLEAU_TOKEN`.
- **ERP**: implementar `ErpClient._post_remoto` (endpoint de asientos) y
  configurar `ERP_BASE_URL`/`ERP_TOKEN`. La estructura del asiento ya se arma
  localmente y cuadra (debe = haber).
- **Front-end**: reemplazar el `localStorage` por llamadas `fetch` a esta API
  (ver `docs/API_FRONTEND.md`).
