# Decisión de diseño — Vinculación bancaria por registro de efectos (`DREG`)

## Regla

Usar el **número de registro de efectos** — campo **`DREG`** en `F03B13`
("Registro efectos", p. ej. `67124900001`) — como:

1. **Identificador del depósito en el banco** (número de referencia del depósito).
2. **Campo de vinculación** de la conciliación (JDE ↔ banco).
3. **Acumulador** del total depositado.

## Por qué

Un **registro agrupa varios cheques posfechados** en un solo envío/depósito, así
que el `DREG` actúa como acumulador. Del ejemplo del [paso 3](03-envio-efectos-banco.md):

| Registro (`DREG`) | Cheques del registro | Total del depósito |
|-------------------|----------------------|-------------------:|
| `67125300001` | SEATEC 200.00 + MACOFE 100.00 | **300.00** |
| `67124900001` | Comisariato 666.00 | **666.00** |

Si el banco refleja el `DREG` como **referencia interna del depósito**, el
extracto bancario traerá ese número y el cruce será **directo y exacto** por
`DREG`, sin depender de fechas ni montos aproximados.

## Acción pendiente — consultar al banco

- **Consultar si el banco permite asignar un número de referencia interno** al
  depósito de los cheques.
- Si es posible, **ese número debe ser el `DREG`**, para usarlo tanto en la
  conciliación como acumulador del depósito.
- Si el banco **no** lo permite, el cruce cae al modo por **monto agregado +
  fecha** (posible conciliación con aprobación humana).

## Implicación para el conciliador de FinancePro

El motor de conciliación actual cruza movimientos **1:1**. Para los
efectos/posfechados se necesita un modo **N:1 (acumulador)**:

1. **Agrupar (sumar)** los movimientos del **libro (JDE)** por `DREG`.
2. Cruzar ese **total** contra **un** movimiento del **banco** cuya referencia
   sea el `DREG`.
3. Clasificación:
   - **CONCILIADO**: el `DREG` coincide y el total del registro cuadra con el
     depósito.
   - **POSIBLE**: cuadra el monto agregado pero falta/─difiere el `DREG`
     (requiere aprobación humana).
   - **NO CONCILIADO**: sin contraparte.

> **Pendiente de implementar** en el módulo de conciliación: un "modo acumulador"
> que agrupe por campo clave (`DREG`) antes de cruzar. Hoy el motor cruza línea a
> línea; este modo permitiría conciliar **un depósito** contra **varios efectos**.

## Referencia del campo

- **`DREG`** = "Registro efectos" en `F03B13`.
- Formato: **nº de registro + compañía** (p. ej. `671249` + `00001` =
  `67124900001`).
