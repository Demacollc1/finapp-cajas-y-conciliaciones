"""Pruebas unitarias del parser y del motor de cruce (sin base de datos)."""

from datetime import date
from decimal import Decimal

from app.conciliacion import matcher
from app.conciliacion.parser import parse_fecha, parse_monto


# --------------------------- parse_monto ---------------------------------- #
def test_parse_monto_us():
    assert parse_monto("1,234.56", separador_decimal=".", separador_miles=",") == Decimal("1234.56")


def test_parse_monto_europeo():
    assert parse_monto("1.234,56", separador_decimal=",", separador_miles=".") == Decimal("1234.56")


def test_parse_monto_coma_decimal_simple():
    assert parse_monto("450,00", separador_decimal=",") == Decimal("450.00")


def test_parse_monto_parentesis_negativo():
    assert parse_monto("(120.00)", separador_decimal=".") == Decimal("-120.00")


def test_parse_monto_con_simbolo():
    assert parse_monto("$ 1.000,50", separador_decimal=",", separador_miles=".") == Decimal("1000.50")


def test_parse_monto_vacio():
    assert parse_monto("") == Decimal("0")


# --------------------------- parse_fecha ---------------------------------- #
def test_parse_fecha_formato_explicito():
    assert parse_fecha("11/05/2026", formato="%d/%m/%Y") == date(2026, 5, 11)


def test_parse_fecha_autodetecta():
    assert parse_fecha("2026-05-11") == date(2026, 5, 11)


def test_parse_fecha_invalida():
    assert parse_fecha("no-es-fecha") is None


# ------------------------------ matcher ----------------------------------- #
def _mov(fecha, monto, clave="", desc=""):
    return {"fecha": fecha, "monto": Decimal(str(monto)), "clave": clave,
            "referencia": clave, "descripcion": desc}


def test_conciliado_por_clave():
    libro = [_mov(date(2026, 5, 11), 450, "DOC1")]
    banco = [_mov(date(2026, 5, 11), 450, "DOC1")]
    r = matcher.conciliar(libro, banco)
    assert len(r["pares"]) == 1
    assert r["pares"][0]["estado"] == "CONCILIADO"
    assert not r["libro_no"] and not r["banco_no"]


def test_posible_por_monto_y_fecha_sin_clave():
    libro = [_mov(date(2026, 5, 8), 120, "")]
    banco = [_mov(date(2026, 5, 8), 120, "")]
    r = matcher.conciliar(libro, banco)
    assert r["pares"][0]["estado"] == "POSIBLE"


def test_clave_coincide_monto_difiere_es_posible():
    libro = [_mov(date(2026, 5, 8), 120, "DOC9")]
    banco = [_mov(date(2026, 5, 8), 130, "DOC9")]
    r = matcher.conciliar(libro, banco)
    assert r["pares"][0]["estado"] == "POSIBLE"
    assert "monto difiere" in r["pares"][0]["motivo"].lower()


def test_valor_absoluto_cruza_signos_opuestos():
    libro = [_mov(date(2026, 5, 8), 120, "")]
    banco = [_mov(date(2026, 5, 8), -120, "")]
    r = matcher.conciliar(libro, banco, comparar_absoluto=True)
    assert r["pares"][0]["estado"] == "POSIBLE"
    # Con signo estricto no debería cruzar.
    r2 = matcher.conciliar(libro, banco, comparar_absoluto=False)
    assert not r2["pares"]


def test_fuera_de_tolerancia_no_cruza():
    libro = [_mov(date(2026, 5, 1), 120, "")]
    banco = [_mov(date(2026, 5, 20), 120, "")]
    r = matcher.conciliar(libro, banco, tolerancia_dias=3)
    assert not r["pares"]
    assert r["libro_no"] == [0] and r["banco_no"] == [0]


def test_no_conciliado_en_ambos_lados():
    libro = [_mov(date(2026, 5, 7), 75.50, "DOC5")]
    banco = [_mov(date(2026, 5, 5), 500, "DOC9")]
    r = matcher.conciliar(libro, banco)
    assert not r["pares"]
    assert r["libro_no"] == [0]
    assert r["banco_no"] == [0]
