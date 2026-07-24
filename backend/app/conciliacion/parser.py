"""Lectura y normalización de CSV a nuestro formato estándar.

Formato estándar (definido por nosotros) para un movimiento:
    {
        "fecha": date | None,
        "descripcion": str,
        "referencia": str,
        "clave": str,          # campo de vinculación (enlace libro <-> banco)
        "monto": Decimal,      # con signo; la conciliación puede usar |monto|
        "raw": dict,           # fila original (auditoría)
    }
"""

from __future__ import annotations

import csv
import io
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

# Formatos de fecha probados cuando el perfil no especifica uno.
_FORMATOS_FECHA = [
    "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%Y/%m/%d",
    "%d/%m/%y", "%m/%d/%y", "%d.%m.%Y", "%Y-%m-%d %H:%M:%S",
]


class ParserError(Exception):
    """Error al leer o mapear un CSV."""


# --------------------------------------------------------------------------- #
#  Decodificación y lectura
# --------------------------------------------------------------------------- #
def _decodificar(contenido: bytes, encoding: str | None) -> str:
    if encoding:
        return contenido.decode(encoding, errors="replace")
    for enc in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            return contenido.decode(enc)
        except UnicodeDecodeError:
            continue
    return contenido.decode("latin-1", errors="replace")


def _detectar_delimitador(muestra: str) -> str:
    try:
        dialecto = csv.Sniffer().sniff(muestra, delimiters=[",", ";", "\t", "|"])
        return dialecto.delimiter
    except csv.Error:
        # Heurística simple: el separador más frecuente en la primera línea.
        primera = muestra.splitlines()[0] if muestra.splitlines() else ""
        return max([",", ";", "\t", "|"], key=primera.count)


def leer_csv(
    contenido: bytes,
    *,
    delimitador: str | None = None,
    encoding: str | None = None,
    filas_omitir: int = 0,
) -> tuple[list[str], list[dict]]:
    """Devuelve (encabezados, filas) donde cada fila es un dict columna->valor."""
    texto = _decodificar(contenido, encoding)
    # Omitir filas iniciales (encabezados de reporte, títulos, etc.).
    if filas_omitir:
        lineas = texto.splitlines()
        texto = "\n".join(lineas[filas_omitir:])

    delim = delimitador or _detectar_delimitador(texto[:4096])
    lector = csv.reader(io.StringIO(texto), delimiter=delim)
    filas = [f for f in lector if any((c or "").strip() for c in f)]
    if not filas:
        return [], []

    encabezados = [h.strip() for h in filas[0]]
    registros = []
    for fila in filas[1:]:
        registro = {}
        for i, col in enumerate(encabezados):
            registro[col] = fila[i].strip() if i < len(fila) else ""
        registros.append(registro)
    return encabezados, registros


def inspeccionar(contenido: bytes, *, delimitador: str | None = None,
                 encoding: str | None = None, filas_omitir: int = 0,
                 n_muestra: int = 5) -> dict:
    """Detecta estructura del CSV para el entrenamiento de un perfil."""
    texto = _decodificar(contenido, encoding)
    if filas_omitir:
        texto = "\n".join(texto.splitlines()[filas_omitir:])
    delim = delimitador or _detectar_delimitador(texto[:4096])
    encabezados, registros = leer_csv(
        contenido, delimitador=delim, encoding=encoding, filas_omitir=filas_omitir
    )
    return {
        "delimitador": delim,
        "columnas": encabezados,
        "total_filas": len(registros),
        "muestra": registros[:n_muestra],
    }


# --------------------------------------------------------------------------- #
#  Parseo de números y fechas
# --------------------------------------------------------------------------- #
def parse_monto(
    valor, *, separador_decimal: str = ".", separador_miles: str | None = None
) -> Decimal:
    """Convierte un texto de importe a Decimal.

    Maneja símbolos de moneda, espacios, paréntesis (negativos), separadores de
    miles y decimales configurables.
    """
    if valor is None:
        return Decimal("0")
    s = str(valor).strip()
    if not s:
        return Decimal("0")

    negativo = False
    if s.startswith("(") and s.endswith(")"):
        negativo = True
        s = s[1:-1]

    # Conservar solo dígitos, signos y separadores.
    s = re.sub(r"[^0-9,.\-+]", "", s)
    if not s:
        return Decimal("0")

    if separador_miles:
        s = s.replace(separador_miles, "")
    if separador_decimal and separador_decimal != ".":
        s = s.replace(separador_decimal, ".")

    # Si quedaron comas (sin separador de miles declarado), tratarlas como decimal.
    if "," in s and "." not in s:
        s = s.replace(",", ".")
    else:
        s = s.replace(",", "")

    if s.count("-") > 0 and not s.startswith("-"):
        s = "-" + s.replace("-", "")

    try:
        monto = Decimal(s)
    except InvalidOperation:
        return Decimal("0")
    if negativo:
        monto = -monto
    return monto.quantize(Decimal("0.01"))


def parse_fecha(valor, *, formato: str | None = None) -> date | None:
    if valor is None:
        return None
    s = str(valor).strip()
    if not s:
        return None
    if formato:
        try:
            return datetime.strptime(s, formato).date()
        except ValueError:
            pass  # cae al autodetectado
    for fmt in _FORMATOS_FECHA:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


# --------------------------------------------------------------------------- #
#  Normalización según perfil
# --------------------------------------------------------------------------- #
def _col(fila: dict, nombre: str | None) -> str:
    if not nombre:
        return ""
    return (fila.get(nombre) or "").strip()


def normalizar_fila(fila: dict, perfil) -> dict:
    """Aplica el mapeo de un perfil a una fila cruda -> movimiento estándar."""
    dec = perfil.separador_decimal or "."
    mil = perfil.separador_miles

    if perfil.columna_monto:
        monto = parse_monto(_col(fila, perfil.columna_monto),
                            separador_decimal=dec, separador_miles=mil)
    else:
        debito = parse_monto(_col(fila, perfil.columna_debito),
                             separador_decimal=dec, separador_miles=mil)
        credito = parse_monto(_col(fila, perfil.columna_credito),
                              separador_decimal=dec, separador_miles=mil)
        monto = credito - debito  # crédito positivo, débito negativo

    if perfil.signo_invertido:
        monto = -monto

    referencia = _col(fila, perfil.columna_referencia)
    clave = _col(fila, perfil.columna_vinculacion) or referencia

    return {
        "fecha": parse_fecha(_col(fila, perfil.columna_fecha),
                             formato=perfil.formato_fecha),
        "descripcion": _col(fila, perfil.columna_descripcion),
        "referencia": referencia,
        "clave": clave,
        "monto": monto,
        "raw": fila,
    }


def normalizar(contenido: bytes, perfil) -> list[dict]:
    """Lee un CSV con un perfil y devuelve la lista de movimientos estándar."""
    _, filas = leer_csv(
        contenido,
        delimitador=perfil.delimitador,
        encoding=perfil.encoding,
        filas_omitir=perfil.filas_omitir or 0,
    )
    return [normalizar_fila(f, perfil) for f in filas]
