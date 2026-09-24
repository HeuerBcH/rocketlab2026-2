from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configurações carregadas de variáveis de ambiente ou do arquivo .env."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    project_name: str = "RocketLab API"
    project_version: str = "2026.2"
    environment: str = "local"
    api_v1_prefix: str = "/api/v1"
    database_url: str = "sqlite+aiosqlite:///./rocketlab.db"
    backend_cors_origins: list[str] = ["http://localhost:5173"]
    log_level: str = "INFO"

    # Autenticação do administrador (único usuário do sistema).
    # A senha fica só como hash (gere com: python -m app.auth.hash_password).
    admin_username: str = "admin"
    admin_password_hash: SecretStr = SecretStr("")
    auth_secret_key: SecretStr = SecretStr("")
    access_token_minutes: int = 60


@lru_cache
def get_settings() -> Settings:
    return Settings()
