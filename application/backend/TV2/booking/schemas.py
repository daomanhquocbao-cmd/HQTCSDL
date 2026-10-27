from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import List, Optional

class CreateBookingSchema(BaseModel):
    room_id: int = Field(..., description="ID của phòng/studio")
    start_time: datetime = Field(..., description="Thời gian bắt đầu")
    end_time: datetime = Field(..., description="Thời gian kết thúc")
    equipment_ids: Optional[List[int]] = Field(default=[], description="Danh sách thiết bị thuê kèm")

    @field_validator("end_time")
    def validate_times(cls, end_time, values):
        start_time = values.data.get("start_time")
        if start_time and end_time <= start_time:
            raise ValueError("Thời gian kết thúc phải sau thời gian bắt đầu.")
        if start_time and start_time < datetime.now():
            raise ValueError("Không thể đặt lịch trong quá khứ.")
        return end_time

class BookingResponseSchema(BaseModel):
    booking_id: int
    user_id: int
    room_id: int
    start_time: datetime
    end_time: datetime
    total_amount: float
    status: str