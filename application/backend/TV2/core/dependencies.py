"""Dependency dùng chung: phân quyền theo role."""
from fastapi import Depends, HTTPException, status

from booking.auth import get_current_user


def require_admin(user: dict = Depends(get_current_user)) -> dict:
    if user.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Chỉ admin mới được thực hiện thao tác này")
    return user
