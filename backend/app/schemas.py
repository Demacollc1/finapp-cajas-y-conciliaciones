"""Esquemas Pydantic: contrato de entrada/salida de la API.

El contrato sigue el JSON canónico compartido por el front-end (snake_case):

    {
      "valija_id": "VAL-882910",
      "fecha": "2026-05-11T09:15:32",
      "usuario": "Cajero_01",
      "efectivo_total": 450.00,
      "nomenclaturas": [{"denominacion": 20.00, "cantidad": 15}],
      "pagos_adicionales": {"tarjeta": 200.00, "de_una": 120.00, "delivery": 85.00},
      "fondo_vuelto": 50.00,
      "cheques": [{"banco": "PICHINCHA", "monto": 125.00,
                   "tipo": "ESTANDAR", "referencia": "882012"}],
      "estado": "ENVIADA"
    }
"""

from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer, field_validator

from .enums import EstadoValija, TipoCheque

# Tipo monetario: se opera con Decimal (exacto) pero se serializa a número JSON.
Money = Annotated[
    Decimal,
    PlainSerializer(lambda v: float(v), return_type=float, when_used="json"),
]


# --------------------------------------------------------------------------- #
#  Sub-estructuras
# --------------------------------------------------------------------------- #
class Nomenclatura(BaseModel):
    """Una denominación y su cantidad contada."""

    denominacion: Money
    cantidad: int = Field(ge=0)


class PagosAdicionales(BaseModel):
    """Pagos electrónicos declarados en el cierre."""

    tarjeta: Money = Decimal("0")
    de_una: Money = Decimal("0")
    delivery: Money = Decimal("0")


class ChequeBase(BaseModel):
    banco: str = Field(min_length=1, max_length=80)
    monto: Money = Field(gt=0)
    tipo: TipoCheque
    referencia: str = Field(min_length=1, max_length=60)


class ChequeOut(ChequeBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


# --------------------------------------------------------------------------- #
#  Valija: entrada
# --------------------------------------------------------------------------- #
class ValijaCreate(BaseModel):
    """Datos para crear un cierre de caja (nace en estado ENVIADA)."""

    usuario: str = Field(min_length=1, max_length=80)
    fecha: datetime | None = None
    # Si no se envía, se calcula a partir de las nomenclaturas.
    efectivo_total: Money | None = None
    nomenclaturas: list[Nomenclatura] = Field(default_factory=list)
    pagos_adicionales: PagosAdicionales = Field(default_factory=PagosAdicionales)
    fondo_vuelto: Money = Decimal("0")
    cheques: list[ChequeBase] = Field(default_factory=list)
    # Permite fijar un ID desde el cliente; si se omite, el servidor lo genera.
    valija_id: str | None = Field(default=None, max_length=20)

    @field_validator("fondo_vuelto")
    @classmethod
    def _vuelto_no_negativo(cls, v: Decimal) -> Decimal:
        if v < 0:
            raise ValueError("fondo_vuelto no puede ser negativo")
        return v


# --------------------------------------------------------------------------- #
#  Valija: salida
# --------------------------------------------------------------------------- #
class ValijaOut(BaseModel):
    """Representación completa de una valija (contrato canónico)."""

    valija_id: str
    fecha: datetime
    usuario: str
    efectivo_total: Money
    nomenclaturas: list[Nomenclatura]
    pagos_adicionales: PagosAdicionales
    fondo_vuelto: Money
    cheques: list[ChequeOut]
    estado: EstadoValija

    # Metadatos operativos
    mensajero: str | None = None
    custodia_en: datetime | None = None
    banco_deposito: str | None = None
    comprobante_deposito: str | None = None
    depositada_en: datetime | None = None
    erp_asiento_id: str | None = None

    # Totales derivados (útiles para el dashboard)
    monto_deposito_banco: Money
    monto_custodia_matriz: Money

    @classmethod
    def from_model(cls, v) -> "ValijaOut":
        """Construye la salida a partir del modelo ORM."""
        return cls(
            valija_id=v.id,
            fecha=v.fecha,
            usuario=v.usuario,
            efectivo_total=v.efectivo_total,
            nomenclaturas=[Nomenclatura(**n) for n in (v.nomenclaturas or [])],
            pagos_adicionales=PagosAdicionales(
                tarjeta=v.pago_tarjeta,
                de_una=v.pago_de_una,
                delivery=v.pago_delivery,
            ),
            fondo_vuelto=v.fondo_vuelto,
            cheques=[ChequeOut.model_validate(c) for c in v.cheques],
            estado=v.estado,
            mensajero=v.mensajero,
            custodia_en=v.custodia_en,
            banco_deposito=v.banco_deposito,
            comprobante_deposito=v.comprobante_deposito,
            depositada_en=v.depositada_en,
            erp_asiento_id=v.erp_asiento_id,
            monto_deposito_banco=v.monto_deposito_banco,
            monto_custodia_matriz=v.monto_custodia_matriz,
        )


# --------------------------------------------------------------------------- #
#  Transiciones de estado
# --------------------------------------------------------------------------- #
class TraspasoCustodiaIn(BaseModel):
    """Cuerpo del traspaso ENVIADA -> CUSTODIA (validación del mensajero)."""

    mensajero: str = Field(min_length=1, max_length=120)
    qr_token: str = Field(min_length=1, description="Token QR escaneado por el mensajero")


class DepositoBancoIn(BaseModel):
    """Cuerpo del cierre CUSTODIA -> DEPOSITADA (papeleta sellada)."""

    banco: str = Field(min_length=1, max_length=80)
    # Referencia o data-URI de la foto de la papeleta.
    comprobante: str = Field(min_length=1)
    registrar_en_erp: bool = True


class QrPayload(BaseModel):
    """Payload del código QR para el traspaso de custodia."""

    valija_id: str
    texto: str
    token: str


# --------------------------------------------------------------------------- #
#  Reportes
# --------------------------------------------------------------------------- #
class KpisOut(BaseModel):
    efectivo_recibido: Money
    caja_vuelto: Money
    en_custodia: int
    sin_confirmar_banco: int
    posfechados_matriz: int
    total_valijas: int


class LineaReporteBanco(BaseModel):
    valija_id: str
    usuario: str
    fecha: datetime
    efectivo: Money
    cheques_estandar: Money
    total_papeleta: Money


class ReporteBancoOut(BaseModel):
    generado_en: datetime
    cantidad_valijas: int
    total_efectivo: Money
    total_cheques_estandar: Money
    total_general: Money
    detalle: list[LineaReporteBanco]


class LineaChequePosfechado(BaseModel):
    valija_id: str
    banco: str
    monto: Money
    referencia: str


class ReporteMatrizOut(BaseModel):
    generado_en: datetime
    cantidad_cheques: int
    total_posfechado: Money
    detalle: list[LineaChequePosfechado]


class ManifiestoOut(BaseModel):
    """Datos del manifiesto de depósito (equivalente al PDF del front-end)."""

    valija_id: str
    usuario: str
    fecha: datetime
    efectivo: Money
    cheques_estandar_cantidad: int
    cheques_estandar_total: Money
    monto_deposito_banco: Money
    cheques_posfechados_cantidad: int
    cheques_posfechados_total: Money
    monto_custodia_matriz: Money


# --------------------------------------------------------------------------- #
#  Integraciones
# --------------------------------------------------------------------------- #
class VentaTableau(BaseModel):
    fecha: datetime
    canal: str
    monto: Money


class VentasTableauOut(BaseModel):
    fuente: str
    fecha_consulta: datetime
    total_ventas: Money
    ventas: list[VentaTableau]


class ConciliacionOut(BaseModel):
    fecha: datetime
    total_declarado: Money
    total_tableau: Money
    diferencia: Money
    cuadrado: bool


class AsientoErpOut(BaseModel):
    valija_id: str
    asiento_id: str
    estado: str
    detalle: dict
