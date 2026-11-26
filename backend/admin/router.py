"""Endpoint quản trị: /api/admin/* (chỉ ADMIN)."""
from typing import Literal, Optional

from typing import Union

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


class UserStatusIn(BaseModel):
    status: Literal["ACTIVE", "SUSPENDED"]


class SettingIn(BaseModel):
    value: Union[bool, int, float, str]


@router.get("/users")
def users(role: Optional[Literal["CUSTOMER", "EXPERT", "PROVIDER", "ADMIN"]] = None,
          status: Optional[Literal["ACTIVE", "PENDING", "SUSPENDED"]] = None,
          q: Optional[str] = Query(None, max_length=100), limit: int = Query(50, ge=1, le=200),
          offset: int = Query(0, ge=0), user: dict = Admin):
    return service.list_users(role, status, q, limit, offset)


@router.patch("/users/{user_id}")
def set_user(user_id: int, data: UserStatusIn, user: dict = Admin):
    return service.set_user_status(user, user_id, data.status)


@router.get("/payments")
def payments(status: Optional[Literal["PENDING", "SUCCESS", "FAILED", "REFUNDED"]] = None,
             q: Optional[str] = Query(None, max_length=100), limit: int = Query(50, ge=1, le=200),
             offset: int = Query(0, ge=0), user: dict = Admin):
    return service.list_payments(status, q, limit, offset)


@router.post("/payments/{payment_id}/refund")
def refund(payment_id: int, user: dict = Admin):
    return service.refund_payment(user, payment_id)


@router.get("/settings")
def settings(user: dict = Admin):
    return service.list_settings()


@router.put("/settings/{key}")
def put_setting(key: str, data: SettingIn, user: dict = Admin):
    return service.update_setting(user, key, data.value)


@router.get("/reports")
def reports(months: int = Query(6, ge=1, le=24), user: dict = Admin):
    return service.reports(months)
