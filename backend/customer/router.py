"""Endpoint dành cho khách hàng: /api/customer/*."""
from datetime import date, datetime
from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from booking.schemas import to_local_naive
from core.dependencies import require_customer
from customer import service

router = APIRouter(prefix="/api/customer", tags=["Customer"])
User = Depends(require_customer)

Method = Literal["VNPAY", "MOMO", "STRIPE", "CASH", "BANK_TRANSFER"]


class EquipmentIn(BaseModel):
    equipment_id: int = Field(gt=0)
    quantity: int = Field(1, gt=0, le=100)


class PackageIn(BaseModel):
    package_id: int = Field(gt=0)
    notes: Optional[str] = Field(None, max_length=500)


class PayIn(BaseModel):
    amount: float = Field(gt=0)
    payment_method: Method
    transaction_code: Optional[str] = Field(None, max_length=100)


class ReviewIn(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: Optional[str] = Field(None, max_length=2000)


class DisputeIn(BaseModel):
    reason: str = Field(min_length=5, max_length=2000)


# --- tìm phòng (công khai)
@router.get("/rooms")
def search_rooms(q: Optional[str] = Query(None, max_length=100), room_type: Optional[Literal["STUDIO", "DARKROOM"]] = None,
                 city: Optional[str] = None, min_price: Optional[float] = Query(None, ge=0),
                 max_price: Optional[float] = Query(None, ge=0), capacity: Optional[int] = Query(None, ge=1),
                 sort: Literal["rating", "price_asc", "price_desc", "capacity", "newest"] = "rating",
                 start_time: Optional[datetime] = None, end_time: Optional[datetime] = None,
                 limit: int = Query(30, ge=1, le=100), offset: int = Query(0, ge=0)):
    start = to_local_naive(start_time) if start_time else None
    end = to_local_naive(end_time) if end_time else None
    if (start is None) != (end is None) or (start and end <= start):
        raise HTTPException(status_code=422, detail="Cần nhập cả start_time và end_time, end_time phải sau start_time")
    return service.search_rooms(q, room_type, city, min_price, max_price, capacity, sort, limit, offset, start, end)


@router.get("/cities")
def cities():
    return service.list_cities()


@router.get("/rooms/{room_id}")
def room_detail(room_id: int):
    return service.room_detail(room_id)


@router.get("/rooms/{room_id}/busy")
def busy(room_id: int, day: date = Query(alias="date")):
    return service.busy_slots(room_id, day)


# --- đơn của tôi
@router.get("/overview")
def overview(user: dict = User):
    return service.overview(user)


@router.get("/bookings")
def my_bookings(status: Optional[Literal["PENDING", "CONFIRMED", "IN_USE", "COMPLETED", "CANCELLED"]] = None,
                limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0), user: dict = User):
    return service.list_bookings(user, status, limit, offset)


@router.get("/bookings/{reservation_id}")
def booking_detail(reservation_id: int, user: dict = User):
    return service.booking_detail(user, reservation_id)


@router.post("/bookings/{reservation_id}/equipment")
def add_equipment(reservation_id: int, data: EquipmentIn, user: dict = User):
    return service.add_equipment(user, reservation_id, data.equipment_id, data.quantity)


@router.post("/bookings/{reservation_id}/packages")
def add_package(reservation_id: int, data: PackageIn, user: dict = User):
    return service.add_package(user, reservation_id, data.package_id, data.notes)


@router.post("/bookings/{reservation_id}/payments")
def pay(reservation_id: int, data: PayIn, user: dict = User):
    return service.pay(user, reservation_id, data.amount, data.payment_method, data.transaction_code)


@router.post("/bookings/{reservation_id}/cancel")
def cancel(reservation_id: int, user: dict = User):
    return service.cancel(user, reservation_id)


@router.post("/bookings/{reservation_id}/disputes", status_code=201)
def dispute(reservation_id: int, data: DisputeIn, user: dict = User):
    return service.raise_dispute(user, reservation_id, data.reason)


@router.post("/bookings/{reservation_id}/review", status_code=201)
def review(reservation_id: int, data: ReviewIn, user: dict = User):
    return service.review_booking(user, reservation_id, data.rating, data.comment)
