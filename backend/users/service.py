"""Xử lý nghiệp vụ Đăng ký / Đăng nhập / Lấy thông tin người dùng."""
from database import get_db_connection
from core.security import hash_password, verify_password

class UserError(Exception): pass
class DuplicateUserError(UserError): pass
class InvalidCredentialsError(UserError): pass
class AccountLockedError(UserError): pass
class UserNotFoundError(UserError): pass

ALLOWED_ROLES = {"CUSTOMER", "PROVIDER", "EXPERT"}

def _to_dict(row) -> dict:
    return {
        "user_id": row.user_id,
        "username": row.username,
        "email": row.email,
        "full_name": row.full_name,
        "phone": row.phone,
        "role": row.role,
        "status": row.status
    }

def register_user(username: str, email: str, password: str, full_name: str, phone: str = None, role: str = "CUSTOMER") -> dict:
    email = email.lower()
    role_clean = role.upper() if role else "CUSTOMER"
    if role_clean not in ALLOWED_ROLES:
        role_clean = "CUSTOMER"

    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM dbo.Users WHERE username = ? OR email = ?", username, email)
        if cur.fetchone() is not None:
            raise DuplicateUserError("Tên đăng nhập hoặc email đã tồn tại")
        
        cur.execute(
            """
            INSERT INTO dbo.Users (username, password_hash, email, phone, full_name, role, status)
            OUTPUT INSERTED.user_id, INSERTED.status
            VALUES (?, ?, ?, ?, ?, ?, 'ACTIVE')
            """,
            username, hash_password(password), email, phone, full_name, role_clean,
        )
        inserted = cur.fetchone()
        user_id = int(inserted[0])
        status_str = str(inserted[1])
        conn.commit()
        
        return {
            "user_id": user_id,
            "username": username,
            "email": email,
            "full_name": full_name,
            "phone": phone,
            "role": role_clean,
            "status": status_str
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
            "SELECT user_id, username, email, full_name, phone, role, status, password_hash "
            "FROM dbo.Users WHERE username = ?", username
        )
        row = cur.fetchone()
        if row is None or not verify_password(password, row.password_hash):
            raise InvalidCredentialsError("Mật khẩu hoặc tên đăng nhập không chính xác")
        
        if row.status == "SUSPENDED":
            raise AccountLockedError("Tài khoản của bạn đã bị khóa. Vui lòng liên hệ Admin.")
        if row.status == "PENDING":
            raise AccountLockedError("Tài khoản đang chờ duyệt từ Quản trị viên.")
            
        return _to_dict(row)
    finally:
        conn.close()

def get_user(user_id: int) -> dict:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT user_id, username, email, full_name, phone, role, status "
            "FROM dbo.Users WHERE user_id = ?", user_id
        )
        row = cur.fetchone()
        if row is None:
            raise UserNotFoundError("Không tìm thấy người dùng")
        return _to_dict(row)
    finally:
        conn.close()
