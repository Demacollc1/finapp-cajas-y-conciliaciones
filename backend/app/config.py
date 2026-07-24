"""Configuración de la aplicación (variables de entorno)."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Ajustes leídos desde variables de entorno o archivo ``.env``."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- Aplicación ---
    app_name: str = "FinancePro API"
    environment: str = "development"
    api_prefix: str = "/api"

    # --- Base de datos ---
    # Por defecto SQLite (portable, cero configuración). Para producción se puede
    # apuntar a PostgreSQL: postgresql+psycopg://usuario:clave@host:5432/finapp
    database_url: str = "sqlite:///./financepro.db"

    # --- CORS (orígenes autorizados del front-end) ---
    cors_origins: list[str] = ["*"]

    # --- Semilla de datos de demostración ---
    seed_on_startup: bool = True

    # --- Firma de tokens QR de traspaso de custodia ---
    qr_secret: str = "cambia-esta-clave-en-produccion"

    # --- Integración Tableau (ventas del sistema) ---
    tableau_base_url: str | None = None
    tableau_token: str | None = None
    tableau_site_id: str | None = None

    # --- Integración ERP (asiento contable) ---
    erp_base_url: str | None = None
    erp_token: str | None = None
    erp_cuenta_caja: str = "1.1.01.001"      # Caja general
    erp_cuenta_bancos: str = "1.1.02.001"    # Bancos
    erp_cuenta_posfechados: str = "1.1.03.005"  # Cheques posfechados en custodia


@lru_cache
def get_settings() -> Settings:
    """Devuelve una instancia cacheada de la configuración."""
    return Settings()


settings = get_settings()
