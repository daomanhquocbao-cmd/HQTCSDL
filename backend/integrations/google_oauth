"""Đăng nhập Google (OAuth 2.0 / OpenID Connect).

Client (web hoặc Flutter) lấy `id_token` từ Google rồi gửi lên POST /api/auth/google.
Backend hỏi Google xác thực token (endpoint tokeninfo), kiểm tra `aud` khớp GOOGLE_CLIENT_ID và email đã xác minh,
sau đó tìm hoặc tạo tài khoản CUSTOMER và cấp JWT của hệ thống như đăng nhập thường.
Biến môi trường: GOOGLE_CLIENT_ID (nhiều giá trị cách nhau dấu phẩy: web, android, ios).
"""
import json
import os
import re
import secrets
import urllib.parse
import urllib.request
from typing import Optional

from fastapi import HTTPException

from core.security import hash_password
from database import get_db_connection
from users.service import _to_dict

TOKENINFO_URL = "https://oauth2.googleapis.com/tokeninfo?id_token="
ISSUERS = ("accounts.google.com", "https://accounts.google.com")


def client_ids() -> list:
    return [c.strip() for c in os.getenv("GOOGLE_CLIENT_ID", "").split(",") if c.strip()]


def fetch_tokeninfo(id_token: str) -> dict:
    try:
        with urllib.request.urlopen(TOKENINFO_URL + urllib.parse.quote(id_token), timeout=8) as r:
            return json.loads(r.read().decode())
    except Exception as exc:  # noqa: BLE001 - mọi lỗi mạng/HTTP đều coi là token không hợp lệ
        raise HTTPException(401, "Google từ chối token hoặc không kết nối được Google") from exc


def check_claims(info: dict, allowed: list) -> dict:
    """Kiểm tra claims; trả {email, name}. Tách riêng để kiểm thử không cần mạng."""
    if not allowed:
        raise HTTPException(503, "Chưa cấu hình GOOGLE_CLIENT_ID trên server.")
    if info.get("aud") not in allowed:
        raise HTTPException(401, "Token không dành cho ứng dụng này.")
    if info.get("iss") not in ISSUERS:
        raise HTTPException(401, "Nguồn phát hành token không hợp lệ.")
    if str(info.get("email_verified")).lower() != "true" or not info.get("email"):
        raise HTTPException(401, "Email Google chưa được xác minh.")
    return {"email": info["email"].lower().strip(), "name": info.get("name") or info["email"].split("@")[0]}


def _username_for(cur, email: str) -> str:
    base = re.sub(r"[^A-Za-z0-9_.]", "", email.split("@")[0])[:30] or "user"
    if len(base) < 3:
        base += "_gg"
    name = base
    while True:
        cur.execute("SELECT 1 FROM dbo.Users WHERE username = ?", name)
        if cur.fetchone() is None:
            return name
        name = f"{base}{secrets.randbelow(9000) + 1000}"


def login_with_google(id_token: str, info: Optional[dict] = None) -> dict:
    claims = check_claims(info if info is not None else fetch_tokeninfo(id_token), client_ids())
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT user_id, username, email, phone, full_name, role, status FROM dbo.Users WHERE email = ?",
                    claims["email"])
        row = cur.fetchone()
        if row is not None:
            if str(row.status).upper() == "SUSPENDED":
                raise HTTPException(403, "Tài khoản của bạn đã bị khóa. Vui lòng liên hệ quản trị viên.")
            return _to_dict(row)
        username = _username_for(cur, claims["email"])
        cur.execute(
            "INSERT INTO dbo.Users (username, password_hash, email, full_name, role, status) "
            "OUTPUT INSERTED.user_id VALUES (?, ?, ?, ?, 'CUSTOMER', 'ACTIVE')",
            username, hash_password(secrets.token_urlsafe(24)), claims["email"], claims["name"][:100])
        uid = int(cur.fetchone()[0])
        conn.commit()
        return {"user_id": uid, "username": username, "email": claims["email"], "full_name": claims["name"][:100],
                "phone": None, "role": "CUSTOMER", "status": "ACTIVE"}
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
