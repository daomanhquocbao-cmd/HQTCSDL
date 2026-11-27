"""Thanh toán VNPay (sandbox) theo tài liệu VNPay 2.1.0: ký HMAC-SHA512 trên chuỗi tham số đã sắp xếp.

Biến môi trường:
  VNPAY_TMN_CODE, VNPAY_HASH_SECRET   : lấy khi đăng ký sandbox tại sandbox.vnpayment.vn
  VNPAY_URL        (mặc định https://sandbox.vnpayment.vn/paymentv2/vpcpay.html)
  VNPAY_RETURN_URL (URL backend nhận redirect, vd http://127.0.0.1:8000/api/payments/vnpay/return)
  VNPAY_FRONT_URL  (trang web hiện kết quả sau khi thanh toán, mặc định /web/customer/customer-pc.html#bookings)
Cần URL công khai (ngrok) nếu muốn VNPay gọi IPN; redirect về trình duyệt thì localhost vẫn chạy.
"""
import hashlib
import hmac
import os
from datetime import datetime
from decimal import Decimal
from typing import Dict
from urllib.parse import quote_plus

from fastapi import HTTPException

from provider.service import _db, _drain, _err

DEFAULT_URL = "https://sandbox.vnpayment.vn/paymentv2/vpcpay.html"


def _cfg() -> dict:
    cfg = {"tmn": os.getenv("VNPAY_TMN_CODE", ""), "secret": os.getenv("VNPAY_HASH_SECRET", ""),
           "url": os.getenv("VNPAY_URL", DEFAULT_URL),
           "return_url": os.getenv("VNPAY_RETURN_URL", "http://127.0.0.1:8000/api/payments/vnpay/return"),
           "front": os.getenv("VNPAY_FRONT_URL", "/web/customer/customer-pc.html#bookings")}
    if not cfg["tmn"] or not cfg["secret"]:
        raise HTTPException(503, "Chưa cấu hình VNPAY_TMN_CODE / VNPAY_HASH_SECRET (đăng ký sandbox của VNPay).")
    return cfg


def _query(params: Dict[str, str]) -> str:
    return "&".join(f"{k}={quote_plus(str(v))}" for k, v in sorted(params.items()) if v not in (None, ""))


def sign(params: Dict[str, str], secret: str) -> str:
    return hmac.new(secret.encode(), _query(params).encode(), hashlib.sha512).hexdigest()


def build_url(reservation_id: int, amount: Decimal, ip: str, cfg: dict, now: datetime = None) -> str:
    now = now or datetime.now()
    params = {
        "vnp_Version": "2.1.0", "vnp_Command": "pay", "vnp_TmnCode": cfg["tmn"],
        "vnp_Amount": str(int(amount) * 100), "vnp_CurrCode": "VND",
        "vnp_TxnRef": f"{reservation_id}-{now:%H%M%S}", "vnp_OrderInfo": f"Thanh toan don {reservation_id}",
        "vnp_OrderType": "other", "vnp_Locale": "vn", "vnp_ReturnUrl": cfg["return_url"],
        "vnp_IpAddr": ip or "127.0.0.1", "vnp_CreateDate": f"{now:%Y%m%d%H%M%S}",
    }
    return f"{cfg['url']}?{_query(params)}&vnp_SecureHash={sign(params, cfg['secret'])}"


def verify(params: Dict[str, str], secret: str) -> bool:
    given = params.get("vnp_SecureHash", "")
    body = {k: v for k, v in params.items() if k.startswith("vnp_") and k not in ("vnp_SecureHash", "vnp_SecureHashType")}
    return bool(given) and hmac.compare_digest(sign(body, secret).lower(), given.lower())


def settle(params: Dict[str, str]) -> dict:
    """Ghi nhận thanh toán từ redirect/IPN. Idempotent theo mã giao dịch VNPay. Trả {ok, code, message}."""
    cfg = _cfg()
    if not verify(params, cfg["secret"]):
        return {"ok": False, "code": "97", "message": "Invalid signature"}
    try:
        rid = int(params.get("vnp_TxnRef", "").split("-")[0])
        amount = Decimal(params.get("vnp_Amount", "0")) / 100
    except (ValueError, ArithmeticError):
        return {"ok": False, "code": "01", "message": "Order not found"}
    if params.get("vnp_ResponseCode") != "00" or params.get("vnp_TransactionStatus", "00") != "00":
        return {"ok": False, "code": "00", "message": "Payment failed or cancelled"}
    tx = "VNP" + (params.get("vnp_TransactionNo") or params.get("vnp_TxnRef"))
    with _db() as cur:
        cur.execute("SELECT customer_id, total_amount FROM dbo.Reservations WHERE reservation_id = ?", rid)
        row = cur.fetchone()
        if row is None:
            return {"ok": False, "code": "01", "message": "Order not found"}
        cur.execute("SELECT 1 FROM dbo.Payments WHERE transaction_code = ?", tx)
        if cur.fetchone():
            return {"ok": True, "code": "02", "message": "Order already confirmed"}
        try:
            cur.execute("EXEC dbo.sp_ProcessPayment @reservation_id = ?, @amount = ?, @payment_method = 'VNPAY', "
                        "@actor_id = ?, @transaction_code = ?", rid, amount, row.customer_id, tx)
            _drain(cur)
        except HTTPException as exc:
            return {"ok": False, "code": "04", "message": str(exc.detail)}
    return {"ok": True, "code": "00", "message": "Confirm Success"}
