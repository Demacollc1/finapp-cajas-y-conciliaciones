"""Datos de demostración que replican el estado inicial del front-end."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from .enums import EstadoValija, TipoCheque
from .models import Cheque, Valija

# Denominaciones del front-end (NOMENCLATURES_DEF) para reconstruir el desglose.
_DENOMS = [
    Decimal("20"), Decimal("10"), Decimal("5"), Decimal("1"), Decimal("1"),
    Decimal("0.50"), Decimal("0.25"), Decimal("0.10"), Decimal("0.05"), Decimal("0.01"),
]


def _nomenclaturas(counts: list[int]) -> list[dict]:
    return [
        {"denominacion": float(_DENOMS[i]), "cantidad": c}
        for i, c in enumerate(counts)
        if c > 0
    ]


_SEED = [
    {
        "id": "VAL-882910",
        "fecha": datetime(2026, 5, 11, 9, 15, 32),
        "usuario": "Cajero_01",
        "efectivo_total": Decimal("450.00"),
        "counts": [15, 10, 8, 10, 0, 0, 0, 0, 0, 0],
        "pago_tarjeta": Decimal("200"),
        "pago_de_una": Decimal("120"),
        "pago_delivery": Decimal("85"),
        "fondo_vuelto": Decimal("50.00"),
        "estado": EstadoValija.ENVIADA,
        "cheques": [
            ("PICHINCHA", Decimal("125.00"), TipoCheque.ESTANDAR, "882012"),
            ("PRODUBANCO", Decimal("300.00"), TipoCheque.POSFECHADO, "3102"),
        ],
    },
    {
        "id": "VAL-109283",
        "fecha": datetime(2026, 5, 10, 18, 20, 11),
        "usuario": "Cajero_02",
        "efectivo_total": Decimal("830.00"),
        "counts": [30, 15, 10, 30, 0, 0, 0, 0, 0, 0],
        "pago_tarjeta": Decimal("450"),
        "pago_de_una": Decimal("250"),
        "pago_delivery": Decimal("150"),
        "fondo_vuelto": Decimal("100.00"),
        "estado": EstadoValija.CUSTODIA,
        "cheques": [
            ("GUAYAQUIL", Decimal("650.00"), TipoCheque.ESTANDAR, "99120"),
        ],
    },
    {
        "id": "VAL-662510",
        "fecha": datetime(2026, 5, 9, 14, 10, 5),
        "usuario": "Cajero_01",
        "efectivo_total": Decimal("250.00"),
        "counts": [10, 5, 0, 0, 0, 0, 0, 0, 0, 0],
        "pago_tarjeta": Decimal("100"),
        "pago_de_una": Decimal("50"),
        "pago_delivery": Decimal("0"),
        "fondo_vuelto": Decimal("20.00"),
        "estado": EstadoValija.DEPOSITADA,
        "cheques": [],
    },
]


def seed(db: Session, *, forzar: bool = False) -> int:
    """Inserta las valijas de demostración si la tabla está vacía.

    Devuelve la cantidad de valijas insertadas.
    """
    existentes = db.execute(select(Valija.id)).scalars().all()
    if existentes and not forzar:
        return 0

    insertadas = 0
    for item in _SEED:
        if db.get(Valija, item["id"]) is not None:
            continue
        valija = Valija(
            id=item["id"],
            fecha=item["fecha"],
            usuario=item["usuario"],
            efectivo_total=item["efectivo_total"],
            nomenclaturas=_nomenclaturas(item["counts"]),
            pago_tarjeta=item["pago_tarjeta"],
            pago_de_una=item["pago_de_una"],
            pago_delivery=item["pago_delivery"],
            fondo_vuelto=item["fondo_vuelto"],
            estado=item["estado"],
            cheques=[
                Cheque(banco=b, monto=m, tipo=t, referencia=r)
                for (b, m, t, r) in item["cheques"]
            ],
        )
        db.add(valija)
        insertadas += 1
    db.commit()
    return insertadas
