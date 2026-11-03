"""Đăng ký / đăng nhập người dùng."""
from database import get_db_connection
from core.security import hash_password, verify_password


class UserError(Exception):
    pass


class DuplicateEmailError(UserError):
    pass


class InvalidCredentialsError(UserError):
    pass


class UserNotFoundError(UserError):
    pass


def register_user(full_name: str, email: str, password: str) -> dict:
    email = email.lower()
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM Users WHERE email = ?", email)
        if cur.fetchone() is not None:
            raise DuplicateEmailError("Email đã được đăng ký")
        cur.execute(
            """
            INSERT INTO Users (full_name, email, password_hash, role)
            OUTPUT INSERTED.user_id
            VALUES (?, ?, ?, 'customer')
            """,
            full_name, email, hash_password(password),
        )
        user_id = int(cur.fetchone()[0])
        conn.commit()
        return {"user_id": user_id, "full_name": full_name, "email": email, "role": "customer"}
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def authenticate(email: str, password: str) -> dict:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT user_id, full_name, email, role, password_hash FROM Users WHERE email = ?",
            email.lower(),
        )
        row = cur.fetchone()
        if row is None or not row.password_hash or not verify_password(password, row.password_hash):
            raise InvalidCredentialsError("Email hoặc mật khẩu không đúng")
        return {"user_id": row.user_id, "full_name": row.full_name,
                "email": row.email, "role": row.role}
    finally:
        conn.close()


def get_user(user_id: int) -> dict:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT user_id, full_name, email, role FROM Users WHERE user_id = ?", user_id)
        row = cur.fetchone()
        if row is None:
            raise UserNotFoundError("Không tìm thấy người dùng")
        return {"user_id": row.user_id, "full_name": row.full_name,
                "email": row.email, "role": row.role}
    finally:
        conn.close()
