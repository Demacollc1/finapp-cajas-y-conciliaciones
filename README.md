# finapp-cajas-y-conciliaciones

Aplicación web para la administración de **cajas de efectivo** y sus **conciliaciones** (arqueo teórico vs. físico), pensada para operaciones en Ecuador (moneda USD).

## Funcionalidad

- **Panel** — indicadores del día: efectivo total en cajas, cajas abiertas, movimientos del día y conciliaciones pendientes.
- **Cajas** — alta de cajas, responsable, estado (abierta/cerrada) y saldo de efectivo calculado.
- **Movimientos** — registro de ingresos y egresos por caja (efectivo, transferencia o tarjeta), con filtros.
- **Conciliación** — arqueo de caja: compara el saldo teórico de efectivo contra el conteo físico y calcula la diferencia (cuadrada / sobrante / faltante), con historial.
- **Reportes** — totales acumulados: ingresos, egresos, flujo neto, efectivo por caja y por método.

## Cómo ejecutarlo

Es una sola página autónoma (HTML + CSS + JavaScript, sin dependencias). Los datos se guardan en el navegador (`localStorage`).

1. Abre `index.html` directamente en el navegador, **o**
2. Sírvelo localmente:
   ```bash
   python3 -m http.server 8000
   # luego abre http://localhost:8000
   ```

La aplicación se carga con **datos de ejemplo** la primera vez. El botón **“Restaurar datos de ejemplo”** (barra lateral) los vuelve a cargar en cualquier momento.
