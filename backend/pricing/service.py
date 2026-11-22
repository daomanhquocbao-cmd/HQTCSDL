"""Báo giá và áp mã khuyến mãi (gọi sp_QuotePrice / sp_ApplyPromotion trong database/07)."""
from datetime import datetime
from typing import Optional

from provider.analytics import _db_ext
from provider.service import _drain, _one, _rows


def quote(room_id: int, start: datetime, end: datetime, promo_code: Optional[str]) -> dict:
    with _db_ext() as cur:
        cur.execute("EXEC dbo.sp_QuotePrice @room_id = ?, @start_time = ?, @end_time = ?, @promo_code = ?",
                    room_id, start, end, promo_code.strip().upper() if promo_code else None)
        row = _one(cur)
        _drain(cur)
    if row is None:
        from provider.service import _err
        raise _err(404, "Không tìm thấy phòng")
    return row


def apply_promotion(user: dict, reservation_id: int, code: str) -> dict:
    with _db_ext() as cur:
        cur.execute("EXEC dbo.sp_ApplyPromotion @reservation_id = ?, @code = ?, @actor_id = ?",
                    reservation_id, code.strip().upper(), user["user_id"])
        row = _one(cur)
        _drain(cur)
    return row or {}
