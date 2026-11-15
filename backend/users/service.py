"""Đăng ký / đăng nhập người dùng (bảng dbo.Users)."""
from typing import Optional
from database import get_db_connection
from core.security import hash_password, verify_password


class UserError(Exception):
    pass


class DuplicateUserError(UserError):
    pass


class InvalidCredentialsError(UserError):
    pass


class AccountLockedError(UserError):
    pass


class UserNotFoundError(UserError):
    pass


def _to_dict(row) -> dict:
    return {
        "user_id": row.user_id,
        "username": row.username,
        "email": row.email,
        "full_name": row.full_name,
        "phone": row.phone,
        "role": row.role,
        "status": row.status,
    }


def register_user(
    username: str,
    email: str,
    password: str,
    full_name: str,
    phone: Optional[str] = None,
    role: str = "CUSTOMER",
) -> dict:
    email = email.lower().strip()
    role = (role or "CUSTOMER").upper()
    if role not in ("CUSTOMER", "PROVIDER", "EXPERT"):
        role = "CUSTOMER"

    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM dbo.Users WHERE username = ? OR email = ?", username, email)
        if cur.fetchone() is not None:
            raise DuplicateUserError("Username hoặc email đã được đăng ký")

        cur.execute(
            """
            INSERT INTO dbo.Users (username, password_hash, email, phone, full_name, role, status)
            OUTPUT INSERTED.user_id, INSERTED.status
            VALUES (?, ?, ?, ?, ?, ?, 'ACTIVE')
            """,
            username,
            hash_password(password),
            email,
            phone,
            full_name,
            role,
        )
        inserted = cur.fetchone()
        user_id = int(inserted[0])
        status = str(inserted[1])
        conn.commit()
        return {
            "user_id": user_id,
            "username": username,
            "email": email,
            "full_name": full_name,
            "phone": phone,
            "role": role,
            "status": status,
        }
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def authenticate(username: str, password: str) -> dict:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT user_id, username, email, phone, full_name, role, status, password_hash
            FROM dbo.Users
            WHERE username = ?
            """,
            username,
        )
        row = cur.fetchone()
        if row is None or not verify_password(password, row.password_hash):
            raise InvalidCredentialsError("Username hoặc mật khẩu không đúng")
        if str(row.status).upper() == "SUSPENDED":
            raise AccountLockedError("Tài khoản của bạn đã bị khóa. Vui lòng liên hệ quản trị viên.")
        return _to_dict(row)
    finally:
        conn.close()


def get_user(user_id: int) -> dict:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT user_id, username, email, phone, full_name, role, status
            FROM dbo.Users
            WHERE user_id = ?
            """,
            user_id,
        )
        row = cur.fetchone()
        if row is None:
            raise UserNotFoundError("Không tìm thấy người dùng")
        return _to_dict(row)
    finally:
        conn.close()
