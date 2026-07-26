# Cheques posfechados — qué vamos a hacer (resumen para contabilidad)

Documento no técnico para el área contable. Explica **cómo funciona hoy** el
proceso de cheques posfechados en JD Edwards y **qué vamos a hacer** para
conectarlo con la app de control de caja y automatizar la conciliación.

## Cómo funciona hoy (resumen)

El cheque posfechado que recibe un local recorre 4 etapas en JDE:

| Etapa | Qué pasa | Documento / estado | Contabilidad |
|-------|----------|--------------------|--------------|
| 1. **Ingreso** | Se registra el cheque como *efecto* | `R1` · estado `4` | Debe *Cheques posfechados por cobrar* (`1.110209.02`) / Haber *CxC clientes* (`1.110205.01`) |
| 2. **Registro** | Se agrupan los cheques a enviar | (registro de efectos) | — |
| 3. **Envío al banco** | Se remiten los cheques (`R03B672`) | `R1`→`R2` · estado `4`→`3` | Debe *Consigna* (`1.110209.03`) / Haber *En cartera* (`1.110209.02`) |
| 4. **Cobro** | El banco los cobra (`R03B680`) | estado `3`→`0` | Debe *Bancos* / Haber *Consigna* (`1.110209.03`) |

En cada envío, JDE genera un **número de batch** que queda en el campo
**`Referencia 1`** de la conciliación bancaria (y como campo **`ICU`** en la
consulta de efectos). Ese número **identifica el lote depositado**.

## Qué vamos a hacer

1. **Conectar la app de control de caja (FinancePro)** con este proceso, para
   tener trazabilidad del cheque desde el local hasta el banco.
2. **Usar el número de batch de JDE** (el de `Referencia 1` / `ICU`) como
   **referencia del depósito** dentro de la app.
3. **Capturar el número de transacción que devuelve el banco** al depositar los
   cheques, para cruzarlo con el **estado de cuenta bancario**.
4. **Automatizar la conciliación**: cruzar los cheques (tabla `F03B13`) con el
   movimiento del banco (tabla `F0911`) usando el **documento `RC`** y el
   **número de batch**.

## Qué **no** cambia (importante)

- **No** cambia la forma de ingresar ni de contabilizar los cheques.
- **No** se crean cuentas contables nuevas ni tipos de documento nuevos.
- Usamos **campos que ya existen** hoy en JDE (número de batch / `Referencia 1` /
  `ICU`, y el documento `RC`).

## Qué necesitamos confirmar con contabilidad

1. Que el **número de batch** (`Referencia 1`) es **estable y único** por envío
   (que no se reutiliza ni se sobreescribe).
2. Que un **envío al banco** corresponde a **un solo depósito** (para poder
   cuadrar el total del batch contra el depósito del extracto).
3. *(Consulta aparte al banco)* si al depositar se puede registrar ese número
   como **referencia** que aparezca en el estado de cuenta.

## Beneficio

- **Trazabilidad completa:** cheque recibido en el local → efecto en JDE →
  depósito en el banco → conciliación, todo enlazado por el mismo número.
- **Menos conciliación manual** y menos errores de cuadre.
