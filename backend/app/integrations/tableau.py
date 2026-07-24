"""Cliente de integración con Tableau (ventas del sistema).

Objetivo: traer las ventas registradas en el sistema para conciliarlas contra
lo declarado en los cierres de caja.

Mientras no se configuren ``TABLEAU_BASE_URL`` y ``TABLEAU_TOKEN`` el cliente
opera en modo *simulado* y devuelve datos determinísticos, de modo que el resto
del sistema (y las pruebas) funcione sin depender del servicio real.

Para producción, implementar :meth:`_fetch_remoto` usando la Tableau REST API
(o el endpoint de datos VizQL) con ``httpx``.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from ..config import settings


class TableauClient:
    def __init__(self) -> None:
        self.base_url = settings.tableau_base_url
        self.token = settings.tableau_token
        self.site_id = settings.tableau_site_id

    @property
    def configurado(self) -> bool:
        return bool(self.base_url and self.token)

    def ventas_del_dia(self, dia: date) -> dict:
        """Devuelve las ventas del sistema para la fecha indicada."""
        if self.configurado:
            return self._fetch_remoto(dia)
        return self._simular(dia)

    # ------------------------------------------------------------------ #
    #  Implementación real (a completar en la fase de integración)
    # ------------------------------------------------------------------ #
    def _fetch_remoto(self, dia: date) -> dict:  # pragma: no cover - requiere red
        """Consulta la Tableau REST API.

        Ejemplo de esqueleto (requiere ``httpx`` y credenciales válidas)::

            import httpx
            headers = {"X-Tableau-Auth": self.token}
            url = f"{self.base_url}/api/3.21/sites/{self.site_id}/views/VENTAS/data"
            resp = httpx.get(url, headers=headers, params={"fecha": dia.isoformat()})
            resp.raise_for_status()
            filas = resp.json()["data"]
            ...
        """
        raise NotImplementedError(
            "Integración real con Tableau pendiente. "
            "Configure TABLEAU_BASE_URL/TABLEAU_TOKEN e implemente _fetch_remoto."
        )

    # ------------------------------------------------------------------ #
    #  Modo simulado
    # ------------------------------------------------------------------ #
    def _simular(self, dia: date) -> dict:
        base = datetime.combine(dia, datetime.min.time())
        ventas = [
            {"fecha": base.replace(hour=10), "canal": "POS", "monto": Decimal("450.00")},
            {"fecha": base.replace(hour=13), "canal": "TARJETA", "monto": Decimal("200.00")},
            {"fecha": base.replace(hour=15), "canal": "DE_UNA", "monto": Decimal("120.00")},
            {"fecha": base.replace(hour=19), "canal": "DELIVERY", "monto": Decimal("85.00")},
        ]
        total = sum((v["monto"] for v in ventas), Decimal("0"))
        return {
            "fuente": "TABLEAU (SIMULADO)",
            "fecha_consulta": base,
            "total_ventas": total,
            "ventas": ventas,
        }


tableau_client = TableauClient()
