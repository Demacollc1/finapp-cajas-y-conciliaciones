"""Motor de cruce entre movimientos de libros (JDE) y bancos.

Estados que produce:
  * CONCILIADO: el campo de vinculación (clave) coincide y el monto cuadra.
  * POSIBLE: coincide monto+fecha (dentro de tolerancia) o la clave coincide
             pero el monto difiere -> requiere aprobación humana.
  * NO_CONCILIADO: sin contraparte.
"""

from __future__ import annotations

import re
from decimal import Decimal

_CENT = Decimal("0.01")


def _norm_clave(valor) -> str:
    """Normaliza una clave de vinculación para comparar (sin ceros/espacios)."""
    s = re.sub(r"\W", "", str(valor or "")).upper()
    return s.lstrip("0")


def _monto_cmp(m: dict, absoluto: bool) -> Decimal:
    v = m["monto"]
    return abs(v) if absoluto else v


def _montos_coinciden(a: dict, b: dict, absoluto: bool) -> bool:
    return _monto_cmp(a, absoluto).quantize(_CENT) == _monto_cmp(b, absoluto).quantize(_CENT)


def _similitud(a: str, b: str) -> float:
    """Jaccard de palabras (0..1) para desempatar posibles coincidencias."""
    ta = {w for w in re.split(r"\W+", (a or "").upper()) if w}
    tb = {w for w in re.split(r"\W+", (b or "").upper()) if w}
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def conciliar(
    libro: list[dict],
    banco: list[dict],
    *,
    tolerancia_dias: int = 3,
    comparar_absoluto: bool = True,
) -> dict:
    """Cruza dos listas de movimientos estándar.

    Devuelve:
      {
        "pares": [{"libro": i, "banco": j, "estado": str,
                   "motivo": str, "score": float}],
        "libro_no": [i, ...],
        "banco_no": [j, ...],
      }
    """
    n_l, n_b = len(libro), len(banco)
    libro_usado = [False] * n_l
    banco_usado = [False] * n_b
    pares: list[dict] = []

    # --- Fase 1: vinculación por clave (automático) ---
    banco_por_clave: dict[str, list[int]] = {}
    for j, b in enumerate(banco):
        k = _norm_clave(b["clave"])
        if k:
            banco_por_clave.setdefault(k, []).append(j)

    for i, l in enumerate(libro):
        k = _norm_clave(l["clave"])
        if not k:
            continue
        candidatos = [j for j in banco_por_clave.get(k, []) if not banco_usado[j]]
        if not candidatos:
            continue
        # Preferir el candidato cuyo monto cuadra.
        elegido = next(
            (j for j in candidatos if _montos_coinciden(l, banco[j], comparar_absoluto)),
            candidatos[0],
        )
        cuadra = _montos_coinciden(l, banco[elegido], comparar_absoluto)
        estado = "CONCILIADO" if cuadra else "POSIBLE"
        motivo = ("Vínculo por campo clave" if cuadra
                  else "Clave coincide pero el monto difiere")
        libro_usado[i] = True
        banco_usado[elegido] = True
        pares.append({"libro": i, "banco": elegido, "estado": estado,
                      "motivo": motivo, "score": 100.0})

    # --- Fase 2: posibles por monto + fecha (aprobación humana) ---
    candidatos: list[tuple[float, int, int, int]] = []
    for i, l in enumerate(libro):
        if libro_usado[i]:
            continue
        for j, b in enumerate(banco):
            if banco_usado[j]:
                continue
            if not _montos_coinciden(l, b, comparar_absoluto):
                continue
            if l["fecha"] and b["fecha"]:
                dd = abs((l["fecha"] - b["fecha"]).days)
            else:
                dd = tolerancia_dias  # sin fecha: se acepta al borde de la tolerancia
            if dd > tolerancia_dias:
                continue
            score = 100 - dd * 10 + _similitud(l["descripcion"], b["descripcion"]) * 20
            candidatos.append((score, i, j, dd))

    candidatos.sort(key=lambda c: c[0], reverse=True)
    for score, i, j, dd in candidatos:
        if libro_usado[i] or banco_usado[j]:
            continue
        libro_usado[i] = True
        banco_usado[j] = True
        pares.append({"libro": i, "banco": j, "estado": "POSIBLE",
                      "motivo": f"Monto y fecha coinciden (±{dd}d)",
                      "score": round(score, 1)})

    libro_no = [i for i in range(n_l) if not libro_usado[i]]
    banco_no = [j for j in range(n_b) if not banco_usado[j]]
    return {"pares": pares, "libro_no": libro_no, "banco_no": banco_no}
