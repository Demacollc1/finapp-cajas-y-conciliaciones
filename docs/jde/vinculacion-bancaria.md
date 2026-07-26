# Decisión de diseño — Referencia y vinculación bancaria

## Regla (revisada)

Usar el **número de `Batch`** — el agrupador de la **transacción contable** del
envío al banco (p. ej. `671256`) — como:

1. **Número de referencia del depósito en el banco.**
2. **Campo de vinculación** de la conciliación (JDE ↔ banco).
3. **Acumulador** del total depositado.

> **Nota de evolución:** primero se consideró el `DREG` (registro de efectos)
> como referencia; tras analizar la jerarquía, se concluye que el **`Batch`** es
> el agrupador correcto, porque **es el nivel de la transacción contable** (un
> `Batch` puede contener varios `DREG`) y así el depósito bancario cuadra 1:1 con
> el asiento (`R09801`).

> **⚠️ Ojo — hay dos batches distintos** (ver
> [cruce-f0911-f03b13.md](cruce-f0911-f03b13.md)):
> - **Batch de ENVÍO** (remesa `R03B672`, p. ej. `2940589`): el depósito físico;
>   es lo que ve el **extracto del banco**. Es el que debería ir como referencia
>   en el banco.
> - **Batch de COBRO** (`R03B680`, p. ej. `2940597`): el asiento interno de banco;
>   es el que aparece en **`F0911R`** (la conciliación interna de JDE).
>
> El batch de envío **no** está en `F0911R`. Para conciliar internamente se
> agrupa por el batch de cobro o por el documento `RC`; falta confirmar si un
> batch de envío se cobra siempre en un único batch de cobro.

## Dónde vive el batch en JDE (aliases confirmados)

| Programa / pantalla | Campo | Alias | Tabla |
|---------------------|-------|:-----:|-------|
| **`P09131` / `W09131A`** (conciliación bancaria manual) | `Referencia 1` | **`R1`** | `F0911` |
| **`P03B602` / `W03B602A`** (consulta de efectos) | `Número batch` | **`ICU`** | `F03B13` |

Al **enviar el cheque al banco**, JDE registra el **nº de batch** en
`Referencia 1` (`R1`) de la conciliación manual; y en la consulta de efectos ese
mismo batch es el campo `ICU`.

## ✅ Decisión para la app de control

**El número de batch de JDE es el "número de referencia de valija de depósito"**
de FinancePro. Se captura al registrar el envío de posfechados al banco y es la
llave para cruzar la conciliación (junto con el nº de transacción del banco que
devuelve el depósito).

## Jerarquía de agrupación (3 niveles)

```
BATCH  (transacción contable = referencia bancaria, p. ej. 671256)  → total 966.00
 ├─ DREG 671249  (registro de efectos)  → 1 efecto  = 666.00
 └─ DREG 671253  (registro de efectos)  → 2 efectos = 300.00
```

| Nivel | Objeto | Rol |
|-------|--------|-----|
| **Batch** | Nº de batch (`671256`) | **Transacción contable** (post `R09801`) y **referencia del depósito bancario / campo de vinculación**. |
| `DREG` | Registro de efectos (`671249`, `671253`) | Sub-agrupación por registro/banco dentro del batch. |
| Efecto | Cheque individual (giro) | El cheque posfechado, con su nº de efecto y monto. |

## Por qué el `Batch`

- El **post contable `R09801` se hace por batch** (batch `671256` = 966.00 total).
  Si el depósito bancario lleva el nº de batch como referencia, **el depósito
  cuadra 1:1 con la transacción contable**.
- El batch **acumula** todos los efectos (a través de sus `DREG`): el total del
  depósito = suma de los efectos del batch.
- Es un identificador **único** por envío, ideal como llave de cruce.

## Acción pendiente — consultar al banco

**Pregunta concreta a confirmar con el banco:**

> Al depositar los cheques en la **máquina de cheques (depósito automático)**,
> ¿se permite **ingresar un número de referencia** que aparezca **dentro del
> estado de cuenta bancario**, para poner ahí el **número de batch de JD
> Edwards**?

- Si **sí** → ese número de referencia **debe ser el nº de `Batch`**, y el cruce
  de la conciliación será **directo y exacto** por batch.
- Si **no** → el cruce cae al modo por **monto agregado + fecha** (posible
  conciliación con aprobación humana), y habría que evaluar otro identificador
  que sí viaje al extracto (p. ej. el nº de depósito de la máquina).

## Plan B (implementado en la app) — capturar el nº de transacción del banco

Independientemente de si el banco permite llevar **nuestra** referencia (el nº de
batch), el banco **sí devuelve un número de transacción** al depositar los
cheques. FinancePro **ya registra el envío físico de posfechados** y **captura
ese número** (sección *Posfechados*):

- Se seleccionan los cheques `POSFECHADO` pendientes y se registra la remesa al
  banco (`POST /posfechados/remesas`).
- Se guarda el **`numero_transaccion_banco`** que devuelve el banco (al momento o
  después, vía `POST /posfechados/remesas/{id}/transaccion`).
- Opcionalmente se anota la **`referencia_jde`** (nº de batch) para atar ambos
  mundos.

Ese **número de transacción del banco** viaja seguro al estado de cuenta, así que
es un **campo de vinculación confiable** para la conciliación de posfechados —
sirva o no la referencia del batch.

## Implicación para el conciliador de FinancePro

El motor de conciliación actual cruza movimientos **1:1**. Para los
efectos/posfechados se necesita un modo **N:1 (acumulador)**:

1. **Agrupar (sumar)** los movimientos del **libro (JDE)** por **nº de `Batch`**.
2. Cruzar ese **total** contra **un** movimiento del **banco** cuya referencia
   sea el nº de batch.
3. Clasificación:
   - **CONCILIADO**: el batch coincide y el total cuadra con el depósito.
   - **POSIBLE**: cuadra el monto agregado pero falta/difiere el batch
     (requiere aprobación humana).
   - **NO CONCILIADO**: sin contraparte.

> **Pendiente de implementar** en el módulo de conciliación: un "modo acumulador"
> que agrupe por un **campo clave configurable** (nº de batch, con `DREG` como
> alternativa) antes de cruzar, para conciliar **un depósito** contra **varios
> efectos**.

## Referencia de campos

- **`Batch`** — nº de batch de la remesa/envío (p. ej. `671256`); agrupador
  contable y **referencia bancaria recomendada**.
- **`DREG`** — "Registro efectos" en `F03B13` (p. ej. `67124900001` = registro
  `671249` + compañía `00001`); sub-agrupación por registro/banco.
