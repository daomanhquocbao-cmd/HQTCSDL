"""Kiểm tra kết nối SQL Server. Chạy trong thư mục backend: python scripts/check_db.py"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

from database import get_db_connection  # noqa: E402


def main():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT DB_NAME()")
    print("Kết nối OK, database:", cur.fetchone()[0])
    cur.execute("SELECT COUNT(*) FROM sys.tables")
    print("Số bảng:", cur.fetchone()[0])
    conn.close()


if __name__ == "__main__":
    main()
