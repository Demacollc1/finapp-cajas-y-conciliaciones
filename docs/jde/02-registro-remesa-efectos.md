# Paso 2 — Registro / remesa de efectos (envío al banco)

## Qué es

Los efectos (`R1`) aceptados en el [paso 1](01-ingreso-cheques-posfechados.md)
se agrupan en una **remesa / registro de efectos** para **enviarlos al banco a
cobro**. JDE genera un **número de registro de efectos** que identifica el lote
y asigna la **cuenta bancaria** por la que se cobrarán.

- **Tabla:** `F03B13` — se **actualiza el mismo registro** del efecto (no se crea
  una fila nueva; se rellenan campos que antes estaban vacíos).
- **Instrumento de pago:** `Insto pago = F` (efecto).
- **Programa (según el campo):** `P03B602`. *(La remesa de efectos suele
  ejecutarse con `P03B672`/`R03B672`; a confirmar cuál se usó.)*

## El objeto que se crea

| Objeto | Campo en `F03B13` | Valor de ejemplo |
|--------|-------------------|------------------|
| **Número de registro de efectos** | `Registro efectos` | `67124900001` |

> Probable composición: **registro `671249` + compañía `00001`** (el batch del
> ingreso fue `671247`). *A confirmar.*

## Qué cambia respecto al paso 1

Mismo efecto, pero la remesa rellena campos que estaban vacíos:

| Campo (`F03B13`) | Paso 1 (ingreso) | Paso 2 (remesa) |
|------------------|------------------|-----------------|
| `Registro efectos` | *(vacío)* | **`67124900001`** |
| `Cuenta bcria LM` (banco destino) | *(vacío)* | **`00000059`** |
| `Md cta` (modo de cuenta) | *(vacío)* | `1` |
| `E E` (estado del efecto) | `4` | `4` *(sin cambio en este campo)* |
| Hora | `13:41` (post) | `13:44:02` |

Todo lo demás es idéntico (mismo `ID pago 389969`, `Número cobro`, importe
`666.00 USD`, cliente `23789`, documento `R1 54356`).

## Datos del ejemplo

| Concepto | Campo | Valor |
|----------|-------|-------|
| ID de pago | `ID pago` | `389969` |
| Número de efecto | `Número cobro` | *(anonimizado)* |
| **Registro de efectos** | `Registro efectos` | **`67124900001`** |
| Banco de cobro | `Cuenta bcria LM` | `00000059` |
| Importe | `Importe cheque` | `666.00 USD` |
| Cliente | `Nº pagador` / `Nombre alfabético` | `23789` · COMISARIATO DEL CONSTRUCTOR S.A. |
| Fecha de liquidación | `Fecha liqd` | `24/07/26` |
| Usuario / hora | `ID usuario` · `Hora actz` | `ROBGOMEZ` · `13:44:02` |

## Relación con FinancePro

Este paso corresponde al **envío físico de los cheques posfechados desde Matriz
al banco**. El **número de registro de efectos** (`67124900001`) identifica el
**lote enviado** — es el equivalente en JDE a una *remesa/valija de cheques*.

Para la conciliación bancaria, este número (junto con el nº de efecto y el
documento `R1`) es un **candidato de campo de vinculación**: cuando el banco
reporte el cobro del cheque, el cruce puede enlazarse por el registro de efectos.

## Contabilización

En este paso **no se adjuntó** reporte de contabilización (`R09801`). Según la
parametrización, la remesa **puede** generar un asiento que reclasifica de
*efectos en cartera* (`1.110209.02`) a una cuenta de *efectos remitidos al
cobro*. **A confirmar** con el post del batch de la remesa (¿`671249`?), si existe.

## Preguntas abiertas

1. ¿Qué **programa** ejecuta realmente la remesa? (el campo muestra `P03B602`;
   la remesa suele ser `P03B672`/`R03B672`).
2. ¿La remesa **genera asiento contable**? Si sí, ¿qué cuentas (efectos
   remitidos)? ¿Es remesa **con o sin** responsabilidad contingente?
3. ¿Confirmamos la **composición** del nº de registro (`671249` + `00001`)?
4. ¿Qué determina la **cuenta bancaria `00000059`**? (¿se elige el banco al
   remesar?) ¿Se relaciona con el `Cuenta bcria LM` que usará la conciliación?
5. ¿Cuántos efectos agrupa un registro normalmente? (aquí 1; el proceso admite
   "un conjunto de cheques").
