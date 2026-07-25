# Automatización de procesos en JD Edwards

Documentación del **paso a paso** de cómo se registran hoy las transacciones en
JD Edwards (JDE), como base para automatizarlas más adelante.

Cada paso describe: qué acción operativa ocurre, qué **tablas** de JDE se
afectan, qué **objetos** se crean (documentos, batches, IDs) y qué se necesita
para automatizarlo.

## Pasos

| # | Proceso | Estado | Doc |
|---|---------|--------|-----|
| 1 | Ingreso de cheques posfechados (efectos A/R) + contabilización | En análisis | [01-ingreso-cheques-posfechados.md](01-ingreso-cheques-posfechados.md) |
| 2 | Registro / remesa de efectos (asignación del registro) | En análisis | [02-registro-remesa-efectos.md](02-registro-remesa-efectos.md) |
| 3 | Envío de efectos al banco (`R03B672`, estado 4→3, `R1`→`R2`) | En análisis | [03-envio-efectos-banco.md](03-envio-efectos-banco.md) |

> Documento vivo: se irá ampliando con cada paso que analicemos.

**Decisión de diseño transversal:**
[Vinculación bancaria por registro de efectos (`DREG`)](vinculacion-bancaria-dreg.md)
— usar el `DREG` como referencia del depósito, campo de vinculación y acumulador
de la conciliación.

## Ciclo del efecto (cheque posfechado)

```
Paso 1            Paso 2            Paso 3                    (siguiente)
Ingreso           Registro          Envío al banco           Cobro
doc R1            registro efectos  R03B672 · doc R1→R2       (banco paga)
estado 4          estado 4          estado 4 → 3             estado 3 → ?
Debe 1.110209.02                    (cuenta 1.110102.03)     Debe Bancos
Haber 1.110205.01                                            Haber efectos
```

**Estados:** `4` = ingresado · `3` = enviado al banco.
**Tipos de documento:** `R1` = efecto aceptado · `R2` = efecto remitido.

## Convenciones

- Los nombres de tabla JDE se citan como `F03B13`, `F0101`, etc.
- Los valores de ejemplo provienen de exportaciones reales **anonimizadas**
  (nombres de banco, cuentas y números de efecto reemplazados por marcadores).
