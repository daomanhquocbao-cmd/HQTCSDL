from typing import List

from fastapi import APIRouter, Depends, HTTPException, Response, status

from core.dependencies import require_admin
from rooms import service
from rooms.schemas import RoomCreate, RoomOut, RoomUpdate

router = APIRouter(prefix="/api/rooms", tags=["Rooms"])


def _not_found(exc: Exception):
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get("", response_model=List[RoomOut])
def list_rooms():
    return service.list_rooms(only_active=True)


@router.get("/{room_id}", response_model=RoomOut)
def get_room(room_id: int):
    try:
        return service.get_room(room_id)
    except service.RoomNotFoundError as exc:
        _not_found(exc)


@router.post("", response_model=RoomOut, status_code=status.HTTP_201_CREATED)
def create_room(data: RoomCreate, _admin: dict = Depends(require_admin)):
    return service.create_room(data.name, data.description, data.hourly_price)


@router.patch("/{room_id}", response_model=RoomOut)
def update_room(room_id: int, data: RoomUpdate, _admin: dict = Depends(require_admin)):
    try:
        return service.update_room(room_id, data.model_dump(exclude_unset=True))
    except service.RoomNotFoundError as exc:
        _not_found(exc)


@router.delete("/{room_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_room(room_id: int, _admin: dict = Depends(require_admin)):
    try:
        service.deactivate_room(room_id)
    except service.RoomNotFoundError as exc:
        _not_found(exc)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
