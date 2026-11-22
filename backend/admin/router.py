"""Endpoint quản trị: /api/admin/* (chỉ ADMIN)."""
from typing import Literal, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from admin import service
from core.dependencies import require_admin

router = APIRouter(prefix="/api/admin", tags=["Admin"])
Admin = Depends(require_admin)


class ProviderStatusIn(BaseModel):
    status: Literal["ACTIVE", "SUSPENDED"]


class StudioStatusIn(BaseModel):
    status: Literal["APPROVED", "REJECTED", "SUSPENDED"]


@router.get("/overview")
def overview(user: dict = Admin):
    return service.overview()


@router.get("/providers")
def providers(status: Optional[Literal["PENDING", "ACTIVE", "SUSPENDED"]] = Query(None), user: dict = Admin):
    return service.list_providers(status)


@router.patch("/providers/{user_id}")
def set_provider(user_id: int, data: ProviderStatusIn, user: dict = Admin):
    return service.set_provider_status(user, user_id, data.status)


@router.get("/studios")
def studios(status: Optional[Literal["PENDING", "APPROVED", "REJECTED", "SUSPENDED"]] = Query(None),
            user: dict = Admin):
    return service.list_studios(status)


@router.patch("/studios/{studio_id}")
def set_studio(studio_id: int, data: StudioStatusIn, user: dict = Admin):
    return service.set_studio_status(studio_id, data.status)
