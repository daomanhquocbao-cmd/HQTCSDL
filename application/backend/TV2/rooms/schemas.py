from typing import Optional

from pydantic import BaseModel, Field


class RoomCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    hourly_price: float = Field(default=0, ge=0)


class RoomUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    hourly_price: Optional[float] = Field(default=None, ge=0)
    is_active: Optional[bool] = None


class RoomOut(BaseModel):
    room_id: int
    name: str
    description: Optional[str] = None
    hourly_price: float
    is_active: bool
