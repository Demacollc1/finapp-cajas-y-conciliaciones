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
| 4 | Confirmación de cobro (cheque cobrado en el banco, estado 3→0) | En análisis | [04-confirmacion-cobro.md](04-confirmacion-cobro.md) |

> Documento vivo: se irá ampliando con cada paso que analicemos.

**Decisión de diseño transversal:**
[Referencia y vinculación bancaria](vinculacion-bancaria.md)
— usar el **nº de `Batch`** como referencia del depósito, campo de vinculación y
acumulador de la conciliación (`Batch` ⊃ `DREG` ⊃ efecto).

## Ciclo del efecto (cheque posfechado)

```
Paso 1  Ingreso         doc R1   estado 4    Debe 1.110209.02 / Haber 1.110205.01
Paso 2  Registro        (DREG)   estado 4
Paso 3  Envío al banco  R1→R2    estado 4→3  Debe 1.110209.03 / Haber 1.110209.02
Paso 4  Cobro/confirm.           estado 3→0  Debe Bancos      / Haber 1.110209.03  (esperado, batch 671259)
```

**Estados:** `4` = ingresado · `3` = enviado al banco · `0` = cobrado/confirmado.
**Tipos de documento:** `R1` = efecto aceptado · `R2` = efecto remitido/consigna.

**Mapa de cuentas:**

| Cuenta | Significado |
|--------|-------------|
| `1.110205.01` | Cuentas por cobrar clientes |
| `1.110209.02` | Cheque posfechado — **ingreso / en cartera** |
| `1.110209.03` | Cheque posfechado — **consigna / en el banco** |
| Bancos | *(cobro final, esperado)* |

## Agrupación y referencia bancaria

`Batch` ⊃ `DREG` ⊃ `Efecto`. **Referencia del depósito en el banco = número de
`Batch`** (el agrupador de la transacción contable). Ver
[vinculacion-bancaria.md](vinculacion-bancaria.md).

## Convenciones

- Los nombres de tabla JDE se citan como `F03B13`, `F0101`, etc.
- Los valores de ejemplo provienen de exportaciones reales **anonimizadas**
  (nombres de banco, cuentas y números de efecto reemplazados por marcadores).
