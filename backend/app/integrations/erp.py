"""Cliente de integración con el ERP (asiento contable).

Objetivo: al confirmar el depósito de una valija (estado DEPOSITADA), registrar
el asiento contable correspondiente usando el número de valija como referencia.

Mientras no se configuren ``ERP_BASE_URL`` y ``ERP_TOKEN`` el cliente opera en
modo *simulado*: construye el asiento y devuelve un identificador determinístico
sin llamar a ningún servicio externo.

Estructura contable del asiento generado:

    DEBE   Bancos                (efectivo + cheques estándar)
    DEBE   Cheques posfechados   (custodia matriz)
    HABER  Caja general          (total de valores)
"""

from __future__ import annotations

from decimal import Decimal

from ..config import settings


class ErpClient:
    def __init__(self) -> None:
        self.base_url = settings.erp_base_url
        self.token = settings.erp_token

    @property
    def configurado(self) -> bool:
        return bool(self.base_url and self.token)

    def registrar_asiento(self, valija) -> dict:
        """Registra el asiento contable de una valija depositada."""
        asiento = self._construir_asiento(valija)
        if self.configurado:
            return self._post_remoto(valija, asiento)
        return self._simular(valija, asiento)

    # ------------------------------------------------------------------ #
    #  Construcción del asiento (lógica de negocio, siempre local)
    # ------------------------------------------------------------------ #
    def _construir_asiento(self, valija) -> dict:
        banco = valija.monto_deposito_banco
        posfechado = valija.monto_custodia_matriz
        total = banco + posfechado

        movimientos = [
            {
                "cuenta": settings.erp_cuenta_bancos,
                "descripcion": f"Depósito valija {valija.id}",
                "debe": _f(banco),
                "haber": 0.0,
            },
        ]
        if posfechado > 0:
            movimientos.append(
                {
                    "cuenta": settings.erp_cuenta_posfechados,
                    "descripcion": f"Cheques posfechados en custodia {valija.id}",
                    "debe": _f(posfechado),
                    "haber": 0.0,
                }
            )
        movimientos.append(
            {
                "cuenta": settings.erp_cuenta_caja,
                "descripcion": f"Cierre de caja {valija.id} - {valija.usuario}",
                "debe": 0.0,
                "haber": _f(total),
            }
        )
        return {
            "referencia": valija.id,
            "glosa": f"Cierre de caja y depósito - Valija {valija.id}",
            "total": _f(total),
            "movimientos": movimientos,
        }

    # ------------------------------------------------------------------ #
    #  Implementación real (a completar en la fase de integración)
    # ------------------------------------------------------------------ #
    def _post_remoto(self, valija, asiento) -> dict:  # pragma: no cover - requiere red
        """Publica el asiento en el ERP.

        Ejemplo de esqueleto::

            import httpx
            headers = {"Authorization": f"Bearer {self.token}"}
            resp = httpx.post(f"{self.base_url}/api/asientos", json=asiento,
                              headers=headers)
            resp.raise_for_status()
            return {"asiento_id": resp.json()["id"], "estado": "REGISTRADO",
                    "detalle": asiento}
        """
        raise NotImplementedError(
            "Integración real con el ERP pendiente. "
            "Configure ERP_BASE_URL/ERP_TOKEN e implemente _post_remoto."
        )

    # ------------------------------------------------------------------ #
    #  Modo simulado
    # ------------------------------------------------------------------ #
    def _simular(self, valija, asiento) -> dict:
        # ID determinístico derivado del número de valija.
        asiento_id = f"AST-{valija.id.replace('VAL-', '')}"
        return {
            "asiento_id": asiento_id,
            "estado": "SIMULADO",
            "detalle": asiento,
        }


def _f(valor: Decimal) -> float:
    return float(valor)


erp_client = ErpClient()
