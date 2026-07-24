# Paso 1 — Ingreso de cheques posfechados (efectos A/R)

## Qué es

Un cheque posfechado recibido de un cliente se registra en JD Edwards como un
**efecto / giro (draft)** dentro de **Cuentas por Cobrar (A/R)**. No es un cobro
en efectivo inmediato: es un instrumento de pago con fecha futura que sigue el
ciclo de vida de los efectos.

Confirmado por la exportación de ejemplo:

- **Tabla principal:** `F03B13` — *Cabecera de cobros/efectos* (Receipts/Drafts
  Header), unida con `F0101` (maestro de direcciones / cliente).
- **Programa de origen:** `P03B602` — *Entrada de efectos* (`ID programa`).
- **Instrumento de pago:** `Insto pago = F` (efecto).
- **Tipo de documento:** `R1` (documento de efecto de A/R).

## Los 4 objetos que se crean

Al ingresar el cheque posfechado, JDE genera:

| Objeto | Campo(s) en `F03B13` | Valor de ejemplo |
|--------|----------------------|------------------|
| **Documento R1** (el efecto) | `A/D tipo doc` + `A/D nº doc` + `A/D cía doc` | `R1` · `54356` · `00001` |
| **ID de pago** | `ID pago` | `389969` |
| **Batch** | `Tipo batch` + `Número batch` + `Fecha batch` | `DB` · `671247` · `24/07/26` |
| **Número de efecto** | `Número cobro` | `NUMEROEFECTOCPOSFECHADO` *(anonimizado)* |

> El **tipo de batch `DB`** corresponde a efectos; el **documento `R1`** es el
> efecto aceptado. *(Ambos a confirmar con su configuración de JDE.)*

## Datos clave del registro (ejemplo)

| Concepto | Campo | Valor |
|----------|-------|-------|
| Cliente | `Nº direc` / `Nombre alfabético [F0101]` | `23789` · COMISARIATO DEL CONSTRUCTOR S.A. |
| RUC/ID fiscal | `ID fiscal [F0101]` | `0992708328001` |
| Importe del cheque | `Importe cheque` | `666.00` |
| Moneda | `Cd mon` / `Mon base` | `USD` / `USD` |
| Fecha del cheque/ítem | `F cheque/ ítem` | `22/07/26` |
| Fecha contable (Libro Mayor) | `Fecha LM` | `24/07/26` |
| Fecha de liquidación | `Fecha liqd` | `24/07/26` |
| Período contable | `Siglo`+`AF`+`Nº per` | siglo 20, AF 26, período 7 → **julio 2026** |
| Compañía | `Cía` | `00001` |
| Estado del efecto | `E E` | `4` *(etapa del ciclo — a confirmar)* |
| Banco / entidad del cliente | `Entidad bancaria`, `Nº cuenta bancaria cliente` | *(anonimizados)* |
| Observación | `Explicación -observación-` | *(nombre del banco)* |
| Auditoría | `ID usuario` · `Hora actz` · `ID estn trabajo` | `ROBGOMEZ` · `13:31:06` · `SVRE1DAPP` |

## Contabilización (reporte R09801)

Al **contabilizar el batch** (`DB 671247`), JDE ejecuta el post del Libro Mayor
(`R09801`) y genera el asiento contable. Este es el asiento del ejemplo:

| Doc | Tipo | Cuenta | Descripción de la cuenta | Débito | Crédito |
|-----|------|--------|--------------------------|-------:|--------:|
| `54356` | **R1** | `1.110209.02` | Efectos / Cheques posfechados por cobrar (*"Cobro efecto — CXC CHEQUE POSFECHADO INGRESO"*) | 666.00 | |
| `54356` | **AE** | `1.110205.01` | Cuentas por cobrar clientes (*"Compen. por doc RC 0054356"*) | | 666.00 |
| | | | **Totales (tipo LM `AA`)** | **666.00** | **666.00** |

**Interpretación contable:** es una **reclasificación dentro del activo** de
Cuentas por Cobrar. El asiento **debita** la cuenta de efectos/cheques
posfechados (`1.110209.02`) y **acredita** la CxC comercial (`1.110205.01`): el
saldo del cliente deja de estar como "factura por cobrar" y pasa a estar
representado por el efecto (el cheque en cartera). **No se registra efectivo ni
ingreso** — es coherente con que el cheque aún no se cobra (posfechado).

Notas:
- El documento **`R1`** es el efecto (lado débito); el **`AE`** (*asiento
  automático*) es la contrapartida generada por el post a la CxC.
- Las cuentas (`1.110209.02`, `1.110205.01`) las determinan las **AAIs**
  (instrucciones de contabilización automática) de efectos — dato clave para
  configurar/validar la automatización.
- El post confirma que además de `F03B13` se afectan las tablas de LM:
  **`F0911`** (detalle de asientos) y **`F0902`** (saldos de cuentas).

## Relación con FinancePro

En el flujo de FinancePro, los cheques marcados **POSFECHADO** se consolidan
para envío a **Matriz**. Este paso es lo que ocurre en Matriz al recibirlos:
cada cheque posfechado se registra como un **efecto R1** en JDE. El **número de
efecto** (o el documento `R1`) es el candidato natural para el **campo de
vinculación** de la conciliación cuando el cheque finalmente se cobre en el banco.

## Consideraciones para automatizar

El ingreso hoy se hace por el programa interactivo `P03B602`. Para automatizarlo,
las vías habituales en JDE (de más a menos recomendable) son:

1. **Interface por lotes (recomendada):** poblar la tabla de interface de cobros
   `F03B13Z1` (y detalle relacionado) y ejecutar el UBE de actualización
   (`R03B551` / proceso de efectos). JDE valida, asigna next numbers y genera
   los asientos. Es la vía soportada y segura.
2. **Orchestrator / AIS REST API:** invocar la entrada de efectos vía
   Orchestrator, reutilizando las validaciones del programa. Requiere AIS Server.
3. **Inserción directa en tablas** (`F03B13`, `F03B14`, `F0911`…): **no
   recomendada** — omite validaciones, next numbers y asientos de LM, y puede
   descuadrar la contabilidad.

## Preguntas abiertas (para el siguiente análisis)

1. ¿El ingreso actual es **manual uno por uno** en `P03B602`, o ya cargan por
   algún archivo/interface?
2. ¿Tienen disponible **Orchestrator / AIS REST** en su instalación de JDE?
   (Define la vía de automatización.)
3. ¿El efecto se **aplica contra una factura** existente (`F03B11`) o entra como
   efecto **a cuenta / no aplicado**?
4. ¿El **número de efecto** lo asigna JDE (next numbers) o proviene del número
   del cheque físico?
5. Tablas afectadas: el post (`R09801`) **confirma** que se escriben `F0911`
   (asientos) y `F0902` (saldos). Falta confirmar si también se tocan `F03B14`
   (detalle de aplicación) y `F03B11` (factura), lo que depende de la pregunta 3.
6. ¿Las cuentas `1.110209.02` (efectos) y `1.110205.01` (CxC clientes) están
   fijadas por **AAI**? ¿Qué AAI/renglón las controla? (Para replicar la
   parametrización al automatizar.)
