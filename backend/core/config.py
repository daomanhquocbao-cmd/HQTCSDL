"""Cấu hình ứng dụng đọc từ biến môi trường."""
import os
from dataclasses import dataclass


def _split_csv(value: str) -> tuple:
    return tuple(item.strip() for item in value.split(",") if item.strip())


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "Booking System API - Python FastAPI")
    app_version: str = os.getenv("APP_VERSION", "1.1.0")
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"
    log_level: str = os.getenv("LOG_LEVEL", "INFO").upper()
    cors_origins: tuple = _split_csv(os.getenv("CORS_ORIGINS", "*"))
    access_token_minutes: int = int(os.getenv("ACCESS_TOKEN_MINUTES", "60"))


settings = Settings()
