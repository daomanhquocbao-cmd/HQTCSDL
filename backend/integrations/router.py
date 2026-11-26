from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field

from core.config import settings
from core.dependencies import require_customer
from core.security import create_access_token
from customer.service import booking_detail
from integrations import google_oauth, vnpay

router = APIRouter(tags=["Integrations"])


class GoogleIn(BaseModel):
    id_token: str = Field(min_length=20)


@router.post("/api/auth/google")
def google_login(data: GoogleIn):
    user = google_oauth.login_with_google(data.id_token)
    token = create_access_token(user["user_id"], user["role"], settings.access_token_minutes)
    return {"access_token": token, "token_type": "bearer", "user": user}


@router.get("/api/auth/google/config")
def google_config():
    """Client dùng để biết có hiện nút Google hay không."""
    ids = google_oauth.client_ids()
    return {"enabled": bool(ids), "client_id": ids[0] if ids else None}


class VnpayIn(BaseModel):
    reservation_id: int = Field(gt=0)


@router.post("/api/payments/vnpay/create")
def vnpay_create(data: VnpayIn, request: Request, user: dict = Depends(require_customer)):
    booking = booking_detail(user, data.reservation_id)  # 404 nếu không phải đơn của khách
    due = Decimal(str(booking["balance_due"]))
    if booking["status"] not in ("PENDING", "CONFIRMED", "IN_USE") or due <= 0:
        raise HTTPException(409, "Đơn này không còn khoản nào cần thanh toán.")
    ip = request.client.host if request.client else "127.0.0.1"
    return {"payment_url": vnpay.build_url(data.reservation_id, due, ip, vnpay._cfg()), "amount": float(due)}


@router.get("/api/payments/vnpay/return")
def vnpay_return(request: Request):
    """VNPay chuyển trình duyệt về đây; ghi nhận thanh toán rồi đưa người dùng về trang đơn."""
    res = vnpay.settle(dict(request.query_params))
    front = vnpay._cfg()["front"]
    sep = "&" if "?" in front else "?"
    return RedirectResponse(f"{front.split('#')[0]}{sep}pay={'ok' if res['ok'] else 'fail'}#bookings")


@router.get("/api/payments/vnpay/ipn")
def vnpay_ipn(request: Request):
    res = vnpay.settle(dict(request.query_params))
    return {"RspCode": res["code"] if res["ok"] or res["code"] in ("97", "01", "02", "04") else "00",
            "Message": res["message"]}
