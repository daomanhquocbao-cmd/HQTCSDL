"""Schema đầu vào cho các endpoint /api/provider/*."""
from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, Field

RoomType = Literal["STUDIO", "DARKROOM"]
RoomStatus = Literal["AVAILABLE", "MAINTENANCE", "INACTIVE"]
EquipmentType = Literal["REUSABLE", "CONSUMABLE"]
EquipmentCategory = Literal["CAMERA", "LENS", "LIGHTING", "TRIPOD", "ENLARGER",
                            "SCANNER", "CHEMICAL", "PAPER", "OTHER"]
EquipmentStatus = Literal["GOOD", "NEEDS_MAINTENANCE", "UNDER_MAINTENANCE", "BROKEN", "RETIRED"]
PaymentMethod = Literal["VNPAY", "MOMO", "STRIPE", "CASH", "BANK_TRANSFER"]


class StudioIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    address: str = Field(min_length=1, max_length=255)
    city: str = Field(min_length=1, max_length=100)
    phone: Optional[str] = Field(default=None, max_length=20)
    description: Optional[str] = None
    open_time: Optional[str] = None     # "HH:MM"
    close_time: Optional[str] = None


class StudioPatch(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    address: Optional[str] = Field(default=None, min_length=1, max_length=255)
    city: Optional[str] = Field(default=None, min_length=1, max_length=100)
    phone: Optional[str] = Field(default=None, max_length=20)
    description: Optional[str] = None
    open_time: Optional[str] = None
    close_time: Optional[str] = None


class RoomIn(BaseModel):
    studio_id: int = Field(gt=0)
    name: str = Field(min_length=1, max_length=100)
    room_type: RoomType
    capacity: int = Field(gt=0)
    price_per_hour: float = Field(ge=0)
    area_sqm: Optional[float] = Field(default=None, ge=0)
    art_style: Optional[str] = Field(default=None, max_length=100)
    lighting: Optional[str] = Field(default=None, max_length=200)
    amenities: Optional[str] = Field(default=None, max_length=500)
    description: Optional[str] = None
    status: RoomStatus = "AVAILABLE"


class RoomPatch(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    room_type: Optional[RoomType] = None
    capacity: Optional[int] = Field(default=None, gt=0)
    price_per_hour: Optional[float] = Field(default=None, ge=0)
    area_sqm: Optional[float] = Field(default=None, ge=0)
    art_style: Optional[str] = Field(default=None, max_length=100)
    lighting: Optional[str] = Field(default=None, max_length=200)
    amenities: Optional[str] = Field(default=None, max_length=500)
    description: Optional[str] = None
    status: Optional[RoomStatus] = None


class EquipmentIn(BaseModel):
    studio_id: int = Field(gt=0)
    name: str = Field(min_length=1, max_length=100)
    equipment_type: EquipmentType = "REUSABLE"
    category: EquipmentCategory = "OTHER"
    quantity: int = Field(ge=0)
    rental_price: float = Field(ge=0)
    next_maintenance_date: Optional[date] = None
    status: EquipmentStatus = "GOOD"


class EquipmentPatch(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    equipment_type: Optional[EquipmentType] = None
    category: Optional[EquipmentCategory] = None
    quantity: Optional[int] = Field(default=None, ge=0)
    rental_price: Optional[float] = Field(default=None, ge=0)
    next_maintenance_date: Optional[date] = None
    status: Optional[EquipmentStatus] = None


class MaintenanceIn(BaseModel):
    cost: float = Field(ge=0)
    description: Optional[str] = None
    status: Literal["SCHEDULED", "DONE"] = "DONE"
    next_maintenance_date: Optional[date] = None


class CheckInIn(BaseModel):
    qr_code: str = Field(min_length=1, max_length=100)


class PaymentIn(BaseModel):
    amount: float = Field(gt=0)
    payment_method: PaymentMethod
    transaction_code: Optional[str] = Field(default=None, max_length=100)


class BookingEquipmentIn(BaseModel):
    equipment_id: int = Field(gt=0)
    quantity: int = Field(default=1, gt=0)


class BookingPackageIn(BaseModel):
    package_id: int = Field(gt=0)
    notes: Optional[str] = None


class ProfilePatch(BaseModel):
    full_name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    phone: Optional[str] = Field(default=None, max_length=20)
    email: Optional[str] = Field(default=None, max_length=100)


class ChangePasswordIn(BaseModel):
    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=8, max_length=128)
