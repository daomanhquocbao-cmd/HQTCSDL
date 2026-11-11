"""Băm mật khẩu và Xử lý JWT Token tập trung tại Core."""
import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from core.config import settings

ALGORITHM = "pbkdf2_sha256"
ITERATIONS = 120_000

JWT_SECRET = os.getenv("JWT_SECRET", "film-platform-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"

security_bearer = HTTPBearer(auto_error=False)

# --- BĂM & KIỂM TRA MẬT KHẨU ---
def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS)
    return f"{ALGORITHM}${ITERATIONS}${salt.hex()}${digest.hex()}"

def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, iterations, salt_hex, hash_hex = stored_hash.split("$")
        if algorithm != ALGORITHM:
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(iterations)
        )
    except (ValueError, AttributeError):
        return False
    return hmac.compare_digest(digest.hex(), hash_hex)

# --- XỬ LÝ JWT TOKEN ---
def create_access_token(user_id: int, role: str = "CUSTOMER", expires_minutes: int = 60) -> str:
    payload = {
        "sub": str(user_id),
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=expires_minutes),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_bearer),
) -> dict:
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Yêu cầu Token xác thực (Authorization Bearer)",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = int(payload["sub"])
    except (JWTError, KeyError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token không hợp lệ hoặc đã hết hạn",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {"user_id": user_id, "role": payload.get("role", "CUSTOMER")}
