"""Sinh câu UPDATE đặt mật khẩu cho từng tài khoản (băm đúng chuẩn của backend).

Chạy trong thư mục backend:
    python scripts/make_password_sql.py admin:MatKhauAdmin1 provider1:MatKhauP1 customer001:MatKhauC1
Mỗi cặp là tên_đăng_nhập:mật_khẩu (mật khẩu >= 8 ký tự). Chép phần in ra vào SSMS rồi chạy.
Mỗi lần chạy sinh muối ngẫu nhiên khác nhau nên chuỗi băm luôn khác, vẫn đăng nhập đúng.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.security import hash_password  # noqa: E402


def main(pairs):
    if not pairs:
        sys.exit(__doc__)
    print("USE FilmPhotographyPlatform;\nGO")
    for p in pairs:
        user, sep, pw = p.partition(":")
        if not sep or not user or len(pw) < 8:
            sys.exit(f"Sai định dạng hoặc mật khẩu < 8 ký tự: {p!r} (cần tên:mậtkhẩu)")
        print(f"UPDATE dbo.Users SET password_hash = N'{hash_password(pw)}' WHERE username = N'{user.replace(chr(39), chr(39) * 2)}';")
    print("GO")


if __name__ == "__main__":
    main(sys.argv[1:])
