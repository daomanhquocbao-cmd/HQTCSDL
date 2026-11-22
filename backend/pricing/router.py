"""Endpoint báo giá / áp khuyến mãi: /api/pricing/*."""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from booking.schemas import to_local_naive
from core.security import get_current_user
from pricing import service

router = APIRouter(prefix="/api/pricing", tags=["Pricing"])


class ApplyPromoIn(BaseModel):
    code: str = Field(min_length=3, max_length=30)


@router.get("/quote")
def quote(room_id: int = Query(gt=0), start_time: datetime = Query(), end_time: datetime = Query(),
          promo_code: Optional[str] = Query(None, max_length=30)):
    """Giá tạm tính (đã gồm quy tắc giờ cao điểm / thấp điểm và mã giảm giá). Công khai."""
    start, end = to_local_naive(start_time), to_local_naive(end_time)
    if end <= start:
        raise HTTPException(status_code=422, detail="end_time phải lớn hơn start_time")
    return service.quote(room_id, start, end, promo_code)


@router.post("/bookings/{reservation_id}/promotion")
def apply_promotion(reservation_id: int, data: ApplyPromoIn, user: dict = Depends(get_current_user)):
    return service.apply_promotion(user, reservation_id, data.code)
