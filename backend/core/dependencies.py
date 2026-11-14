"""Dependency dùng chung: phân quyền theo role (ADMIN, EXPERT, PROVIDER, CUSTOMER)."""
from fastapi import Depends, HTTPException, status
from booking.auth import get_current_user


def require_roles(*roles: str):
    allowed = {r.upper() for r in roles}

    def checker(user: dict = Depends(get_current_user)) -> dict:
        if str(user.get("role", "")).upper() not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bạn không có quyền thực hiện thao tác này"
            )
        return user

    return checker


require_admin = require_roles("ADMIN")
