# Automatización de procesos en JD Edwards

Documentación del **paso a paso** de cómo se registran hoy las transacciones en
JD Edwards (JDE), como base para automatizarlas más adelante.

Cada paso describe: qué acción operativa ocurre, qué **tablas** de JDE se
afectan, qué **objetos** se crean (documentos, batches, IDs) y qué se necesita
para automatizarlo.

## Pasos

| # | Proceso | Estado | Doc |
|---|---------|--------|-----|
| 1 | Ingreso de cheques posfechados (efectos A/R) | En análisis | [01-ingreso-cheques-posfechados.md](01-ingreso-cheques-posfechados.md) |

> Documento vivo: se irá ampliando con cada paso que analicemos.

## Convenciones

- Los nombres de tabla JDE se citan como `F03B13`, `F0101`, etc.
- Los valores de ejemplo provienen de exportaciones reales **anonimizadas**
  (nombres de banco, cuentas y números de efecto reemplazados por marcadores).
