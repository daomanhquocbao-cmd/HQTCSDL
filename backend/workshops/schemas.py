from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from booking.schemas import to_local_naive


class WorkshopCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    description: Optional[str] = Field(default=None, max_length=4000)
    capacity: int = Field(..., gt=0, le=10000)
    start_time: datetime
    end_time: datetime

    @field_validator("start_time", "end_time")
    @classmethod
    def normalize_tz(cls, v: datetime) -> datetime:
        return to_local_naive(v)

    @model_validator(mode="after")
    def check_time_range(self):
        if self.end_time <= self.start_time:
            raise ValueError("end_time phải lớn hơn start_time")
        return self


class WorkshopOut(BaseModel):
    workshop_id: int
    expert_id: Optional[int] = None
    expert_name: Optional[str] = None
    title: str
    description: Optional[str] = None
    capacity: int
    registered: int
    remaining_slots: int
    start_time: datetime
    end_time: datetime


class RegistrationOut(BaseModel):
    workshop_id: int
    customer_id: int
    message: str
