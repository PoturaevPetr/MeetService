"""Конфигурация MeetService (JWT совместим с ChatService)."""

from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import Any

from pydantic_settings import BaseSettings, SettingsConfigDict


def _default_database_url() -> str:
    user = os.getenv("DB_USER", "postgres")
    password = os.getenv("DB_PASSWORD", "postgres")
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    name = os.getenv("DB_NAME", "meet_service")
    return f"postgresql://{user}:{password}@{host}:{port}/{name}"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    PORT: int = 8480
    DEBUG: bool = True

    USE_SQLITE: bool = False
    SQLITE_PATH: str = "./meet_service.db"

    DATABASE_URL: str = ""

    JWT_SECRET_KEY: str = ""
    JWT_ALGORITHM: str = "HS256"

    # Тот же ключ, что ChatService — тогда access-токены клиента принимаются без доработок.
    # Для локальной разработки можно скопировать JWT_SECRET_KEY из .env ChatService.

    # JSON-массив ICE-серверов для клиента: [{"urls":["stun:..."]}, {"urls":["turn:..."],"username":"u","credential":"p"}]
    ICE_SERVERS_JSON: str = '[{"urls":["stun:stun.l.google.com:19302"]}]'

    CORS_ORIGINS: str = "*"

    def model_post_init(self, __context: Any) -> None:
        if self.USE_SQLITE:
            object.__setattr__(self, "DATABASE_URL", f"sqlite:///{self.SQLITE_PATH}")
        elif not self.DATABASE_URL.strip():
            object.__setattr__(self, "DATABASE_URL", _default_database_url())

    def cors_list(self) -> list[str]:
        raw = self.CORS_ORIGINS.strip()
        if raw == "*":
            return ["*"]
        return [x.strip() for x in raw.split(",") if x.strip()]

    def ice_servers(self) -> list[dict[str, Any]]:
        try:
            data = json.loads(self.ICE_SERVERS_JSON)
            if isinstance(data, list):
                return data
        except json.JSONDecodeError:
            pass
        return [{"urls": ["stun:stun.l.google.com:19302"]}]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
