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
> `Batch`** (agrupador de la transacción contable) como referencia del depósito
> bancario. Ver [vinculacion-bancaria.md](vinculacion-bancaria.md).

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
  La **contabilización** es a nivel de **batch**, y el **nº de batch** es también
  la **referencia del depósito bancario** para la conciliación. Ver
  [vinculacion-bancaria.md](vinculacion-bancaria.md).

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

## Contabilización (reporte `R09801`, batch DB `671256`)

**Confirmado: la remesa sí genera asiento.** El post reclasifica cada efecto de
*posfechado ingreso* a *posfechado consigna* (una pareja de líneas por efecto):

| Doc | Cuenta | Descripción de la cuenta | Débito | Crédito |
|-----|--------|--------------------------|-------:|--------:|
| `R2` 54356 | `1.110209.03` | CXC cheque posfechado **CONSIGNA** | 666.00 | |
| `R1` 54356 | `1.110209.02` | CXC cheque posfechado **INGRESO** | | 666.00 |
| `R2` 54357 | `1.110209.03` | …CONSIGNA | 200.00 | |
| `R1` 54357 | `1.110209.02` | …INGRESO | | 200.00 |
| `R2` 54358 | `1.110209.03` | …CONSIGNA | 100.00 | |
| `R1` 54358 | `1.110209.02` | …INGRESO | | 100.00 |
| | | **Totales (tipo LM `AA`)** | **966.00** | **966.00** |

**Interpretación:** mueve el saldo **dentro** de "cheques posfechados por cobrar",
de la sub-cuenta **ingreso / en cartera (`1.110209.02`)** a **consigna /
remitido al banco (`1.110209.03`)**. Sigue **sin ser efectivo**: el cheque está
en el banco para cobro pero aún no se acredita.

> **Corrección:** la cuenta `1.110102.03` que aparece en el detalle operativo
> `R03B672` **no** es la del asiento; el post usa `1.110209.03`. Queda por aclarar
> qué representa `1.110102.03` (posible cuenta bancaria/operativa de la remesa).

## Relación con FinancePro

Corresponde al momento en que el **lote de cheques posfechados sale de Matriz
hacia el banco**. El **registro de efectos** y el **nº de giro** son los
identificadores del lote y de cada cheque — los **campos de vinculación** para
conciliar cuando el banco reporte el cobro (paso siguiente).

## Preguntas abiertas

1. ~~¿`R03B672` genera asiento?~~ **Confirmado:** sí — reclasifica
   `1.110209.02` (ingreso) → `1.110209.03` (consigna). Ver contabilización arriba.
2. ¿Qué representa `1.110102.03` (aparece en el detalle `R03B672` pero **no** en
   el asiento)? ¿Cuenta bancaria/operativa de la consigna?
3. ¿La entidad bancaria (`17`, etc.) determina a qué banco físico se remite?
4. El **siguiente paso** es el **cobro del efecto** (el banco paga en la fecha de
   vencimiento): ¿cambia el estado `3 → X` y genera el asiento a Bancos
   (Debe Bancos / Haber `1.110209.03`)?
