"""Kiểm tra kết nối và các đối tượng database. Chạy trong thư mục backend: python scripts/check_db.py"""
import os
import sys

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

from dotenv import load_dotenv  # noqa: E402

load_dotenv(os.path.join(BACKEND_DIR, ".env"))  # nạp .env trước khi import database

from database import DB_NAME, DB_SERVER, get_db_connection  # noqa: E402

# Các đối tượng mà backend cần (tạo bởi database/01 và 03)
EXPECTED = {
    "Bảng": ("sys.tables", [
        "Users", "Studios", "Rooms", "Equipment", "EquipmentMaintenance", "ServicePackages",
        "PackageEquipment", "Reservations", "ReservationEquipments", "ReservationPackages",
        "ServiceSessions", "ReservationStatusHistory", "Payments", "Reviews",
        "Workshops", "WorkshopRegistrations"]),
    "Stored procedure": ("sys.procedures", [
        "sp_CreateReservation", "sp_AddReservationEquipment", "sp_AddReservationPackage",
        "sp_ConfirmReservation", "sp_CancelReservation", "sp_CheckIn", "sp_CheckOut",
        "sp_ProcessPayment", "sp_RegisterWorkshop"]),
    "View": ("sys.views", ["vw_ReservationDetail"]),
}


def main() -> int:
    print(f"Kiểm tra {DB_NAME} trên {DB_SERVER} ...")
    try:
        conn = get_db_connection()
    except Exception as exc:
        low = str(exc).lower()
        hint = ("Chưa cài ODBC Driver 17" if "im002" in low or "data source name" in low
                else "Sai DB_USER/DB_PASSWORD trong .env" if "28000" in low or "login failed" in low
                else "Chưa có database, chạy database/01_create_tables.sql" if "4060" in low
                else "Kiểm tra DB_SERVER, SQL Server đã bật chưa, cổng 1433")
        print("[LOI] Không kết nối được.", hint)
        return 1

    missing = []
    try:
        cur = conn.cursor()
        for title, (catalog, names) in EXPECTED.items():
            cur.execute(f"SELECT name FROM {catalog} WHERE schema_id = SCHEMA_ID('dbo')")
            found = {row[0].lower() for row in cur.fetchall()}
            lost = [n for n in names if n.lower() not in found]
            print(f"{title}: {len(names) - len(lost)}/{len(names)}", "OK" if not lost else f"THIEU {lost}")
            missing += lost
    finally:
        conn.close()

    if missing:
        print("[THIEU] Chạy lần lượt database/01, 02, 03 rồi kiểm tra lại.")
        return 1
    print("[OK] Database sẵn sàng cho backend.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
