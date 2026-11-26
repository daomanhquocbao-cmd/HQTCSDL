"""Endpoint AI cho khách hàng: /api/ai/*."""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from ai import service
from core.security import JWT_ALGORITHM, JWT_SECRET

router = APIRouter(prefix="/api/ai", tags=["AI"])
_bearer = HTTPBearer(auto_error=False)


def optional_user_id(credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer)) -> Optional[int]:
    """Có token hợp lệ -> cá nhân hóa theo khách; không có -> gợi ý chung."""
    if not credentials:
        return None
    try:
        return int(jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])["sub"])
    except (JWTError, KeyError, ValueError):
        return None


@router.get("/recommendations")
def recommendations(top: int = Query(5, ge=1, le=20), user_id: Optional[int] = Depends(optional_user_id)):
    return {"personalized": user_id is not None, "items": service.recommend(user_id, top)}


@router.get("/ask")
def ask(q: str = Query(min_length=2, max_length=300), limit: int = Query(6, ge=1, le=20)):
    return service.ask(q, limit)


@router.get("/suggest-room-extras")
def suggest_extras(room_id: int = Query(gt=0), limit: int = Query(5, ge=1, le=10)):
    """Thiết bị và gói nên thêm khi đặt phòng này."""
    return service.suggest_for_room(room_id, limit)
