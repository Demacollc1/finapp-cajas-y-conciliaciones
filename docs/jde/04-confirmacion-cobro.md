# Paso 4 — Confirmación de cobro (cheque cobrado en el banco)

## Qué es

Cuando el banco confirma que los cheques posfechados fueron **cobrados**, se
corre el **reporte de confirmación de cheques posfechados**, que:

- Mueve cada efecto a **estado `0`** (cobrado / confirmado).
- Genera un **nuevo batch** (ej. `671259`).

Es el **cierre del ciclo** del efecto y el momento natural de la **conciliación
bancaria** (el banco confirma el depósito → se confirman los cheques).

## Estados del efecto (completo)

| Estado | Significado |
|:------:|-------------|
| `4` | Ingresado / aceptado (pasos 1–2) |
| `3` | Enviado al banco / remitido (paso 3) |
| **`0`** | **Cobrado / confirmado (este paso)** |

Progresión: **`4` → `3` → `0`**.

## Ejemplo (pantalla "Trabajo con efectos")

Los 3 efectos del registro pasan a **estado `0`**, batch **`671259`**:

| Cliente | Nº efecto | Estado | Batch | Importe |
|---------|-----------|:------:|:-----:|--------:|
| COMISARIATO DEL CONSTRUCTOR S.A. | *(anonimizado)* | `0` | `671259` | 666.00 |
| SEATEC S.A. | 667 | `0` | `671259` | 200.00 |
| MACOFE S.A. | 668 | `0` | `671259` | 100.00 |
| | | | **Total** | **966.00** |

## Contabilización (pendiente de confirmar)

Es el punto donde el saldo debería pasar de *consigna* (`1.110209.03`) a
**Bancos** (entra el efectivo). El reporte `R09801` adjunto corresponde al
**batch `671256`** (la remesa del [paso 3](03-envio-efectos-banco.md):
`1.110209.02` → `1.110209.03`), **no** al batch de confirmación **`671259`**.

> **Falta** el `R09801` del batch **`671259`** para ver el asiento del cobro.
> **Esperado:** `Debe Bancos / Haber 1.110209.03` (consigna → bancos).

## Relación con FinancePro / conciliación

Este es el momento en que el cheque se **concilia**: el banco confirma el cobro
(el depósito —referenciado por el **nº de batch**— aparece en el extracto) y se
corre la confirmación que cierra el efecto (estado `0`).

Es el **disparador natural del cruce automático** del conciliador: cuando el
extracto bancario trae el depósito con la referencia = nº de batch, el sistema
concilia el total contra los efectos de ese batch (modo **acumulador**) y esa
confirmación es la que llevaría los efectos a estado `0` en JDE.

## Ciclo contable completo

```
Paso 1  Ingreso   Debe 1.110209.02  / Haber 1.110205.01   (CxC → posfechado en cartera)
Paso 3  Envío     Debe 1.110209.03  / Haber 1.110209.02   (cartera → consigna banco)
Paso 4  Cobro     Debe Bancos       / Haber 1.110209.03   (consigna → bancos)  [esperado, batch 671259]
```

## Preguntas abiertas

1. ¿Qué **programa/reporte** ejecuta la confirmación de cheques posfechados?
   (¿colección/confirmación de efectos, tipo `R03B680`?)
2. ¿El batch **`671259`** genera el **asiento a Bancos**
   (`Debe Bancos / Haber 1.110209.03`)? → aportar el `R09801` de `671259`.
3. ¿La confirmación se **dispara desde la conciliación** (cuando el banco
   confirma el depósito) o es un proceso manual independiente?
4. ¿`Estado 0` = efecto **cerrado/cobrado definitivo**?
