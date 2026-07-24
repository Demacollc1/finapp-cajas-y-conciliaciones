"""Enumeraciones del dominio y reglas de transición de estados."""

from enum import Enum


class EstadoValija(str, Enum):
    """Ciclo de vida de una valija.

    ENVIADA    -> Cerrada en el local, lista para ser recolectada.
    CUSTODIA   -> En tránsito con el mensajero (traspaso validado por QR).
    DEPOSITADA -> Cierre final confirmado con foto de la papeleta sellada.
    """

    ENVIADA = "ENVIADA"
    CUSTODIA = "CUSTODIA"
    DEPOSITADA = "DEPOSITADA"


class TipoCheque(str, Enum):
    """Segregación de cheques.

    ESTANDAR   -> Se depositan al banco junto con el efectivo (papeleta bancaria).
    POSFECHADO -> Se consolidan para envío a la Matriz central (custodia).
    """

    ESTANDAR = "ESTANDAR"
    POSFECHADO = "POSFECHADO"


# Transiciones permitidas dentro del ciclo de custodia.
# Cualquier salto no declarado aquí se rechaza (p.ej. ENVIADA -> DEPOSITADA).
TRANSICIONES_VALIDAS: dict[EstadoValija, set[EstadoValija]] = {
    EstadoValija.ENVIADA: {EstadoValija.CUSTODIA},
    EstadoValija.CUSTODIA: {EstadoValija.DEPOSITADA},
    EstadoValija.DEPOSITADA: set(),
}


def transicion_permitida(actual: EstadoValija, destino: EstadoValija) -> bool:
    """Indica si se puede pasar de ``actual`` a ``destino``."""
    return destino in TRANSICIONES_VALIDAS.get(actual, set())
