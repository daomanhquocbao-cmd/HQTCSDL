"""Đăng ký / đăng nhập người dùng (bảng Users)."""
from database import get_db_connection
from core.security import hash_password, verify_password


class UserError(Exception):
    pass


class DuplicateUserError(UserError):
    pass


class InvalidCredentialsError(UserError):
    pass


class UserNotFoundError(UserError):
    pass


def _to_dict(row) -> dict:
    return {"user_id": row.user_id, "username": row.username, "email": row.email,
            "phone": row.phone, "role": row.role}


def register_user(username: str, email: str, password: str, phone=None) -> dict:
    email = email.lower()
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM dbo.Users WHERE username = ? OR email = ?", username, email)
        if cur.fetchone() is not None:
            raise DuplicateUserError("Username hoặc email đã được đăng ký")
        cur.execute(
            """
            INSERT INTO dbo.Users (username, password_hash, email, phone, role)
            OUTPUT INSERTED.user_id
            VALUES (?, ?, ?, ?, 'CUSTOMER')
            """,
            username, hash_password(password), email, phone,
        )
        user_id = int(cur.fetchone()[0])
        conn.commit()
        return {"user_id": user_id, "username": username, "email": email,
                "phone": phone, "role": "CUSTOMER"}
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
            "SELECT user_id, username, email, phone, role, password_hash "
            "FROM dbo.Users WHERE username = ?", username,
        )
        row = cur.fetchone()
        if row is None or not verify_password(password, row.password_hash):
            raise InvalidCredentialsError("Username hoặc mật khẩu không đúng")
        return _to_dict(row)
    finally:
        conn.close()


def get_user(user_id: int) -> dict:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT user_id, username, email, phone, role FROM dbo.Users WHERE user_id = ?", user_id)
        row = cur.fetchone()
        if row is None:
            raise UserNotFoundError("Không tìm thấy người dùng")
        return _to_dict(row)
    finally:
        conn.close()
