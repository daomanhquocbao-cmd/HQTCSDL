"""Schema đầu vào cho các endpoint /api/provider/*."""
from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator

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


class CancelIn(BaseModel):
    reason: Optional[str] = Field(default=None, max_length=500, description="Lý do hủy đơn (khách sẽ thấy)")


class DisputePatch(BaseModel):
    status: Literal["IN_REVIEW", "RESOLVED", "REJECTED"]
    resolution: Optional[str] = Field(default=None, max_length=4000, description="Nội dung phản hồi / hướng giải quyết")


# ---- chính sách giá & khuyến mãi (database/07_pricing_promotions_ai.sql)
DayType = Literal["ALL", "WEEKDAY", "WEEKEND"]
ActiveState = Literal["ACTIVE", "INACTIVE"]


class PricingRuleIn(BaseModel):
    studio_id: int = Field(gt=0)
    room_id: Optional[int] = Field(default=None, gt=0, description="Bỏ trống = áp dụng cho cả cơ sở")
    name: str = Field(min_length=1, max_length=100)
    day_type: DayType = "ALL"
    start_hour: int = Field(ge=0, le=23)
    end_hour: int = Field(ge=1, le=24)
    multiplier: float = Field(ge=0.5, le=3.0, description="1.0 = giá gốc, 1.2 = tăng 20%")
    status: ActiveState = "ACTIVE"

    @model_validator(mode="after")
    def _hours(self):
        if self.end_hour <= self.start_hour:
            raise ValueError("end_hour phải lớn hơn start_hour")
        return self


class PricingRulePatch(BaseModel):
    room_id: Optional[int] = Field(default=None, gt=0)
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    day_type: Optional[DayType] = None
    start_hour: Optional[int] = Field(default=None, ge=0, le=23)
    end_hour: Optional[int] = Field(default=None, ge=1, le=24)
    multiplier: Optional[float] = Field(default=None, ge=0.5, le=3.0)
    status: Optional[ActiveState] = None


class PromotionIn(BaseModel):
    studio_id: int = Field(gt=0)
    code: str = Field(min_length=3, max_length=30, pattern=r"^[A-Za-z0-9_-]+$")
    title: str = Field(min_length=1, max_length=150)
    discount_type: Literal["PERCENT", "FIXED"]
    discount_value: float = Field(gt=0)
    max_discount: Optional[float] = Field(default=None, gt=0)
    min_order_amount: float = Field(default=0, ge=0)
    start_date: date
    end_date: date
    max_uses: Optional[int] = Field(default=None, gt=0)
    status: ActiveState = "ACTIVE"

    @model_validator(mode="after")
    def _check(self):
        self.code = self.code.upper()
        if self.end_date < self.start_date:
            raise ValueError("end_date phải sau hoặc bằng start_date")
        if self.discount_type == "PERCENT" and self.discount_value > 100:
            raise ValueError("Giảm theo % không được vượt 100")
        return self


class PromotionPatch(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=150)
    discount_type: Optional[Literal["PERCENT", "FIXED"]] = None
    discount_value: Optional[float] = Field(default=None, gt=0)
    max_discount: Optional[float] = Field(default=None, gt=0)
    min_order_amount: Optional[float] = Field(default=None, ge=0)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    max_uses: Optional[int] = Field(default=None, gt=0)
    status: Optional[ActiveState] = None
