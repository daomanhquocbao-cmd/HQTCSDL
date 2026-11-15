"""Xác thực JWT cho module booking."""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

# Dùng chung khóa và hàm tạo token với core.security để token do /api/users/login cấp
# được mọi router chấp nhận (trước đây hai nơi có secret mặc định khác nhau).
from core.security import JWT_ALGORITHM, JWT_SECRET, create_access_token  # noqa: F401

# HTTPBearer trả 403 khi thiếu header Authorization
security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """Giải mã token và trả về {'user_id': int, 'role': str}."""
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
