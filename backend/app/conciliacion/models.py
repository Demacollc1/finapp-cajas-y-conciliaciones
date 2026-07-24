"""Modelos ORM de la conciliación: perfiles, corridas y movimientos."""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from ..database import Base
from ..enums import EstadoMovimiento, OrigenMovimiento, TipoPerfil

Money = Numeric(16, 2)


class PerfilBanco(Base):
    """Plantilla de mapeo de un CSV a nuestro formato estándar.

    Representa el "entrenamiento" inicial: define cómo leer el archivo de un
    banco (o de JD Edwards) y qué columna corresponde a cada campo estándar.
    """

    __tablename__ = "perfiles_conciliacion"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    tipo: Mapped[TipoPerfil] = mapped_column(
        SAEnum(TipoPerfil, native_enum=False, length=10), nullable=False
    )

    # --- Lectura del archivo ---
    delimitador: Mapped[str | None] = mapped_column(String(4), nullable=True)  # None = autodetectar
    encoding: Mapped[str | None] = mapped_column(String(20), nullable=True)
    filas_omitir: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # --- Mapeo de columnas -> campos estándar ---
    columna_fecha: Mapped[str] = mapped_column(String(120), nullable=False)
    formato_fecha: Mapped[str | None] = mapped_column(String(40), nullable=True)
    columna_descripcion: Mapped[str | None] = mapped_column(String(120), nullable=True)
    columna_referencia: Mapped[str | None] = mapped_column(String(120), nullable=True)
    # Campo de vinculación: clave que enlaza libro <-> banco (p.ej. Nº documento).
    columna_vinculacion: Mapped[str | None] = mapped_column(String(120), nullable=True)

    # Monto: una sola columna con signo, o débito/crédito por separado.
    columna_monto: Mapped[str | None] = mapped_column(String(120), nullable=True)
    columna_debito: Mapped[str | None] = mapped_column(String(120), nullable=True)
    columna_credito: Mapped[str | None] = mapped_column(String(120), nullable=True)

    # --- Formato numérico ---
    separador_decimal: Mapped[str] = mapped_column(String(1), nullable=False, default=".")
    separador_miles: Mapped[str | None] = mapped_column(String(1), nullable=True)
    signo_invertido: Mapped[bool] = mapped_column(nullable=False, default=False)

    creado_en: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )


class Conciliacion(Base):
    """Una corrida de conciliación con sus totales."""

    __tablename__ = "conciliaciones"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    descripcion: Mapped[str | None] = mapped_column(String(200), nullable=True)
    fecha_ejecucion: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    tolerancia_dias: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    comparar_absoluto: Mapped[bool] = mapped_column(nullable=False, default=True)

    total_libro: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_banco: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    conciliados: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    posibles: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    no_conciliados_libro: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    no_conciliados_banco: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    monto_conciliado: Mapped[Decimal] = mapped_column(Money, nullable=False, default=0)
    monto_posible: Mapped[Decimal] = mapped_column(Money, nullable=False, default=0)
    monto_no_conciliado_libro: Mapped[Decimal] = mapped_column(Money, nullable=False, default=0)
    monto_no_conciliado_banco: Mapped[Decimal] = mapped_column(Money, nullable=False, default=0)

    creado_en: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    movimientos: Mapped[list["MovimientoConciliacion"]] = relationship(
        back_populates="conciliacion",
        cascade="all, delete-orphan",
        order_by="MovimientoConciliacion.id",
    )


class MovimientoConciliacion(Base):
    """Movimiento normalizado dentro de una conciliación."""

    __tablename__ = "movimientos_conciliacion"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    conciliacion_id: Mapped[int] = mapped_column(
        ForeignKey("conciliaciones.id", ondelete="CASCADE"), nullable=False, index=True
    )
    origen: Mapped[OrigenMovimiento] = mapped_column(
        SAEnum(OrigenMovimiento, native_enum=False, length=8), nullable=False, index=True
    )
    fuente: Mapped[str] = mapped_column(String(120), nullable=False)

    fecha: Mapped[date | None] = mapped_column(Date, nullable=True)
    descripcion: Mapped[str | None] = mapped_column(String(300), nullable=True)
    referencia: Mapped[str | None] = mapped_column(String(120), nullable=True)
    clave: Mapped[str | None] = mapped_column(String(120), nullable=True)
    monto: Mapped[Decimal] = mapped_column(Money, nullable=False, default=0)

    estado: Mapped[EstadoMovimiento] = mapped_column(
        SAEnum(EstadoMovimiento, native_enum=False, length=14),
        nullable=False,
        default=EstadoMovimiento.NO_CONCILIADO,
        index=True,
    )
    # Movimiento contraparte (el otro lado del par).
    match_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    motivo: Mapped[str | None] = mapped_column(String(120), nullable=True)
    score: Mapped[float | None] = mapped_column(nullable=True)

    raw: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    conciliacion: Mapped["Conciliacion"] = relationship(back_populates="movimientos")
