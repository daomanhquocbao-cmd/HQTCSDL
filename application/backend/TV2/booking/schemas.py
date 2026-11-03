"""Pydantic schemas cho đơn đặt phòng (bảng Reservations)."""
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator

# Giờ địa phương Việt Nam (UTC+7). Datetime có múi giờ sẽ đổi về giờ VN rồi bỏ tzinfo
# để khớp với GETDATE() của SQL Server.
LOCAL_TZ = timezone(timedelta(hours=7))


class BookingStatus(str, Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"
    COMPLETED = "COMPLETED"


def to_local_naive(value: datetime) -> datetime:
    if value.tzinfo is not None:
        return value.astimezone(LOCAL_TZ).replace(tzinfo=None)
    return value


class BookingCreate(BaseModel):
    room_id: int = Field(..., gt=0, description="ID phòng cần đặt")
    start_time: datetime
    end_time: datetime
    customer_note: Optional[str] = Field(default=None, max_length=2000)

    @field_validator("start_time", "end_time")
    @classmethod
    def normalize_tz(cls, v: datetime) -> datetime:
        return to_local_naive(v)

    @model_validator(mode="after")
    def check_time_range(self):
        if self.end_time <= self.start_time:
            raise ValueError("end_time phải lớn hơn start_time")
        return self


class BookingStatusUpdate(BaseModel):
    status: BookingStatus


class BookingOut(BaseModel):
    reservation_id: int
    room_id: Optional[int] = None
    customer_id: Optional[int] = None
    start_time: datetime
    end_time: datetime
    total_amount: float
    customer_note: Optional[str] = None
    status: BookingStatus
