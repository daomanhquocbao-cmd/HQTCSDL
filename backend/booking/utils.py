"""Hàm tiện ích thuần (không cần DB) cho booking."""
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal


def calc_duration_hours(start: datetime, end: datetime) -> float:
    if end <= start:
        raise ValueError("end phải lớn hơn start")
    return (end - start).total_seconds() / 3600


def calc_total_price(start: datetime, end: datetime, hourly_price: float) -> float:
    """Giá = số giờ * đơn giá, làm tròn 2 chữ số."""
    if hourly_price < 0:
        raise ValueError("hourly_price không được âm")
    total = Decimal(str(calc_duration_hours(start, end))) * Decimal(str(hourly_price))
    return float(total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def is_overlapping(start_a: datetime, end_a: datetime, start_b: datetime, end_b: datetime) -> bool:
    """Hai khoảng [start, end) chồng nhau khi mỗi khoảng bắt đầu trước khi khoảng kia kết thúc."""
    return start_a < end_b and start_b < end_a
