"""Perfiles de demostración para la conciliación (JDE + dos bancos).

Coinciden con los CSV de ejemplo en docs/ (ejemplo_jde.csv,
ejemplo_banco_pichincha.csv, ejemplo_banco_produbanco.csv), de modo que el
módulo se puede probar de extremo a extremo sin entrenamiento manual.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..enums import TipoPerfil
from .models import PerfilBanco

_PERFILES = [
    dict(
        nombre="JD Edwards (Libro)",
        tipo=TipoPerfil.LIBRO,
        delimitador=",",
        columna_fecha="Fecha",
        formato_fecha="%Y-%m-%d",
        columna_descripcion="Descripcion",
        columna_referencia="Documento",
        columna_vinculacion="Documento",
        columna_monto="Monto",
        separador_decimal=".",
        separador_miles=",",
        signo_invertido=False,
    ),
    dict(
        nombre="Banco Pichincha",
        tipo=TipoPerfil.BANCO,
        delimitador=";",
        columna_fecha="FECHA",
        formato_fecha="%d/%m/%Y",
        columna_descripcion="CONCEPTO",
        columna_referencia="REFERENCIA",
        columna_vinculacion="REFERENCIA",
        columna_debito="DEBITO",
        columna_credito="CREDITO",
        separador_decimal=",",
        separador_miles=".",
        signo_invertido=False,
    ),
    dict(
        nombre="Banco Produbanco",
        tipo=TipoPerfil.BANCO,
        delimitador=",",
        columna_fecha="Date",
        formato_fecha="%m/%d/%Y",
        columna_descripcion="Description",
        columna_referencia="Doc",
        columna_vinculacion="Doc",
        columna_monto="Amount",
        separador_decimal=".",
        separador_miles=",",
        signo_invertido=False,
    ),
]


def seed_perfiles(db: Session) -> int:
    """Inserta los perfiles de demostración si no existen."""
    existentes = db.execute(select(PerfilBanco.id)).first()
    if existentes:
        return 0
    insertados = 0
    for datos in _PERFILES:
        db.add(PerfilBanco(**datos))
        insertados += 1
    db.commit()
    return insertados
