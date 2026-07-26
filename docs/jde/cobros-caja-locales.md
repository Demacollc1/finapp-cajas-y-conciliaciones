# Cobros en caja de los locales → depósito al banco (asiento `CZ`)

Flujo **de efectivo** (distinto al de cheques posfechados / efectos): cómo se
registran contablemente los cobros en caja de cada local y su depósito al banco.

## Proceso

### Paso 1 — Recibo manual de cobro (`P03B102`)
- Se ingresa un **"Recibo manual de cobro"** en la aplicación **`P03B102`**.
- El cobro se refleja en la cuenta **Caja General de cada local** (por unidad de
  negocio / sucursal).

### Paso 2 — Envío de los cobros al depósito (asiento `CZ`)
- Se envían los cobros al **depósito al banco**.
- Se realiza un **asiento contable con tipo de documento `CZ`** que **saca los
  valores de Caja General y los envía al banco**.
- Movimiento esperado: **Debe Bancos / Haber Caja General**.

## Observación (tabla JE — asientos de diario)

- En **Izamba** se generan asientos **`CZ`** para mover de Caja General al banco.

## Preguntas para el departamento contable (a consultar)

Con **hipótesis de trabajo** para guiar la consulta (a validar, no confirmadas):

1. **¿Por qué no hay transacciones `CZ` de otras sucursales además de Izamba?**
   *Hipótesis:* las demás sucursales podrían (a) usar **otro tipo de documento o
   proceso** (depósito directo sin pasar por Caja General), (b) tener el depósito
   **centralizado/automático**, o (c) **no registrar** ese movimiento en JDE
   (control manual/externo).

2. **¿Por qué las `CZ` parecen hacerse por transacción y no por el valor completo
   del depósito?**
   *Hipótesis:* el asiento se genera **por cada recibo/cobro individual** en vez
   de **consolidar el depósito**. Esto dificulta conciliar contra **un** depósito
   bancario (que es el total del día/lote).

3. **¿En qué momento y quién hace los asientos al enviar los depósitos al banco?**
   *Hipótesis:* podría ser **manual** (tesorería/contabilidad al preparar el
   depósito) o **automático** al contabilizar. Definirlo es clave para saber
   **dónde inyectar la referencia del depósito**.

4. **¿Cómo se controla el valor depositado vs. el valor del asiento?**
   *Hipótesis:* hoy sería un **cuadre manual** (comparar el total depositado con
   la suma de `CZ`). Es justo donde nuestra app + conciliación agregarían valor
   (acumulador + referencia de depósito).

## Objetivo (próximo desarrollo)

- **Vincular** la app de cierre de caja (FinancePro) con el **asiento contable**.
- Identificar **en qué parte del proceso** y **en qué campo** referenciar el
  **número de depósito del banco** con el ERP (análogo al batch/`Referencia 1`
  del flujo de posfechados).

## Relación con FinancePro

- El **efectivo del cierre de caja** (la valija) **=** los cobros en **Caja
  General** del local.
- Al depositar, el **`CZ`** mueve de **Caja General → Bancos**: es el equivalente
  real del asiento que hoy simula el conector ERP (`app/integrations/erp.py`).
- **Punto de enganche:** el **número de depósito del banco** (como el
  nº de transacción / batch de los posfechados) debería quedar en un **campo del
  asiento `CZ`** (p. ej. `Referencia`) para poder conciliar.

## Datos que ayudarían a confirmar (para el siguiente análisis)

- Volcado de la tabla **JE / `F0911`** filtrado por **tipo de documento `CZ`**
  (varias sucursales, varios días).
- Un ejemplo de **recibo** (`P03B102`) con su **asiento** resultante.
- Idealmente, un caso donde se vea **un depósito** y **sus varias `CZ`** (para
  responder la pregunta 2).
