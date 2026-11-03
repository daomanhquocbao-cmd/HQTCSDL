from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from booking.auth import get_current_user
from core.dependencies import require_roles
from studios import service
from studios.schemas import ReviewCreate, ReviewOut, StudioCreate, StudioOut

router = APIRouter(prefix="/api/studios", tags=["Studios"])


def _not_found(exc: Exception):
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get("", response_model=List[StudioOut])
def list_studios(
    keyword: Optional[str] = Query(default=None, max_length=100),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    return service.list_studios(limit, offset, keyword)


@router.get("/{studio_id}", response_model=StudioOut)
def get_studio(studio_id: int):
    try:
        return service.get_studio(studio_id)
    except service.StudioNotFoundError as exc:
        _not_found(exc)


@router.post("", response_model=StudioOut, status_code=status.HTTP_201_CREATED)
def create_studio(data: StudioCreate, user: dict = Depends(require_roles("ADMIN", "PROVIDER"))):
    return service.create_studio(user["user_id"], data.name, data.address, data.description, data.phone)


@router.get("/{studio_id}/reviews", response_model=List[ReviewOut])
def list_reviews(
    studio_id: int,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    try:
        return service.list_reviews(studio_id, limit, offset)
    except service.StudioNotFoundError as exc:
        _not_found(exc)


@router.post("/{studio_id}/reviews", response_model=ReviewOut, status_code=status.HTTP_201_CREATED)
def add_review(studio_id: int, data: ReviewCreate, user: dict = Depends(get_current_user)):
    try:
        return service.add_review(studio_id, user["user_id"], data.rating, data.comment)
    except service.StudioNotFoundError as exc:
        _not_found(exc)
