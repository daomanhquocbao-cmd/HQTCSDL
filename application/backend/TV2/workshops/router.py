from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from booking.auth import get_current_user
from core.dependencies import require_roles
from workshops import service
from workshops.schemas import RegistrationOut, WorkshopCreate, WorkshopOut

router = APIRouter(prefix="/api/workshops", tags=["Workshops"])

_ERROR_MAP = {
    service.WorkshopNotFoundError: status.HTTP_404_NOT_FOUND,
    service.AlreadyRegisteredError: status.HTTP_409_CONFLICT,
    service.WorkshopFullError: status.HTTP_409_CONFLICT,
}


def _raise_http(exc: service.WorkshopError):
    raise HTTPException(status_code=_ERROR_MAP.get(type(exc), status.HTTP_400_BAD_REQUEST), detail=str(exc))


@router.get("", response_model=List[WorkshopOut])
def list_workshops(
    upcoming_only: bool = False,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    return service.list_workshops(upcoming_only, limit, offset)


@router.get("/me/registrations", response_model=List[WorkshopOut])
def my_registrations(user: dict = Depends(get_current_user)):
    return service.list_my_workshops(user["user_id"])


@router.get("/{workshop_id}", response_model=WorkshopOut)
def get_workshop(workshop_id: int):
    try:
        return service.get_workshop(workshop_id)
    except service.WorkshopError as exc:
        _raise_http(exc)


@router.post("", response_model=WorkshopOut, status_code=status.HTTP_201_CREATED)
def create_workshop(data: WorkshopCreate, user: dict = Depends(require_roles("ADMIN", "EXPERT"))):
    return service.create_workshop(user["user_id"], data.title, data.description,
                                   data.capacity, data.start_time, data.end_time)


@router.post("/{workshop_id}/register", response_model=RegistrationOut, status_code=status.HTTP_201_CREATED)
def register(workshop_id: int, user: dict = Depends(get_current_user)):
    try:
        return service.register(workshop_id, user["user_id"])
    except service.WorkshopError as exc:
        _raise_http(exc)


@router.delete("/{workshop_id}/register", status_code=status.HTTP_204_NO_CONTENT)
def unregister(workshop_id: int, user: dict = Depends(get_current_user)):
    try:
        service.unregister(workshop_id, user["user_id"])
    except service.WorkshopError as exc:
        _raise_http(exc)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
