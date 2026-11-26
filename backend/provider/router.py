"""Endpoint cho giao diện Provider. Hợp đồng chi tiết: docs/PROVIDER_API.md."""
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, Response, status

from core.dependencies import require_provider
from core.security import get_current_user
from datetime import date as _date

from provider import analytics, scheduler, schemas, service

router = APIRouter(prefix="/api/provider", tags=["Provider"])
profile_router = APIRouter(prefix="/api/users", tags=["Users"])

User = Depends(require_provider)


@router.get("/overview")
def overview(user: dict = User):
    return service.overview(user)


# --- studios
@router.get("/studios")
def list_studios(user: dict = User):
    return service.list_studios(user)


@router.post("/studios", status_code=status.HTTP_201_CREATED)
def create_studio(data: schemas.StudioIn, user: dict = User):
    return service.create_studio(user, data)


@router.patch("/studios/{studio_id}")
def update_studio(studio_id: int, data: schemas.StudioPatch, user: dict = User):
    return service.update_studio(user, studio_id, data)


@router.delete("/studios/{studio_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_studio(studio_id: int, user: dict = User):
    service.delete_studio(user, studio_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- rooms
@router.get("/rooms")
def list_rooms(studio_id: Optional[int] = Query(default=None, gt=0), user: dict = User):
    return service.list_rooms(user, studio_id)


@router.post("/rooms", status_code=status.HTTP_201_CREATED)
def create_room(data: schemas.RoomIn, user: dict = User):
    return service.create_room(user, data)


@router.patch("/rooms/{room_id}")
def update_room(room_id: int, data: schemas.RoomPatch, user: dict = User):
    return service.update_room(user, room_id, data)


# --- equipment
@router.get("/equipment")
def list_equipment(studio_id: Optional[int] = Query(default=None, gt=0), user: dict = User):
    return service.list_equipment(user, studio_id)


@router.post("/equipment", status_code=status.HTTP_201_CREATED)
def create_equipment(data: schemas.EquipmentIn, user: dict = User):
    return service.create_equipment(user, data)


@router.patch("/equipment/{equipment_id}")
def update_equipment(equipment_id: int, data: schemas.EquipmentPatch, user: dict = User):
    return service.update_equipment(user, equipment_id, data)


@router.delete("/equipment/{equipment_id}", status_code=status.HTTP_204_NO_CONTENT)
def retire_equipment(equipment_id: int, user: dict = User):
    service.retire_equipment(user, equipment_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/equipment/{equipment_id}/maintenance", status_code=status.HTTP_201_CREATED)
def add_maintenance(equipment_id: int, data: schemas.MaintenanceIn, user: dict = User):
    return service.add_maintenance(user, equipment_id, data)


# --- packages, reviews
@router.get("/packages")
def list_packages(studio_id: Optional[int] = Query(default=None, gt=0), user: dict = User):
    return service.list_packages(user, studio_id)


@router.get("/reviews")
def list_reviews(studio_id: Optional[int] = Query(default=None, gt=0),
                 limit: int = Query(default=50, ge=1, le=200), offset: int = Query(default=0, ge=0),
                 user: dict = User):
    return service.list_reviews(user, studio_id, limit, offset)


# --- bookings (luồng theo stored procedure). "checkin" phải khai báo trước "{id}".
@router.get("/disputes")
def list_disputes(status: Optional[str] = Query(default=None, pattern="^(OPEN|IN_REVIEW|RESOLVED|REJECTED)$"),
                  limit: int = Query(default=100, ge=1, le=500), offset: int = Query(default=0, ge=0),
                  user: dict = User):
    return service.list_disputes(user, status, limit, offset)


@router.patch("/disputes/{dispute_id}")
def update_dispute(dispute_id: int, data: schemas.DisputePatch, user: dict = User):
    return service.update_dispute(user, dispute_id, data)


@router.get("/workshops")
def list_workshops(status: Optional[str] = Query(default=None, pattern="^(OPEN|CLOSED|CANCELLED|COMPLETED)$"),
                   limit: int = Query(default=100, ge=1, le=500), offset: int = Query(default=0, ge=0),
                   user: dict = User):
    return service.list_workshops(user, status, limit, offset)


@router.get("/bookings")
def list_bookings(status: Optional[str] = Query(default=None, pattern="^(PENDING|CONFIRMED|IN_USE|COMPLETED|CANCELLED)$"),
                  studio_id: Optional[int] = Query(default=None, gt=0),
                  room_id: Optional[int] = Query(default=None, gt=0),
                  limit: int = Query(default=100, ge=1, le=500), offset: int = Query(default=0, ge=0),
                  user: dict = User):
    return service.list_bookings(user, status, studio_id, room_id, limit, offset)


@router.post("/bookings/checkin")
def check_in(data: schemas.CheckInIn, user: dict = User):
    return service.check_in(user, data.qr_code.strip())


@router.get("/bookings/{reservation_id}")
def get_booking(reservation_id: int, user: dict = User):
    return service.get_booking(user, reservation_id)


@router.post("/bookings/{reservation_id}/confirm")
def confirm(reservation_id: int, user: dict = User):
    return service.confirm(user, reservation_id)


@router.post("/bookings/{reservation_id}/cancel")
def cancel(reservation_id: int, data: Optional[schemas.CancelIn] = None, user: dict = User):
    return service.cancel(user, reservation_id, data.reason if data else None)


@router.post("/bookings/{reservation_id}/checkout")
def checkout(reservation_id: int, user: dict = User):
    return service.checkout(user, reservation_id)


@router.post("/bookings/{reservation_id}/payments", status_code=status.HTTP_201_CREATED)
def pay(reservation_id: int, data: schemas.PaymentIn, user: dict = User):
    return service.pay(user, reservation_id, data)


@router.post("/bookings/{reservation_id}/equipment", status_code=status.HTTP_201_CREATED)
def add_equipment(reservation_id: int, data: schemas.BookingEquipmentIn, user: dict = User):
    return service.add_equipment(user, reservation_id, data)


@router.post("/bookings/{reservation_id}/packages", status_code=status.HTTP_201_CREATED)
def add_package(reservation_id: int, data: schemas.BookingPackageIn, user: dict = User):
    return service.add_package(user, reservation_id, data)


# --- phân tích: tỉ lệ lấp đầy, hiệu suất thiết bị, AI dự báo / gợi ý giá
@router.get("/analytics/occupancy")
def occupancy(days: int = Query(30, ge=7, le=365), studio_id: Optional[int] = Query(None, gt=0), user: dict = User):
    return analytics.occupancy(user, days, studio_id)


@router.get("/analytics/heatmap")
def heatmap(days: int = Query(56, ge=14, le=365), studio_id: Optional[int] = Query(None, gt=0), user: dict = User):
    return analytics.heatmap(user, days, studio_id)


@router.get("/analytics/equipment")
def equipment_utilization(days: int = Query(30, ge=7, le=365), studio_id: Optional[int] = Query(None, gt=0),
                          user: dict = User):
    return analytics.equipment_utilization(user, days, studio_id)


@router.get("/ai/forecast")
def ai_forecast(studio_id: Optional[int] = Query(None, gt=0), horizon_days: int = Query(7, ge=1, le=30),
                lookback_days: int = Query(84, ge=28, le=365), user: dict = User):
    return analytics.forecast(user, studio_id, horizon_days, lookback_days)


@router.get("/ai/pricing-suggestions")
def ai_pricing(studio_id: Optional[int] = Query(None, gt=0), days: int = Query(56, ge=14, le=365), user: dict = User):
    return analytics.pricing_suggestions(user, studio_id, days)


@router.get("/ai/schedule-optimize")
def ai_schedule(studio_id: Optional[int] = Query(None, gt=0), day: Optional[_date] = Query(None), user: dict = User):
    """Tối ưu phân bổ phòng/thiết bị trong một ngày (mặc định hôm nay)."""
    return scheduler.optimize_day(user, studio_id, day or _date.today())


# --- chính sách giá
@router.get("/pricing-rules")
def list_rules(studio_id: Optional[int] = Query(None, gt=0), user: dict = User):
    return analytics.list_rules(user, studio_id)


@router.post("/pricing-rules", status_code=status.HTTP_201_CREATED)
def create_rule(data: schemas.PricingRuleIn, user: dict = User):
    return analytics.create_rule(user, data)


@router.patch("/pricing-rules/{rule_id}")
def update_rule(rule_id: int, data: schemas.PricingRulePatch, user: dict = User):
    return analytics.update_rule(user, rule_id, data)


@router.delete("/pricing-rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_rule(rule_id: int, user: dict = User):
    analytics.delete_rule(user, rule_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- khuyến mãi
@router.get("/promotions")
def list_promotions(studio_id: Optional[int] = Query(None, gt=0), user: dict = User):
    return analytics.list_promotions(user, studio_id)


@router.post("/promotions", status_code=status.HTTP_201_CREATED)
def create_promotion(data: schemas.PromotionIn, user: dict = User):
    return analytics.create_promotion(user, data)


@router.patch("/promotions/{promo_id}")
def update_promotion(promo_id: int, data: schemas.PromotionPatch, user: dict = User):
    return analytics.update_promotion(user, promo_id, data)


@router.delete("/promotions/{promo_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_promotion(promo_id: int, user: dict = User):
    analytics.delete_promotion(user, promo_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- hồ sơ cá nhân (dùng chung mọi vai trò đã đăng nhập)
@profile_router.patch("/me")
def update_me(data: schemas.ProfilePatch, user: dict = Depends(get_current_user)):
    return service.update_profile(user, data)


@profile_router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(data: schemas.ChangePasswordIn, user: dict = Depends(get_current_user)):
    service.change_password(user, data.current_password, data.new_password)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
