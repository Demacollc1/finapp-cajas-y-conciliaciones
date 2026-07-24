"""Esquemas Pydantic del módulo de conciliación."""

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer

from ..enums import EstadoMovimiento, OrigenMovimiento, TipoPerfil

Money = Annotated[
    Decimal,
    PlainSerializer(lambda v: float(v), return_type=float, when_used="json"),
]


# --------------------------------------------------------------------------- #
#  Perfiles (entrenamiento)
# --------------------------------------------------------------------------- #
class PerfilBase(BaseModel):
    nombre: str = Field(min_length=1, max_length=120)
    tipo: TipoPerfil
    delimitador: str | None = Field(default=None, max_length=4)
    encoding: str | None = None
    filas_omitir: int = Field(default=0, ge=0)

    columna_fecha: str = Field(min_length=1, max_length=120)
    formato_fecha: str | None = None
    columna_descripcion: str | None = None
    columna_referencia: str | None = None
    columna_vinculacion: str | None = None

    columna_monto: str | None = None
    columna_debito: str | None = None
    columna_credito: str | None = None

    separador_decimal: str = Field(default=".", max_length=1)
    separador_miles: str | None = Field(default=None, max_length=1)
    signo_invertido: bool = False


class PerfilCreate(PerfilBase):
    pass


class PerfilUpdate(PerfilBase):
    pass


class PerfilOut(PerfilBase):
    id: int
    creado_en: datetime | None = None
    actualizado_en: datetime | None = None
    model_config = ConfigDict(from_attributes=True)


# --------------------------------------------------------------------------- #
#  Inspección de CSV (para el entrenamiento)
# --------------------------------------------------------------------------- #
class InspeccionOut(BaseModel):
    delimitador: str
    columnas: list[str]
    total_filas: int
    muestra: list[dict]


# --------------------------------------------------------------------------- #
#  Movimientos y resultado de conciliación
# --------------------------------------------------------------------------- #
class MovimientoOut(BaseModel):
    id: int
    origen: OrigenMovimiento
    fuente: str
    fecha: date | None
    descripcion: str | None
    referencia: str | None
    clave: str | None
    monto: Money
    estado: EstadoMovimiento
    match_id: int | None
    motivo: str | None
    score: float | None
    model_config = ConfigDict(from_attributes=True)


class ParConciliado(BaseModel):
    estado: EstadoMovimiento
    motivo: str | None
    score: float | None
    libro: MovimientoOut
    banco: MovimientoOut


class ResumenConciliacion(BaseModel):
    id: int
    descripcion: str | None
    fecha_ejecucion: datetime
    tolerancia_dias: int
    comparar_absoluto: bool
    total_libro: int
    total_banco: int
    conciliados: int
    posibles: int
    no_conciliados_libro: int
    no_conciliados_banco: int
    monto_conciliado: Money
    monto_posible: Money
    monto_no_conciliado_libro: Money
    monto_no_conciliado_banco: Money
    model_config = ConfigDict(from_attributes=True)


class DetalleConciliacion(BaseModel):
    resumen: ResumenConciliacion
    conciliados: list[ParConciliado]
    posibles: list[ParConciliado]
    no_conciliados_libro: list[MovimientoOut]
    no_conciliados_banco: list[MovimientoOut]
