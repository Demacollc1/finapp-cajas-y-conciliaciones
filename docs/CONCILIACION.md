# Conciliación de Cuentas (JD Edwards ↔ Bancos)

Módulo que cruza las transacciones de **JD Edwards** (libros) contra los
**estados de cuenta de los bancos**, normalizando cada archivo a un formato
estándar y clasificando cada movimiento.

## Flujo

```
1. CSV JD Edwards ─┐
                   ├─► Normalización por PERFIL ─► Formato estándar ─► CRUCE ─► Resultado
2. CSV Bancos ─────┘        (entrenable)                                         (3 estados)
```

1. **Descargar** de JD Edwards el CSV detallado (no consolidado) y subirlo.
2. **Descargar** los CSV de cada banco y subirlos (uno o varios a la vez).
3. Cada banco tiene una **estructura distinta**; el sistema aplica un **perfil de
   mapeo** (entrenado una vez) para llevarlo al formato estándar.
4. Se realiza el **cruce** y se clasifican los movimientos.

## Los tres estados del cruce

| Estado | Cómo se determina | Acción |
|--------|-------------------|--------|
| **CONCILIADO** | El **campo de vinculación** (clave, p. ej. Nº de documento) coincide en ambos archivos **y** el monto cuadra (valor absoluto). | Automático |
| **POSIBLE** | Coinciden **monto y fecha** (dentro de la tolerancia de días) pero no hay vínculo confirmado — o la clave coincide pero el monto difiere. | **Requiere aprobación humana** (Aprobar / Rechazar) |
| **NO CONCILIADO** | Sin contraparte. | Revisión manual |

Los montos se comparan por **valor absoluto** (un depósito de 100 en JDE cruza
con 100 en el banco aunque uno figure como débito y el otro como crédito).

## Entrenamiento de un perfil

La primera vez que aparece un banco (o para JDE) se crea un **perfil** que define
cómo leer su CSV. En la UI: *Conciliación → Perfiles → + Entrenar*.

Campos del perfil:

| Campo | Descripción |
|-------|-------------|
| `tipo` | `LIBRO` (JDE) o `BANCO` |
| `delimitador` | `,` `;` `\t` `|` — se autodetecta si se omite |
| `filas_omitir` | Filas de encabezado del reporte a saltar antes de la tabla |
| `columna_fecha` + `formato_fecha` | Columna de fecha y su formato (`%d/%m/%Y`, `%Y-%m-%d`, …) |
| `columna_descripcion` | Concepto/glosa |
| **`columna_vinculacion`** | **Campo clave que enlaza libro ↔ banco** (Nº documento/referencia) |
| `columna_monto` **o** `columna_debito`+`columna_credito` | Importe en una columna con signo, o débito/crédito separados (monto = crédito − débito) |
| `separador_decimal` / `separador_miles` | `.` o `,` (soporta formatos US y europeo) |
| `signo_invertido` | Invierte el signo del importe si el banco lo reporta al revés |

## Archivos de ejemplo

En este directorio hay CSV listos para probar (coinciden con los perfiles
sembrados por defecto):

- `ejemplo_jde.csv` — libros (JD Edwards), formato US, delimitador `,`.
- `ejemplo_banco_pichincha.csv` — delimitador `;`, decimales con coma, columnas Débito/Crédito.
- `ejemplo_banco_produbanco.csv` — formato US, monto en una columna.

Cruzándolos (tolerancia 3 días) se obtiene: **3 conciliados** (por clave),
**1 posible** (coincide monto y fecha, sin clave), **1 no conciliado en libros**
y **2 no conciliados en bancos**.

## Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| `POST` | `/api/conciliacion/perfiles/inspeccionar` | Detecta columnas/delimitador de un CSV (para entrenar) |
| `POST` | `/api/conciliacion/perfiles` | Crear perfil de mapeo |
| `GET` / `PUT` / `DELETE` | `/api/conciliacion/perfiles/{id}` | Consultar / actualizar / eliminar |
| `POST` | `/api/conciliacion/ejecutar` | Cruzar un CSV de JDE contra uno o más CSV de bancos (multipart) |
| `GET` | `/api/conciliacion` | Listar corridas |
| `GET` | `/api/conciliacion/{id}` | Detalle (conciliados, posibles, no conciliados) |
| `POST` | `/api/conciliacion/{id}/movimientos/{mid}/aprobar` | Aprobar una posible → CONCILIADO |
| `POST` | `/api/conciliacion/{id}/movimientos/{mid}/rechazar` | Rechazar una posible → NO CONCILIADO |

En `/ejecutar`, el perfil de cada banco se **autodetecta** por sus columnas; si
un archivo es ambiguo o nuevo, se indica con `banco_perfil_ids` (alineado a los
archivos) o se entrena primero.
