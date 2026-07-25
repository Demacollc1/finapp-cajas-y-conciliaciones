"""Modelos ORM: Valija (cabecera) y Cheque (detalle segregable)."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from .database import Base
from .enums import EstadoValija, TipoCheque

# Precisión monetaria: 14 dígitos, 2 decimales.
Money = Numeric(14, 2)


class Valija(Base):
    """Cabecera de un cierre de caja.

    Agrupa el efectivo contado (desglosado por nomenclatura), los pagos
    electrónicos, el fondo de vuelto y los cheques declarados. Su ``estado``
    avanza por el ciclo ENVIADA -> CUSTODIA -> DEPOSITADA.
    """

    __tablename__ = "valijas"

    # Identificador operativo "VAL-XXXXXX".
    id: Mapped[str] = mapped_column(String(20), primary_key=True)
    fecha: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    usuario: Mapped[str] = mapped_column(String(80), nullable=False, index=True)

    # Efectivo físico total y su desglose por denominación.
    efectivo_total: Mapped[Decimal] = mapped_column(Money, nullable=False, default=0)
    # [{"denominacion": 20.00, "cantidad": 15}, ...]
    nomenclaturas: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    # Pagos electrónicos declarados.
    pago_tarjeta: Mapped[Decimal] = mapped_column(Money, nullable=False, default=0)
    pago_de_una: Mapped[Decimal] = mapped_column(Money, nullable=False, default=0)
    pago_delivery: Mapped[Decimal] = mapped_column(Money, nullable=False, default=0)

    # Fondo de vuelto que permanece en caja (deducción).
    fondo_vuelto: Mapped[Decimal] = mapped_column(Money, nullable=False, default=0)

    estado: Mapped[EstadoValija] = mapped_column(
        SAEnum(EstadoValija, native_enum=False, length=12, validate_strings=True),
        nullable=False,
        default=EstadoValija.ENVIADA,
        index=True,
    )

    # --- Metadatos de traspaso de custodia (ENVIADA -> CUSTODIA) ---
    mensajero: Mapped[str | None] = mapped_column(String(120), nullable=True)
    custodia_en: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # --- Metadatos de depósito bancario (CUSTODIA -> DEPOSITADA) ---
    banco_deposito: Mapped[str | None] = mapped_column(String(80), nullable=True)
    comprobante_deposito: Mapped[str | None] = mapped_column(String, nullable=True)
    depositada_en: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # --- Trazabilidad de integración con el ERP ---
    erp_asiento_id: Mapped[str | None] = mapped_column(String(60), nullable=True)

    creado_en: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    cheques: Mapped[list["Cheque"]] = relationship(
        back_populates="valija",
        cascade="all, delete-orphan",
        order_by="Cheque.id",
    )

    # --- Propiedades derivadas de negocio ---
    @property
    def cheques_estandar(self) -> list["Cheque"]:
        return [c for c in self.cheques if c.tipo == TipoCheque.ESTANDAR]

    @property
    def cheques_posfechados(self) -> list["Cheque"]:
        return [c for c in self.cheques if c.tipo == TipoCheque.POSFECHADO]

    @property
    def total_estandar(self) -> Decimal:
        return sum((c.monto for c in self.cheques_estandar), Decimal("0"))

    @property
    def total_posfechado(self) -> Decimal:
        return sum((c.monto for c in self.cheques_posfechados), Decimal("0"))

    @property
    def monto_deposito_banco(self) -> Decimal:
        """Efectivo + cheques estándar = lo que va en la papeleta del banco."""
        return self.efectivo_total + self.total_estandar

    @property
    def monto_custodia_matriz(self) -> Decimal:
        """Cheques posfechados = lo que se consolida hacia la Matriz."""
        return self.total_posfechado


class Cheque(Base):
    """Cheque declarado dentro de una valija.

    El campo ``tipo`` determina su ruta: ESTANDAR al banco, POSFECHADO a Matriz.
    """

    __tablename__ = "cheques"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    valija_id: Mapped[str] = mapped_column(
        ForeignKey("valijas.id", ondelete="CASCADE"), nullable=False, index=True
    )
    banco: Mapped[str] = mapped_column(String(80), nullable=False)
    monto: Mapped[Decimal] = mapped_column(Money, nullable=False)
    tipo: Mapped[TipoCheque] = mapped_column(
        SAEnum(TipoCheque, native_enum=False, length=12, validate_strings=True),
        nullable=False,
        index=True,
    )
    referencia: Mapped[str] = mapped_column(String(60), nullable=False)

    # Remesa física al banco (solo aplica a cheques POSFECHADO enviados).
    remesa_id: Mapped[int | None] = mapped_column(
        ForeignKey("remesas_posfechados.id", ondelete="SET NULL"), nullable=True, index=True
    )

    valija: Mapped["Valija"] = relationship(back_populates="cheques")
    remesa: Mapped["RemesaPosfechados | None"] = relationship(back_populates="cheques")


class RemesaPosfechados(Base):
    """Registro del envío físico de cheques POSFECHADO al banco.

    Agrupa los cheques posfechados que se depositan físicamente en el banco y
    guarda el **número de transacción que el banco devuelve** — el identificador
    que aparece en el estado de cuenta y sirve de llave para la conciliación.
    """

    __tablename__ = "remesas_posfechados"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    banco: Mapped[str] = mapped_column(String(80), nullable=False)
    fecha_envio: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    usuario: Mapped[str] = mapped_column(String(80), nullable=False)

    # Número de transacción/comprobante que devuelve el banco al depositar.
    numero_transaccion_banco: Mapped[str | None] = mapped_column(String(80), nullable=True)
    # Referencia opcional del lado JDE (batch / registro de efectos).
    referencia_jde: Mapped[str | None] = mapped_column(String(60), nullable=True)

    # REGISTRADA (sin nº de transacción aún) / CONFIRMADA (con nº del banco).
    estado: Mapped[str] = mapped_column(String(12), nullable=False, default="REGISTRADA")

    creado_en: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    cheques: Mapped[list["Cheque"]] = relationship(
        back_populates="remesa", order_by="Cheque.id"
    )

    @property
    def total(self) -> Decimal:
        return sum((c.monto for c in self.cheques), Decimal("0"))

    @property
    def cantidad_cheques(self) -> int:
        return len(self.cheques)
