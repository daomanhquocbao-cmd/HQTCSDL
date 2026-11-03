"""Pydantic schemas cho Booking."""
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class BookingStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"


def _to_naive_utc(value: datetime) -> datetime:
    if value.tzinfo is not None:
        return value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


class BookingCreate(BaseModel):
    room_id: int = Field(..., gt=0, description="ID phòng/studio cần đặt")
    start_time: datetime
    end_time: datetime
    note: Optional[str] = Field(default=None, max_length=500)

    @field_validator("start_time", "end_time")
    @classmethod
    def normalize_tz(cls, v: datetime) -> datetime:
        return _to_naive_utc(v)

    @model_validator(mode="after")
    def check_time_range(self):
        if self.end_time <= self.start_time:
            raise ValueError("end_time phải lớn hơn start_time")
        return self


class BookingOut(BaseModel):
    booking_id: int
    user_id: int
    room_id: int
    start_time: datetime
    end_time: datetime
    status: BookingStatus
    note: Optional[str] = None
