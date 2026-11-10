from typing import Literal, Optional

from pydantic import BaseModel, Field

RoomType = Literal["STUDIO", "DARKROOM"]
RoomStatus = Literal["AVAILABLE", "MAINTENANCE", "INACTIVE"]


class RoomCreate(BaseModel):
    studio_id: int = Field(..., gt=0)
    name: str = Field(..., min_length=2, max_length=100)
    room_type: RoomType
    capacity: int = Field(..., gt=0)
    price_per_hour: float = Field(..., ge=0)
    description: Optional[str] = Field(default=None, max_length=2000)
    status: RoomStatus = "AVAILABLE"


class RoomUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=100)
    room_type: Optional[RoomType] = None
    capacity: Optional[int] = Field(default=None, gt=0)
    price_per_hour: Optional[float] = Field(default=None, ge=0)
    description: Optional[str] = Field(default=None, max_length=2000)
    status: Optional[RoomStatus] = None


class RoomOut(BaseModel):
    room_id: int
    studio_id: Optional[int] = None
    name: str
    room_type: RoomType
    capacity: int
    price_per_hour: float
    description: Optional[str] = None
    status: RoomStatus
