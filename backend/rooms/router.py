from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from booking.schemas import to_local_naive
from core.dependencies import require_roles
from rooms import service
from rooms.schemas import RoomCreate, RoomOut, RoomType, RoomUpdate

router = APIRouter(prefix="/api/rooms", tags=["Rooms"])

manager = require_roles("ADMIN", "PROVIDER")


def _not_found(exc: Exception):
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


def _ensure_can_manage(user: dict, studio_id: Optional[int]) -> None:
    """ADMIN quản lý được mọi phòng; PROVIDER chỉ quản lý phòng thuộc studio của mình."""
    role = str(user["role"]).upper()
    if role == "ADMIN":
        return
    if role == "PROVIDER" and studio_id is not None:
        try:
            provider_id = service.get_studio_provider_id(studio_id)
        except service.StudioNotFoundError as exc:
            _not_found(exc)
        if provider_id == user["user_id"]:
            return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                        detail="Bạn không có quyền quản lý phòng của studio này")


@router.get("", response_model=List[RoomOut])
def list_rooms(
    studio_id: Optional[int] = Query(default=None, gt=0),
    room_type: Optional[RoomType] = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    return service.list_rooms(studio_id=studio_id, room_type=room_type, limit=limit, offset=offset)


@router.get("/available", response_model=List[RoomOut])
def available_rooms(
    start_time: datetime,
    end_time: datetime,
    room_type: Optional[RoomType] = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    start, end = to_local_naive(start_time), to_local_naive(end_time)
    if end <= start:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="end_time phải lớn hơn start_time")
    return service.list_available_rooms(start, end, room_type, limit, offset)


@router.get("/{room_id}", response_model=RoomOut)
def get_room(room_id: int):
    try:
        return service.get_room(room_id)
    except service.RoomNotFoundError as exc:
        _not_found(exc)


@router.post("", response_model=RoomOut, status_code=status.HTTP_201_CREATED)
def create_room(data: RoomCreate, user: dict = Depends(manager)):
    _ensure_can_manage(user, data.studio_id)
    try:
        return service.create_room(data.studio_id, data.name, data.room_type, data.capacity,
                                   data.price_per_hour, data.description, data.status)
    except service.StudioNotFoundError as exc:
        _not_found(exc)


@router.patch("/{room_id}", response_model=RoomOut)
def update_room(room_id: int, data: RoomUpdate, user: dict = Depends(manager)):
    try:
        room = service.get_room(room_id)
        _ensure_can_manage(user, room["studio_id"])
        return service.update_room(room_id, data.model_dump(exclude_unset=True))
    except service.RoomNotFoundError as exc:
        _not_found(exc)


@router.delete("/{room_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_room(room_id: int, user: dict = Depends(manager)):
    try:
        room = service.get_room(room_id)
        _ensure_can_manage(user, room["studio_id"])
        service.deactivate_room(room_id)
    except service.RoomNotFoundError as exc:
        _not_found(exc)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
