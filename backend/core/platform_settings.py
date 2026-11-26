"""Đọc cấu hình nền tảng từ bảng dbo.SystemSettings (tạo ở database/08_collections_settings_ledger.sql).

Admin đổi giá trị trên trang quản trị -> các module (AI, đặt phòng, giá) đọc lại ở lần gọi sau.
Chưa chạy file 08 (không có bảng) thì dùng giá trị mặc định bên dưới, không làm hỏng luồng chính.
"""
from typing import Any

import pyodbc
from fastapi import HTTPException

from database import get_db_connection

DEFAULTS = {
    "ai.recommendations.enabled": True,
    "ai.assistant.enabled": True,
    "ai.knowledge_search.enabled": True,
    "ai.pricing_suggestions.enabled": True,
    "pricing.high_occupancy_pct": 75,
    "pricing.low_occupancy_pct": 20,
    "booking.max_hours_per_booking": 12,
    "platform.maintenance_mode": False,
    "platform.commission_percent": 10.0,
}


def cast(value: str, value_type: str) -> Any:
    """Chuỗi lưu trong DB -> kiểu Python theo cột value_type."""
    if value_type == "BOOL":
        return str(value).strip().lower() in ("1", "true", "yes", "on")
    if value_type == "INT":
        return int(float(value))
    if value_type == "NUMBER":
        return float(value)
    return value


def get_setting(key: str, default: Any = None) -> Any:
    fallback = DEFAULTS.get(key, default) if default is None else default
    try:
        conn = get_db_connection()
    except Exception:
        return fallback
    try:
        cur = conn.cursor()
        cur.execute("SELECT setting_value, value_type FROM dbo.SystemSettings WHERE setting_key = ?", key)
        row = cur.fetchone()
        return cast(row[0], row[1]) if row else fallback
    except (pyodbc.Error, ValueError):
        return fallback
    finally:
        conn.close()


def require_enabled(key: str, message: str) -> None:
    """Ném 403 nếu admin đã tắt tính năng `key`."""
    if not get_setting(key):
        raise HTTPException(status_code=403, detail=message)
