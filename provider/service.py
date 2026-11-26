"""Nghiệp vụ cho Provider (chủ studio).

- PROVIDER chỉ thấy/sửa dữ liệu thuộc studio của mình, ADMIN thấy tất cả.
- Đổi trạng thái đơn, thanh toán, thêm thiết bị/gói đều gọi stored procedure trong
  03_stored_procedures.sql (quy tắc nghiệp vụ nằm ở SQL, Python chỉ chuyển lỗi thành HTTP).
"""
import re
from contextlib import contextmanager
from datetime import date, datetime, time
from decimal import Decimal
from typing import Any, Dict, Iterable, List, Optional, Tuple

import pyodbc
from fastapi import HTTPException, status

from core.db_errors import extract_message
from core.security import hash_password, verify_password
from database import get_db_connection

TIME_RE = re.compile(r"^\d{2}:\d{2}(:\d{2})?$")


# ----------------------------------------------------------------- tiện ích
def _py(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, time):
        return value.strftime("%H:%M")
    return value


def _rows(cur) -> List[dict]:
    cols = [c[0] for c in cur.description]
    return [{c: _py(v) for c, v in zip(cols, row)} for row in cur.fetchall()]


def _one(cur) -> Optional[dict]:
    rows = _rows(cur)
    return rows[0] if rows else None


def _drain(cur) -> None:
    """Đọc hết kết quả của stored procedure để lỗi THROW được ném ra."""
    try:
        while cur.nextset():
            pass
    except pyodbc.ProgrammingError:
        pass


def _http_from_sql(exc: Exception) -> HTTPException:
    msg = extract_message(exc)
    low = msg.lower()
    if "không tìm thấy" in low or "không hợp lệ" in low:
        code = status.HTTP_404_NOT_FOUND
    elif "không có quyền" in low or "chỉ chủ studio" in low or "chỉ nhân viên" in low:
        code = status.HTTP_403_FORBIDDEN
    elif "constraint" in low or "conflicted" in low or "duplicate" in low or "truncat" in low:
        code, msg = status.HTTP_400_BAD_REQUEST, "Dữ liệu không hợp lệ: " + msg
    else:
        code = status.HTTP_409_CONFLICT
    return HTTPException(status_code=code, detail=msg)


@contextmanager
def _db():
    """Mở kết nối, tự commit khi xong, rollback + đổi lỗi SQL thành HTTPException."""
    conn = get_db_connection()
    try:
        yield conn.cursor()
        conn.commit()
    except pyodbc.Error as exc:
        conn.rollback()
        raise _http_from_sql(exc) from exc
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _is_admin(user: dict) -> bool:
    return str(user.get("role", "")).upper() == "ADMIN"


def _scope(user: dict, column: str) -> Tuple[str, list]:
    if _is_admin(user):
        return "", []
    return f" AND {column} = ?", [user["user_id"]]


def _err(code: int, detail: str) -> HTTPException:
    return HTTPException(status_code=code, detail=detail)


def _time(value: Optional[str], label: str) -> Optional[str]:
    if value is None:
        return None
    if not TIME_RE.match(value):
        raise _err(400, f"{label} phải có dạng HH:MM")
    return value


def _provider_of_studio(cur, studio_id: int) -> int:
    cur.execute("SELECT provider_id FROM dbo.Studios WHERE studio_id = ?", studio_id)
    row = cur.fetchone()
    if row is None:
        raise _err(404, "Không tìm thấy studio")
    return row.provider_id


def _assert_studio(cur, user: dict, studio_id: int) -> None:
    if not _is_admin(user) and _provider_of_studio(cur, studio_id) != user["user_id"]:
        raise _err(403, "Bạn không có quyền với studio này")


def _dump(model, nullable: Iterable[str]) -> Dict[str, Any]:
    """Các trường client gửi lên; bỏ giá trị null ở cột NOT NULL."""
    nullable = set(nullable)
    data = model.model_dump(exclude_unset=True)
    return {k: v for k, v in data.items() if v is not None or k in nullable}


def _update(cur, table: str, key: str, key_value: int, data: Dict[str, Any]) -> None:
    if not data:
        raise _err(400, "Không có trường nào để cập nhật")
    sets = ", ".join(f"{col} = ?" for col in data)  # tên cột lấy từ schema, không từ người dùng
    cur.execute(f"UPDATE dbo.{table} SET {sets} WHERE {key} = ?", *data.values(), key_value)


def _new_id(cur) -> int:
    cur.execute("SELECT CAST(SCOPE_IDENTITY() AS INT)")
    return cur.fetchone()[0]


# ------------------------------------------------------------------ studios
STUDIO_SELECT = """
SELECT s.studio_id, s.provider_id, s.name, s.address, s.city, s.latitude, s.longitude,
       s.description, s.phone, s.open_time, s.close_time, s.status, s.created_at,
       (SELECT COUNT(*) FROM dbo.Rooms r WHERE r.studio_id = s.studio_id) AS room_count,
       (SELECT COUNT(*) FROM dbo.Reviews rv WHERE rv.studio_id = s.studio_id) AS review_count,
       (SELECT CAST(AVG(CAST(rv.rating AS DECIMAL(4,2))) AS DECIMAL(3,2))
          FROM dbo.Reviews rv WHERE rv.studio_id = s.studio_id) AS avg_rating
FROM dbo.Studios s WHERE 1 = 1"""


def _studio(cur, studio_id: int) -> dict:
    cur.execute(STUDIO_SELECT + " AND s.studio_id = ?", studio_id)
    row = _one(cur)
    if row is None:
        raise _err(404, "Không tìm thấy studio")
    return row


def list_studios(user: dict) -> List[dict]:
    with _db() as cur:
        clause, params = _scope(user, "s.provider_id")
        cur.execute(STUDIO_SELECT + clause + " ORDER BY s.studio_id", *params)
        return _rows(cur)


def create_studio(user: dict, data) -> dict:
    open_t = _time(data.open_time, "Giờ mở cửa") or "08:00"
    close_t = _time(data.close_time, "Giờ đóng cửa") or "21:00"
    if close_t <= open_t:
        raise _err(400, "Giờ đóng cửa phải sau giờ mở cửa")
    state = "APPROVED" if _is_admin(user) else "PENDING"
    with _db() as cur:
        if not _is_admin(user):
            cur.execute("SELECT status FROM dbo.Users WHERE user_id = ?", user["user_id"])
            row = cur.fetchone()
            if row is None or str(row.status).upper() != "ACTIVE":
                raise _err(403, "Tài khoản nhà cung cấp chưa được quản trị viên duyệt, chưa thể tạo cơ sở.")
        cur.execute(
            "INSERT INTO dbo.Studios (provider_id, name, address, city, description, phone, "
            "open_time, close_time, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            user["user_id"], data.name, data.address, data.city, data.description, data.phone,
            open_t, close_t, state)
        return _studio(cur, _new_id(cur))


def update_studio(user: dict, studio_id: int, data) -> dict:
    fields = _dump(data, {"description", "phone"})
    for key in ("open_time", "close_time"):
        if key in fields:
            fields[key] = _time(fields[key], key)
    with _db() as cur:
        _assert_studio(cur, user, studio_id)
        current = _studio(cur, studio_id)
        open_t = fields.get("open_time") or current["open_time"]
        close_t = fields.get("close_time") or current["close_time"]
        if close_t[:5] <= open_t[:5]:
            raise _err(400, "Giờ đóng cửa phải sau giờ mở cửa")
        _update(cur, "Studios", "studio_id", studio_id, fields)
        return _studio(cur, studio_id)


def delete_studio(user: dict, studio_id: int) -> None:
    """Xóa hẳn cơ sở cùng phòng / thiết bị / gói dịch vụ của nó.

    Chỉ cho xóa khi cơ sở CHƯA có đơn đặt phòng hay workshop nào (các bảng đó giữ khóa ngoại và là
    dữ liệu lịch sử / doanh thu). Nếu đã có, trả 409 để người dùng chuyển sang ẩn phòng.
    """
    with _db() as cur:
        _assert_studio(cur, user, studio_id)
        cur.execute(
            "SELECT COUNT(*) FROM dbo.Reservations rs JOIN dbo.Rooms r ON r.room_id = rs.room_id "
            "WHERE r.studio_id = ?", studio_id)
        if cur.fetchone()[0]:
            raise _err(409, "Cơ sở đã có đơn đặt phòng nên không thể xóa. "
                            "Hãy ẩn các phòng của cơ sở này thay vì xóa.")
        cur.execute("SELECT COUNT(*) FROM dbo.Workshops WHERE studio_id = ?", studio_id)
        if cur.fetchone()[0]:
            raise _err(409, "Cơ sở đang có workshop nên không thể xóa.")
        # PackageEquipment / EquipmentMaintenance / StudioImages tự xóa theo (ON DELETE CASCADE)
        # PricingRules / Promotions chỉ có sau khi chạy 07_pricing_promotions_ai.sql nên xóa có điều kiện
        for table in ("PricingRules", "Promotions"):
            cur.execute(f"IF OBJECT_ID('dbo.{table}', 'U') IS NOT NULL "
                        f"DELETE FROM dbo.{table} WHERE studio_id = ?", studio_id)
        cur.execute("DELETE FROM dbo.ServicePackages WHERE studio_id = ?", studio_id)
        cur.execute("DELETE FROM dbo.Equipment WHERE studio_id = ?", studio_id)
        cur.execute("DELETE FROM dbo.Rooms WHERE studio_id = ?", studio_id)
        cur.execute("DELETE FROM dbo.Studios WHERE studio_id = ?", studio_id)


# -------------------------------------------------------------------- rooms
ROOM_SELECT = """
SELECT r.room_id, r.studio_id, s.name AS studio_name, s.city, s.address, r.name, r.room_type,
       r.capacity, r.area_sqm, r.art_style, r.lighting, r.ventilation, r.acoustics, r.usage_policy,
       r.amenities, r.price_per_hour,
       r.description, r.status, r.created_at
FROM dbo.Rooms r JOIN dbo.Studios s ON s.studio_id = r.studio_id WHERE 1 = 1"""
ROOM_NULLABLE = {"area_sqm", "art_style", "lighting", "amenities", "description", "ventilation", "acoustics",
                 "usage_policy"}


def _room(cur, room_id: int) -> dict:
    cur.execute(ROOM_SELECT + " AND r.room_id = ?", room_id)
    row = _one(cur)
    if row is None:
        raise _err(404, "Không tìm thấy phòng")
    return row


def list_rooms(user: dict, studio_id: Optional[int]) -> List[dict]:
    with _db() as cur:
        clause, params = _scope(user, "s.provider_id")
        if studio_id:
            clause += " AND r.studio_id = ?"
            params.append(studio_id)
        cur.execute(ROOM_SELECT + clause + " ORDER BY r.studio_id, r.room_id", *params)
        return _rows(cur)


def create_room(user: dict, data) -> dict:
    with _db() as cur:
        _assert_studio(cur, user, data.studio_id)
        cur.execute(
            "INSERT INTO dbo.Rooms (studio_id, name, room_type, capacity, area_sqm, art_style, "
            "lighting, amenities, price_per_hour, description, status, ventilation, acoustics, usage_policy) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            data.studio_id, data.name, data.room_type, data.capacity, data.area_sqm, data.art_style,
            data.lighting, data.amenities, Decimal(str(data.price_per_hour)), data.description,
            data.status, data.ventilation, data.acoustics, data.usage_policy)
        return _room(cur, _new_id(cur))


def update_room(user: dict, room_id: int, data) -> dict:
    fields = _dump(data, ROOM_NULLABLE)
    if "price_per_hour" in fields:
        fields["price_per_hour"] = Decimal(str(fields["price_per_hour"]))
    with _db() as cur:
        _assert_studio(cur, user, _room(cur, room_id)["studio_id"])
        _update(cur, "Rooms", "room_id", room_id, fields)
        return _room(cur, room_id)


# ---------------------------------------------------------------- equipment
EQUIPMENT_SELECT = """
SELECT e.equipment_id, e.studio_id, s.name AS studio_name, e.name, e.equipment_type, e.category,
       e.quantity, e.rental_price, e.next_maintenance_date, e.status
FROM dbo.Equipment e JOIN dbo.Studios s ON s.studio_id = e.studio_id WHERE 1 = 1"""


def _equipment(cur, equipment_id: int) -> dict:
    cur.execute(EQUIPMENT_SELECT + " AND e.equipment_id = ?", equipment_id)
    row = _one(cur)
    if row is None:
        raise _err(404, "Không tìm thấy thiết bị")
    return row


def list_equipment(user: dict, studio_id: Optional[int]) -> List[dict]:
    with _db() as cur:
        clause, params = _scope(user, "s.provider_id")
        if studio_id:
            clause += " AND e.studio_id = ?"
            params.append(studio_id)
        cur.execute(EQUIPMENT_SELECT + clause + " ORDER BY e.studio_id, e.equipment_id", *params)
        return _rows(cur)


def create_equipment(user: dict, data) -> dict:
    with _db() as cur:
        _assert_studio(cur, user, data.studio_id)
        cur.execute(
            "INSERT INTO dbo.Equipment (studio_id, name, equipment_type, category, quantity, "
            "rental_price, next_maintenance_date, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            data.studio_id, data.name, data.equipment_type, data.category, data.quantity,
            Decimal(str(data.rental_price)), data.next_maintenance_date, data.status)
        return _equipment(cur, _new_id(cur))


def update_equipment(user: dict, equipment_id: int, data) -> dict:
    fields = _dump(data, {"next_maintenance_date"})
    if "rental_price" in fields:
        fields["rental_price"] = Decimal(str(fields["rental_price"]))
    with _db() as cur:
        _assert_studio(cur, user, _equipment(cur, equipment_id)["studio_id"])
        _update(cur, "Equipment", "equipment_id", equipment_id, fields)
        return _equipment(cur, equipment_id)


def retire_equipment(user: dict, equipment_id: int) -> None:
    with _db() as cur:
        _assert_studio(cur, user, _equipment(cur, equipment_id)["studio_id"])
        cur.execute("UPDATE dbo.Equipment SET status = 'RETIRED' WHERE equipment_id = ?", equipment_id)


def add_maintenance(user: dict, equipment_id: int, data) -> dict:
    with _db() as cur:
        _assert_studio(cur, user, _equipment(cur, equipment_id)["studio_id"])
        cur.execute(
            "INSERT INTO dbo.EquipmentMaintenance (equipment_id, cost, description, status) "
            "VALUES (?, ?, ?, ?)", equipment_id, Decimal(str(data.cost)), data.description, data.status)
        maintenance_id = _new_id(cur)
        if data.next_maintenance_date is not None:
            cur.execute("UPDATE dbo.Equipment SET next_maintenance_date = ? WHERE equipment_id = ?",
                        data.next_maintenance_date, equipment_id)
        if data.status == "DONE":   # bảo trì xong: thiết bị dùng lại được (trừ khi đã thanh lý)
            cur.execute("UPDATE dbo.Equipment SET status = 'GOOD' WHERE equipment_id = ? "
                        "AND status IN ('NEEDS_MAINTENANCE','UNDER_MAINTENANCE','BROKEN')", equipment_id)
        cur.execute("SELECT maintenance_id, equipment_id, maintenance_date, cost, description, status "
                    "FROM dbo.EquipmentMaintenance WHERE maintenance_id = ?", maintenance_id)
        return _one(cur)


# ----------------------------------------------------------------- packages
def list_packages(user: dict, studio_id: Optional[int]) -> List[dict]:
    with _db() as cur:
        clause, params = _scope(user, "s.provider_id")
        if studio_id:
            clause += " AND sp.studio_id = ?"
            params.append(studio_id)
        cur.execute(
            "SELECT sp.package_id, sp.studio_id, s.name AS studio_name, sp.name, sp.price, "
            "sp.duration_hours, sp.room_type, sp.instructor_id, u.full_name AS instructor_name, "
            "sp.description, sp.is_active "
            "FROM dbo.ServicePackages sp JOIN dbo.Studios s ON s.studio_id = sp.studio_id "
            "LEFT JOIN dbo.Users u ON u.user_id = sp.instructor_id WHERE 1 = 1" + clause +
            " ORDER BY sp.studio_id, sp.package_id", *params)
        packages = _rows(cur)
        for p in packages:
            p["is_active"] = bool(p["is_active"])
            p["equipment"] = []
        index = {p["package_id"]: p for p in packages}
        if index:
            cur.execute(
                "SELECT pe.package_id, pe.equipment_id, e.name, pe.quantity_included "
                "FROM dbo.PackageEquipment pe JOIN dbo.Equipment e ON e.equipment_id = pe.equipment_id "
                "JOIN dbo.ServicePackages sp ON sp.package_id = pe.package_id "
                "JOIN dbo.Studios s ON s.studio_id = sp.studio_id WHERE 1 = 1" + clause, *params)
            for row in _rows(cur):
                if row["package_id"] in index:
                    index[row["package_id"]]["equipment"].append(
                        {"equipment_id": row["equipment_id"], "name": row["name"],
                         "quantity_included": row["quantity_included"]})
        return packages


# ------------------------------------------------------------------ reviews
def list_reviews(user: dict, studio_id: Optional[int], limit: int, offset: int) -> List[dict]:
    with _db() as cur:
        clause, params = _scope(user, "s.provider_id")
        if studio_id:
            clause += " AND rv.studio_id = ?"
            params.append(studio_id)
        cur.execute(
            "SELECT rv.review_id, rv.reservation_id, rv.studio_id, s.name AS studio_name, "
            "rv.customer_id, u.full_name AS customer_name, rv.rating, rv.comment, rv.created_at "
            "FROM dbo.Reviews rv JOIN dbo.Studios s ON s.studio_id = rv.studio_id "
            "JOIN dbo.Users u ON u.user_id = rv.customer_id WHERE 1 = 1" + clause +
            " ORDER BY rv.created_at DESC, rv.review_id DESC OFFSET ? ROWS FETCH NEXT ? ROWS ONLY",
            *params, offset, limit)
        return _rows(cur)


# --------------------------------------------------------------- disputes
DISPUTE_SELECT = (
    "SELECT d.dispute_id, d.reservation_id, d.raised_by, u.full_name AS raised_by_name, d.reason, d.status, "
    "d.resolution, d.created_at, d.resolved_at, rm.name AS room_name, s.studio_id, s.name AS studio_name "
    "FROM dbo.Disputes d JOIN dbo.Reservations r ON r.reservation_id = d.reservation_id "
    "JOIN dbo.Rooms rm ON rm.room_id = r.room_id JOIN dbo.Studios s ON s.studio_id = rm.studio_id "
    "JOIN dbo.Users u ON u.user_id = d.raised_by WHERE 1 = 1")


def list_disputes(user: dict, status_filter: Optional[str], limit: int, offset: int) -> List[dict]:
    with _db() as cur:
        clause, params = _scope(user, "s.provider_id")
        if status_filter:
            clause += " AND d.status = ?"
            params.append(status_filter)
        cur.execute(DISPUTE_SELECT + clause + " ORDER BY d.created_at DESC, d.dispute_id DESC "
                    "OFFSET ? ROWS FETCH NEXT ? ROWS ONLY", *params, offset, limit)
        return _rows(cur)


def update_dispute(user: dict, dispute_id: int, data) -> dict:
    """Provider tiếp nhận (IN_REVIEW) hoặc phản hồi/giải quyết (RESOLVED); từ chối (REJECTED) chỉ admin."""
    with _db() as cur:
        cur.execute("SELECT d.status, s.provider_id FROM dbo.Disputes d "
                    "JOIN dbo.Reservations r ON r.reservation_id = d.reservation_id "
                    "JOIN dbo.Rooms rm ON rm.room_id = r.room_id JOIN dbo.Studios s ON s.studio_id = rm.studio_id "
                    "WHERE d.dispute_id = ?", dispute_id)
        row = cur.fetchone()
        if row is None:
            raise _err(404, "Không tìm thấy khiếu nại")
        if not _is_admin(user) and row.provider_id != user["user_id"]:
            raise _err(403, "Khiếu nại này không thuộc studio của bạn")
        if row.status in ("RESOLVED", "REJECTED"):
            raise _err(409, "Khiếu nại đã được xử lý xong, không thể thay đổi.")
        if data.status == "REJECTED" and not _is_admin(user):
            raise _err(403, "Chỉ admin mới được bác bỏ khiếu nại.")
        resolution = (data.resolution or "").strip() or None
        if data.status in ("RESOLVED", "REJECTED"):
            if not resolution or len(resolution) < 3:
                raise _err(400, "Cần nhập nội dung phản hồi / hướng giải quyết.")
            cur.execute("UPDATE dbo.Disputes SET status = ?, resolution = ?, resolved_by = ?, "
                        "resolved_at = GETDATE() WHERE dispute_id = ?",
                        data.status, resolution, user["user_id"], dispute_id)
        else:
            cur.execute("UPDATE dbo.Disputes SET status = ? WHERE dispute_id = ?", data.status, dispute_id)
        cur.execute(DISPUTE_SELECT + " AND d.dispute_id = ?", dispute_id)
        return _one(cur)


# -------------------------------------------------------------- workshops
def list_workshops(user: dict, status_filter: Optional[str], limit: int, offset: int) -> List[dict]:
    """Workshop do chuyên gia tổ chức tại các cơ sở của provider (chỉ xem)."""
    with _db() as cur:
        clause, params = _scope(user, "s.provider_id")
        if status_filter:
            clause += " AND w.status = ?"
            params.append(status_filter)
        cur.execute(
            "SELECT w.workshop_id, w.title, w.description, w.expert_id, e.full_name AS expert_name, "
            "w.studio_id, s.name AS studio_name, w.capacity, "
            "(SELECT COUNT(*) FROM dbo.WorkshopRegistrations wr WHERE wr.workshop_id = w.workshop_id) AS registered, "
            "w.fee, w.start_time, w.end_time, w.status "
            "FROM dbo.Workshops w JOIN dbo.Studios s ON s.studio_id = w.studio_id "
            "JOIN dbo.Users e ON e.user_id = w.expert_id WHERE 1 = 1" + clause +
            " ORDER BY w.start_time DESC, w.workshop_id DESC OFFSET ? ROWS FETCH NEXT ? ROWS ONLY",
            *params, offset, limit)
        return _rows(cur)


# ----------------------------------------------------------------- bookings
BOOKING_SELECT = """
SELECT v.reservation_id, v.status, v.start_time, v.end_time, v.customer_id, v.customer,
       u.full_name AS customer_name, v.room_id, v.room_name, v.studio_id, v.studio_name,
       v.total_amount, v.paid_amount, v.balance_due, r.qr_code, r.customer_note, v.provider_id
FROM dbo.vw_ReservationDetail v
JOIN dbo.Reservations r ON r.reservation_id = v.reservation_id
JOIN dbo.Users u ON u.user_id = v.customer_id WHERE 1 = 1"""


def list_bookings(user: dict, status_: Optional[str], studio_id: Optional[int],
                  room_id: Optional[int], limit: int, offset: int) -> List[dict]:
    with _db() as cur:
        clause, params = _scope(user, "v.provider_id")
        for column, value in (("v.status", status_), ("v.studio_id", studio_id), ("v.room_id", room_id)):
            if value:
                clause += f" AND {column} = ?"
                params.append(value)
        cur.execute(BOOKING_SELECT + clause +
                    " ORDER BY v.start_time DESC, v.reservation_id DESC OFFSET ? ROWS FETCH NEXT ? ROWS ONLY",
                    *params, offset, limit)
        rows = _rows(cur)
        for row in rows:
            row.pop("provider_id", None)
        return rows


def _booking_detail(cur, user: dict, reservation_id: int) -> dict:
    cur.execute(BOOKING_SELECT + " AND v.reservation_id = ?", reservation_id)
    booking = _one(cur)
    if booking is None:
        raise _err(404, "Không tìm thấy đơn đặt phòng")
    if not _is_admin(user) and booking.pop("provider_id") != user["user_id"]:
        raise _err(403, "Đơn này không thuộc studio của bạn")
    booking.pop("provider_id", None)

    cur.execute("SELECT re.equipment_id, e.name, re.quantity, re.unit_price "
                "FROM dbo.ReservationEquipments re JOIN dbo.Equipment e ON e.equipment_id = re.equipment_id "
                "WHERE re.reservation_id = ?", reservation_id)
    booking["equipment"] = _rows(cur)
    cur.execute("SELECT rp.package_id, sp.name, rp.price, rp.notes "
                "FROM dbo.ReservationPackages rp JOIN dbo.ServicePackages sp ON sp.package_id = rp.package_id "
                "WHERE rp.reservation_id = ?", reservation_id)
    booking["packages"] = _rows(cur)
    cur.execute("SELECT payment_id, amount, payment_method, transaction_code, status, paid_at, created_at "
                "FROM dbo.Payments WHERE reservation_id = ? ORDER BY payment_id", reservation_id)
    booking["payments"] = _rows(cur)
    cur.execute("SELECT h.old_status, h.new_status, h.changed_at, "
                "COALESCE(u.full_name, N'Hệ thống') AS changed_by_name "
                "FROM dbo.ReservationStatusHistory h LEFT JOIN dbo.Users u ON u.user_id = h.changed_by "
                "WHERE h.reservation_id = ? ORDER BY h.history_id", reservation_id)
    booking["history"] = _rows(cur)
    cur.execute("SELECT checkin_time, checkout_time, actual_minutes FROM dbo.ServiceSessions "
                "WHERE reservation_id = ?", reservation_id)
    booking["session"] = _one(cur)
    booking["cancel_reason"] = _cancel_reason(cur, reservation_id) if booking["status"] == "CANCELLED" else None
    return booking


def _cancel_reason(cur, reservation_id: int) -> Optional[str]:
    """Cột cancel_reason do database/06_provider_additions.sql thêm; chưa chạy script đó thì trả None."""
    try:
        cur.execute("SELECT cancel_reason FROM dbo.Reservations WHERE reservation_id = ?", reservation_id)
        row = cur.fetchone()
        return row[0] if row else None
    except pyodbc.Error:
        return None


def get_booking(user: dict, reservation_id: int) -> dict:
    with _db() as cur:
        return _booking_detail(cur, user, reservation_id)


def _run(user: dict, reservation_id: int, sql: str, *params) -> dict:
    """Kiểm tra quyền → gọi stored procedure → trả chi tiết đơn sau khi đổi."""
    with _db() as cur:
        _booking_detail(cur, user, reservation_id)          # 404 / 403 sớm
        cur.execute(sql, *params)
        _drain(cur)
        return _booking_detail(cur, user, reservation_id)


def confirm(user: dict, reservation_id: int) -> dict:
    return _run(user, reservation_id, "EXEC dbo.sp_ConfirmReservation @reservation_id = ?, @actor_id = ?",
                reservation_id, user["user_id"])


def cancel(user: dict, reservation_id: int, reason: Optional[str] = None) -> dict:
    """Hủy đơn; nếu có lý do thì lưu vào Reservations.cancel_reason (khách thấy lý do bị hủy)."""
    reason = (reason or "").strip() or None
    with _db() as cur:
        _booking_detail(cur, user, reservation_id)          # 404 / 403 sớm
        cur.execute("EXEC dbo.sp_CancelReservation @reservation_id = ?, @actor_id = ?",
                    reservation_id, user["user_id"])
        _drain(cur)
        saved = False
        if reason:
            try:
                cur.execute("UPDATE dbo.Reservations SET cancel_reason = ? "
                            "WHERE reservation_id = ? AND status = 'CANCELLED'", reason, reservation_id)
                saved = True
            except pyodbc.Error:
                saved = False                               # chưa chạy 06_provider_additions.sql
        booking = _booking_detail(cur, user, reservation_id)
        if reason:
            booking["cancel_reason"] = reason if saved else None
            booking["reason_saved"] = saved
        return booking


def checkout(user: dict, reservation_id: int) -> dict:
    return _run(user, reservation_id, "EXEC dbo.sp_CheckOut @reservation_id = ?, @actor_id = ?",
                reservation_id, user["user_id"])


def check_in(user: dict, qr_code: str) -> dict:
    with _db() as cur:
        cur.execute("SELECT reservation_id FROM dbo.Reservations WHERE qr_code = ?", qr_code)
        row = cur.fetchone()
        if row is None:
            raise _err(404, "Mã QR không hợp lệ.")
        _booking_detail(cur, user, row.reservation_id)      # chặn quét QR của studio khác
        cur.execute("EXEC dbo.sp_CheckIn @qr_code = ?, @actor_id = ?", qr_code, user["user_id"])
        _drain(cur)
        return _booking_detail(cur, user, row.reservation_id)


def pay(user: dict, reservation_id: int, data) -> dict:
    return _run(user, reservation_id,
                "EXEC dbo.sp_ProcessPayment @reservation_id = ?, @amount = ?, @payment_method = ?, "
                "@actor_id = ?, @transaction_code = ?",
                reservation_id, Decimal(str(data.amount)), data.payment_method, user["user_id"],
                data.transaction_code)


def add_equipment(user: dict, reservation_id: int, data) -> dict:
    return _run(user, reservation_id,
                "EXEC dbo.sp_AddReservationEquipment @reservation_id = ?, @equipment_id = ?, "
                "@quantity = ?, @actor_id = ?",
                reservation_id, data.equipment_id, data.quantity, user["user_id"])


def add_package(user: dict, reservation_id: int, data) -> dict:
    return _run(user, reservation_id,
                "EXEC dbo.sp_AddReservationPackage @reservation_id = ?, @package_id = ?, "
                "@actor_id = ?, @notes = ?",
                reservation_id, data.package_id, user["user_id"], data.notes)


# ----------------------------------------------------------------- overview
def overview(user: dict) -> dict:
    with _db() as cur:
        s_clause, s_params = _scope(user, "s.provider_id")

        def scalar(sql: str, *extra):
            cur.execute(sql + s_clause, *extra, *s_params)
            return cur.fetchone()[0]

        pay_from = ("FROM dbo.Payments p JOIN dbo.Reservations r ON r.reservation_id = p.reservation_id "
                    "JOIN dbo.Rooms rm ON rm.room_id = r.room_id "
                    "JOIN dbo.Studios s ON s.studio_id = rm.studio_id WHERE p.status = 'SUCCESS'")
        res_from = ("FROM dbo.Reservations r JOIN dbo.Rooms rm ON rm.room_id = r.room_id "
                    "JOIN dbo.Studios s ON s.studio_id = rm.studio_id WHERE 1 = 1")
        paid_at = "COALESCE(p.paid_at, p.created_at)"

        data = {
            "studio_count": scalar("SELECT COUNT(*) FROM dbo.Studios s WHERE 1 = 1"),
            "room_count": scalar("SELECT COUNT(*) FROM dbo.Rooms rm JOIN dbo.Studios s "
                                 "ON s.studio_id = rm.studio_id WHERE 1 = 1"),
            "equipment_count": scalar("SELECT COUNT(*) FROM dbo.Equipment e JOIN dbo.Studios s "
                                      "ON s.studio_id = e.studio_id WHERE e.status <> 'RETIRED'"),
            "total_bookings": scalar("SELECT COUNT(*) " + res_from),
            "pending_bookings": scalar("SELECT COUNT(*) " + res_from + " AND r.status = 'PENDING'"),
            "upcoming_bookings": scalar("SELECT COUNT(*) " + res_from +
                                        " AND r.status IN ('PENDING','CONFIRMED') AND r.start_time >= GETDATE()"),
            "revenue_total": float(scalar("SELECT ISNULL(SUM(p.amount), 0) " + pay_from)),
            "revenue_this_month": float(scalar(
                f"SELECT ISNULL(SUM(p.amount), 0) {pay_from} AND YEAR({paid_at}) = YEAR(GETDATE()) "
                f"AND MONTH({paid_at}) = MONTH(GETDATE())")),
        }

        cur.execute("SELECT COUNT(*) AS n, AVG(CAST(rv.rating AS DECIMAL(4,2))) AS avg_rating "
                    "FROM dbo.Reviews rv JOIN dbo.Studios s ON s.studio_id = rv.studio_id WHERE 1 = 1"
                    + s_clause, *s_params)
        rating = cur.fetchone()
        data["review_count"] = rating.n
        data["avg_rating"] = round(float(rating.avg_rating), 2) if rating.avg_rating is not None else None

        cur.execute(
            f"SELECT CONVERT(CHAR(7), {paid_at}, 120) AS month, SUM(p.amount) AS revenue, "
            f"COUNT(DISTINCT p.reservation_id) AS bookings {pay_from} "
            f"AND {paid_at} >= DATEADD(MONTH, -5, DATEFROMPARTS(YEAR(GETDATE()), MONTH(GETDATE()), 1))"
            + s_clause + f" GROUP BY CONVERT(CHAR(7), {paid_at}, 120) ORDER BY month", *s_params)
        data["revenue_by_month"] = _rows(cur)

        cur.execute(
            "SELECT TOP 5 rm.room_id, rm.name AS room_name, s.name AS studio_name, "
            "COUNT(*) AS bookings, SUM(r.total_amount) AS revenue "
            + res_from + " AND r.status IN ('CONFIRMED','IN_USE','COMPLETED')" + s_clause +
            " GROUP BY rm.room_id, rm.name, s.name ORDER BY SUM(r.total_amount) DESC", *s_params)
        data["top_rooms"] = _rows(cur)
        return data


# ------------------------------------------------- hồ sơ cá nhân (/api/users)
def update_profile(user: dict, data) -> dict:
    fields = _dump(data, {"phone"})
    if "email" in fields:
        fields["email"] = fields["email"].lower()
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", fields["email"]):
            raise _err(400, "Email không hợp lệ")
    with _db() as cur:
        if "email" in fields:
            cur.execute("SELECT 1 FROM dbo.Users WHERE email = ? AND user_id <> ?", fields["email"], user["user_id"])
            if cur.fetchone():
                raise _err(409, "Email đã được sử dụng")
        _update(cur, "Users", "user_id", user["user_id"], fields)
        cur.execute("SELECT user_id, username, email, full_name, phone, role, status "
                    "FROM dbo.Users WHERE user_id = ?", user["user_id"])
        row = _one(cur)
        if row is None:
            raise _err(404, "Không tìm thấy người dùng")
        return row


def change_password(user: dict, current_password: str, new_password: str) -> None:
    with _db() as cur:
        cur.execute("SELECT password_hash FROM dbo.Users WHERE user_id = ?", user["user_id"])
        row = cur.fetchone()
        if row is None:
            raise _err(404, "Không tìm thấy người dùng")
        if not verify_password(current_password, row.password_hash):
            raise _err(400, "Mật khẩu hiện tại không đúng")
        cur.execute("UPDATE dbo.Users SET password_hash = ? WHERE user_id = ?",
                    hash_password(new_password), user["user_id"])
