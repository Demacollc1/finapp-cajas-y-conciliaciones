# Paso 3 — Envío de efectos al banco (`R03B672`)

## Qué es

Se ejecuta el reporte **`R03B672` — "Remesa de giros"**, que **envía al banco**
los efectos previamente registrados. Al correrlo:

- Genera un **reporte de detalle** de los efectos contenidos en el registro
  (`R03B672`, versión DEM0002).
- Genera el **documento físico de remesa** para el banco
  (`R03B672P` — *"Formulario papel de remesa de giros C/C"*, versión XJDE0001).
- **Cambia el estado** de cada efecto de **`4` (ingresado)** a **`3` (enviado al
  banco)**.
- **Cambia el tipo de documento** del efecto de **`R1`** (aceptado) a **`R2`**
  (remitido).
- El efecto **desaparece de la pantalla de confirmación de cheques**: al pasar a
  estado `3` sale del filtro de pendientes por confirmar (ya fue enviado).

> **Identificador de la conciliación:** se recomienda usar el **número de
> registro de efectos** (campo **`DREG`**) como referencia del depósito
> bancario. Ver [vinculacion-bancaria-dreg.md](vinculacion-bancaria-dreg.md).

## Estados del efecto

| Estado | Significado |
|:------:|-------------|
| `4` | Ingresado / aceptado (pasos 1–2) |
| `3` | **Enviado al banco (remitido)** ← este paso |

## Documentos y tipos

| Tipo doc | Etapa |
|:--------:|-------|
| `R1` | Efecto aceptado (paso 1) |
| **`R2`** | **Efecto remitido al banco (este paso)** |

## Contenido de la remesa (ejemplo, batch `671256`)

El registro enviado agrupa **3 efectos** por **US$ 966.00**:

| Cliente | Nº direc | Doc | Nº efecto | Importe | Registro efectos | Cuenta |
|---------|:--------:|:---:|-----------|--------:|------------------|--------|
| COMISARIATO DEL CONSTRUCTOR S.A. | 23789 | `R2` 54356 | *(anonimizado)* | 666.00 | `67124900001` | `1.110102.03` |
| SEATEC S.A. | 22383 | `R2` 54357 | 667 | 200.00 | `67125300001` | `1.110102.03` |
| MACOFE S.A. | 22825 | `R2` 54358 | 668 | 100.00 | `67125300001` | `1.110102.03` |
| | | | **Total** | **966.00** | | |

- **Batch de la remesa:** `671256`, fecha `24/07/26`.
- **Cuenta asociada:** `1.110102.03` (cuenta bancaria / de giros remitidos).
- Confirma la composición del **registro de efectos** = **nº registro +
  compañía** (`671249` + `00001`, `671253` + `00001`).
- **El batch agrupa varios `DREG` en una sola transacción contable:** el batch
  `671256` contiene los registros `671249` (666.00) y `671253` (300.00) = 966.00.
  La **contabilización** es a nivel de **batch**; la **conciliación bancaria** a
  nivel de **`DREG`** (cada depósito). Ver
  [vinculacion-bancaria-dreg.md](vinculacion-bancaria-dreg.md).

## Los dos reportes que genera

**1. `R03B672` — "Remesa de giros"** (detalle contable/operativo)
Una página por cliente con: Nº dirección, nombre, **tipo doc `R2`**, nº de
documento A/D, nº de efecto, entidad bancaria, fecha de vencimiento, importe,
**número de cuenta `1.110102.03`** y registro de efectos. Totales por cliente.

**2. `R03B672P` — "Formulario papel de remesa de giros C/C"** (documento físico
para el banco)
Agrupado por **registro de efectos** y banco, con la **cuenta bancaria del
cliente**, pagador, importe, **nº de giro** y **referencia del recibo**:

| Registro | Banco | Efectos | Total |
|----------|:-----:|---------|------:|
| `67125300001` | Entd. bcria 17 | SEATEC (667, 200.00) + MACOFE (668, 100.00) | 300.00 |
| `67124900001` | *(banco Comisariato)* | Comisariato (666.00) | 666.00 |
| | | **Total remesa** | **966.00** |

## Contabilización

Estos dos reportes son el **detalle** y el **documento físico**; el efecto visible
es el cambio de estado `4 → 3` y de tipo `R1 → R2`. La aparición de la cuenta
`1.110102.03` sugiere una reclasificación contable de la remesa (de *efectos en
cartera* `1.110209.02` hacia una cuenta bancaria/de giros remitidos), pero **no
se adjuntó el post `R09801`** de este batch. **A confirmar** si `R03B672` genera
asiento (según versión/parametrización) o si es solo operativo.

## Relación con FinancePro

Corresponde al momento en que el **lote de cheques posfechados sale de Matriz
hacia el banco**. El **registro de efectos** y el **nº de giro** son los
identificadores del lote y de cada cheque — los **campos de vinculación** para
conciliar cuando el banco reporte el cobro (paso siguiente).

## Preguntas abiertas

1. ¿`R03B672` **genera asiento contable** (reclasificación a `1.110102.03`), o
   la contabilización ocurre en un post posterior?
2. ¿Qué representa exactamente la cuenta `1.110102.03`? (¿banco / giros
   remitidos / cuenta puente?)
3. ¿La entidad bancaria (`17`, etc.) determina a qué banco físico se remite?
4. El **siguiente paso** sería el **cobro del efecto** (el banco paga en la fecha
   de vencimiento): ¿cambia el estado `3 → X` y genera el asiento a Bancos?
