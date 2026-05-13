from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://f1:change_me@localhost:5432/f1_telemetry"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    udp_host: str = "0.0.0.0"
    udp_port: int = Field(default=20777, ge=1, le=65535)
    store_raw_packets: bool = True

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
