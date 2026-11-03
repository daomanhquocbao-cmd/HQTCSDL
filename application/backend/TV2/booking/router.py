"""Các endpoint /api/bookings."""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from booking import service
from booking.auth import get_current_user
from booking.schemas import BookingCreate, BookingOut, BookingStatus

router = APIRouter(prefix="/api/bookings", tags=["Bookings"])

_ERROR_MAP = {
    service.RoomNotFoundError: status.HTTP_404_NOT_FOUND,
    service.BookingNotFoundError: status.HTTP_404_NOT_FOUND,
    service.TimeConflictError: status.HTTP_409_CONFLICT,
    service.PermissionDeniedError: status.HTTP_403_FORBIDDEN,
    service.InvalidStateError: status.HTTP_400_BAD_REQUEST,
}


def _raise_http(exc: service.BookingError):
    code = _ERROR_MAP.get(type(exc), status.HTTP_400_BAD_REQUEST)
    raise HTTPException(status_code=code, detail=str(exc))


@router.post("", response_model=BookingOut, status_code=status.HTTP_201_CREATED)
def create_booking(data: BookingCreate, user: dict = Depends(get_current_user)):
    try:
        return service.create_booking(user["user_id"], data)
    except service.BookingError as exc:
        _raise_http(exc)


@router.get("", response_model=List[BookingOut])
def list_my_bookings(
    status_filter: Optional[BookingStatus] = Query(default=None, alias="status"),
    user: dict = Depends(get_current_user),
):
    return service.list_my_bookings(
        user["user_id"], status_filter.value if status_filter else None
    )


@router.get("/{booking_id}", response_model=BookingOut)
def get_booking(booking_id: int, user: dict = Depends(get_current_user)):
    try:
        return service.get_booking(booking_id, user["user_id"], user["role"])
    except service.BookingError as exc:
        _raise_http(exc)


@router.patch("/{booking_id}/cancel", response_model=BookingOut)
def cancel_booking(booking_id: int, user: dict = Depends(get_current_user)):
    try:
        return service.cancel_booking(booking_id, user["user_id"], user["role"])
    except service.BookingError as exc:
        _raise_http(exc)
