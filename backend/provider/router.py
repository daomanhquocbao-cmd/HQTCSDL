"""Endpoint cho giao diện Provider. Hợp đồng chi tiết: docs/PROVIDER_API.md."""
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, Response, status

from core.dependencies import require_provider
from core.security import get_current_user
from provider import schemas, service

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


# --- hồ sơ cá nhân (dùng chung mọi vai trò đã đăng nhập)
@profile_router.patch("/me")
def update_me(data: schemas.ProfilePatch, user: dict = Depends(get_current_user)):
    return service.update_profile(user, data)


@profile_router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(data: schemas.ChangePasswordIn, user: dict = Depends(get_current_user)):
    service.change_password(user, data.current_password, data.new_password)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
