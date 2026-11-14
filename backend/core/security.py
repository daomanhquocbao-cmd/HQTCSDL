"""Băm và kiểm tra mật khẩu bằng PBKDF2-HMAC-SHA256 (chỉ dùng thư viện chuẩn)."""
import hashlib
import hmac
import os

ALGORITHM = "pbkdf2_sha256"
ITERATIONS = 120_000


def hash_password(password: str) -> str:
    """Tạo salt ngẫu nhiên 16 bytes và băm mật khẩu với 120,000 vòng lặp."""
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS)
    return f"{ALGORITHM}${ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Xác thực mật khẩu đầu vào với chuỗi hash trong CSDL."""
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
