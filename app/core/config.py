from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )

    # ─────────── APP ───────────
    app_name: str = "Real Estate and TDR Exchange of India"
    environment: str = "dev"
    log_level: str = "INFO"

    # ─────────── API ───────────
    api_prefix: str = "/api/v1"
    request_id_header: str = "X-Request-Id"

    # ─────────── DATABASE ───────────
    database_url: str

    # ─────────── JWT / AUTH ───────────
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_access_token_minutes: int = 1440  # 24 hours


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()



