from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Optional
from booking.schemas import CreateBookingSchema
from booking.services import BookingService
from booking.models import BookingModel
from middlewares.auth import get_current_user

router = APIRouter(prefix="/api/bookings", tags=["Booking"])

@router.post("", status_code=201)
def create_booking(data: CreateBookingSchema, current_user: dict = Depends(get_current_user)):
    return BookingService.create_new_booking(user_id=current_user["user_id"], data=data)

@router.get("")
def get_bookings(
    status: Optional[str] = Query(None),
    user_id: Optional[int] = Query(None),
    current_user: dict = Depends(get_current_user)):
    return BookingModel.get_all_bookings(status_filter=status, user_id=user_id)

@router.get("/{booking_id}")
def get_booking_detail(booking_id: int, current_user: dict = Depends(get_current_user)):
    booking = BookingModel.get_booking_by_id(booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Không tìm thấy lịch đặt.")
    return booking

@router.delete("/{booking_id}/cancel")
def cancel_booking(booking_id: int, current_user: dict = Depends(get_current_user)):
    return BookingService.cancel_booking(booking_id, current_user)

@router.patch("/{booking_id}/confirm")
def confirm_booking(booking_id: int, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Yêu cầu quyền Admin.")
    success = BookingModel.update_status(booking_id, "CONFIRMED")
    if not success:
        raise HTTPException(status_code=404, detail="Không tìm thấy lịch đặt.")
    return {"message": "Đã xác nhận lịch đặt thành công."}