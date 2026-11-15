"""Kiểm tra kết nối và cấu trúc database SQL Server cho backend.

Chạy trong thư mục backend:
    python scripts/check_db.py

Script kiểm tra lần lượt:
  1. Kết nối tới SQL Server (cấu hình đọc từ file .env hoặc biến môi trường).
  2. Phiên bản SQL Server và tên database đang dùng.
  3. Các bảng mà backend cần, kèm số dòng ước lượng.
  4. Các stored procedure và view mà backend gọi.

Kết thúc với mã thoát 0 nếu mọi thứ đầy đủ, 1 nếu lỗi kết nối hoặc còn thiếu.
"""
import os
import sys

# Cho phép `import database` dù chạy script từ thư mục nào.
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

from dotenv import load_dotenv  # noqa: E402

# Nạp .env TRƯỚC khi import database (database.py đọc biến môi trường ngay lúc import).
load_dotenv(os.path.join(BACKEND_DIR, ".env"))

import pyodbc  # noqa: E402
from database import DB_NAME, DB_SERVER, DB_USER, get_db_connection  # noqa: E402

# Bảng, stored procedure, view mà code trong backend/ đang dùng (tạo bởi database/01 và 03).
EXPECTED_TABLES = [
    "Users", "Studios", "Rooms", "Equipment", "EquipmentMaintenance",
    "ServicePackages", "PackageEquipment", "Reservations", "ReservationEquipments",
    "ReservationPackages", "ServiceSessions", "ReservationStatusHistory",
    "Payments", "Reviews", "Workshops", "WorkshopRegistrations",
]
EXPECTED_PROCEDURES = [
    "sp_CreateReservation", "sp_AddReservationEquipment", "sp_AddReservationPackage",
    "sp_ConfirmReservation", "sp_CancelReservation", "sp_CheckIn", "sp_CheckOut",
    "sp_ProcessPayment", "sp_RegisterWorkshop",
]
EXPECTED_VIEWS = ["vw_ReservationDetail"]


def explain_error(exc: Exception) -> str:
    """Gợi ý cách sửa cho các lỗi kết nối hay gặp."""
    text = str(exc)
    low = text.lower()
    if "im002" in low or "data source name not found" in low:
        return "Chưa cài 'ODBC Driver 17 for SQL Server' trên máy này."
    if "28000" in low or "login failed" in low:
        return "Sai DB_USER hoặc DB_PASSWORD trong file .env."
    if "4060" in low or "cannot open database" in low:
        return "Database chưa tồn tại: chạy database/01_create_tables.sql trước."
    if "08001" in low or "hyt00" in low or "could not open a connection" in low or "timeout" in low:
        return ("Không tới được SQL Server: kiểm tra DB_SERVER, SQL Server đã bật chưa, "
                "cổng 1433 và firewall.")
    return ""


def fetch_names(cur, sql: str) -> set:
    """Chạy câu SELECT trả về cột tên, trả về tập tên viết thường (so sánh không phân biệt hoa thường)."""
    cur.execute(sql)
    return {str(row[0]).lower() for row in cur.fetchall()}


def approx_rows(cur, table: str):
    """Số dòng ước lượng từ thống kê của SQL Server (nhanh, không quét cả bảng lớn).

    Trả về None nếu tài khoản không đủ quyền xem thống kê.
    """
    try:
        cur.execute(
            "SELECT SUM(row_count) FROM sys.dm_db_partition_stats "
            "WHERE object_id = OBJECT_ID(?) AND index_id IN (0, 1)",
            f"dbo.{table}",
        )
        value = cur.fetchone()[0]
        return int(value) if value is not None else 0
    except pyodbc.Error:
        return None


def report_group(title: str, expected: list, existing: set) -> list:
    """In trạng thái từng mục của một nhóm và trả về danh sách mục còn thiếu."""
    print(f"\n{title}")
    missing = []
    for name in expected:
        if name.lower() in existing:
            print(f"  [OK]    {name}")
        else:
            print(f"  [THIEU] {name}")
            missing.append(name)
    return missing


def main() -> int:
    print("=== KIỂM TRA DATABASE ===")
    print(f"Server  : {DB_SERVER}")
    print(f"Database: {DB_NAME}")
    print(f"User    : {DB_USER}")

    # --- 1. Kết nối ---
    try:
        conn = get_db_connection()
    except Exception as exc:  # database.py in lỗi gốc rồi ném lại; ở đây thêm gợi ý
        print("\n[LOI] Không kết nối được SQL Server.")
        hint = explain_error(exc)
        if hint:
            print("Gợi ý:", hint)
        return 1

    try:
        cur = conn.cursor()

        # --- 2. Thông tin server ---
        cur.execute("SELECT DB_NAME(), @@VERSION")
        db_name, version = cur.fetchone()
        print(f"\n[OK] Kết nối thành công, đang dùng database: {db_name}")
        print("     " + str(version).splitlines()[0])

        # --- 3. Bảng ---
        tables = fetch_names(cur, "SELECT name FROM sys.tables WHERE schema_id = SCHEMA_ID('dbo')")
        missing_tables = report_group("Bảng (dbo):", EXPECTED_TABLES, tables)

        print("\nSố dòng ước lượng:")
        users_rows = None
        for name in EXPECTED_TABLES:
            if name.lower() not in tables:
                continue
            rows = approx_rows(cur, name)
            label = "không đủ quyền xem" if rows is None else f"~{rows:,} dòng"
            print(f"  {name:<26} {label}")
            if name == "Users":
                users_rows = rows

        # --- 4. Stored procedure và view ---
        procs = fetch_names(cur, "SELECT name FROM sys.procedures WHERE schema_id = SCHEMA_ID('dbo')")
        missing_procs = report_group("Stored procedure:", EXPECTED_PROCEDURES, procs)

        views = fetch_names(cur, "SELECT name FROM sys.views WHERE schema_id = SCHEMA_ID('dbo')")
        missing_views = report_group("View:", EXPECTED_VIEWS, views)
    except pyodbc.Error as exc:
        print(f"\n[LOI] Lỗi khi truy vấn database: {exc}")
        return 1
    finally:
        conn.close()

    # --- Tổng kết ---
    print("\n=== KẾT QUẢ ===")
    problems = missing_tables or missing_procs or missing_views
    if problems:
        print("[THIEU] Database chưa đủ đối tượng mà backend cần.")
        print("Gợi ý: chạy lần lượt trong thư mục database/: 01_create_tables.sql -> "
              "02_seed_data.sql -> 03_stored_procedures.sql")
        return 1
    if users_rows == 0:
        print("[CANH BAO] Bảng Users đang trống: chưa có dữ liệu mẫu, chạy 02_seed_data.sql.")
    print("[OK] Database sẵn sàng cho backend.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
