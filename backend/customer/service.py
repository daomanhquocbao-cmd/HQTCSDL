"""Nghiệp vụ phía KHÁCH HÀNG (nhiếp ảnh gia).

Tìm / lọc / so sánh phòng, xem chi tiết phòng + thiết bị + gói, theo dõi đơn của mình, thuê thêm thiết bị,
chọn gói, thanh toán, gửi khiếu nại. Mọi quy tắc nghiệp vụ (tồn kho, trùng lịch, quyền, trả vượt tiền)
nằm trong stored procedure của SQL Server; file này chỉ gọi và định dạng lại kết quả.
"""
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import List, Optional

import pyodbc

from provider.service import _db, _drain, _err, _new_id, _one, _rows

SORTS = {
    "rating": "ISNULL(v.avg_rating, 0) DESC, rm.price_per_hour",
    "price_asc": "rm.price_per_hour ASC, rm.room_id",
    "price_desc": "rm.price_per_hour DESC, rm.room_id",
    "capacity": "rm.capacity DESC, rm.price_per_hour",
    "newest": "rm.created_at DESC, rm.room_id DESC",
}

ROOM_SELECT = (
    "SELECT rm.room_id, rm.name AS room_name, rm.room_type, rm.capacity, rm.area_sqm, rm.art_style, rm.lighting, rm.ventilation, rm.acoustics, rm.usage_policy, "
    "rm.amenities, rm.price_per_hour, rm.description, s.studio_id, s.name AS studio_name, s.address, s.city, "
    "s.latitude, s.longitude, s.phone AS studio_phone, s.open_time, s.close_time, "
    "ISNULL(v.avg_rating, 0) AS avg_rating, ISNULL(v.review_count, 0) AS review_count, "
    "(SELECT TOP 1 image_url FROM dbo.StudioImages i WHERE i.studio_id = s.studio_id "
    " ORDER BY i.is_primary DESC, i.image_id) AS image_url "
    "FROM dbo.Rooms rm JOIN dbo.Studios s ON s.studio_id = rm.studio_id "
    "LEFT JOIN dbo.vw_StudioRating v ON v.studio_id = s.studio_id "
    "WHERE rm.status = 'AVAILABLE' AND s.status = 'APPROVED'"
)


def _fix_room(row: dict) -> dict:
    row["avg_rating"] = float(row.get("avg_rating") or 0)
    return row


# ------------------------------------------------------------------ tìm phòng
def search_rooms(q: Optional[str], room_type: Optional[str], city: Optional[str], min_price: Optional[float],
                 max_price: Optional[float], capacity: Optional[int], sort: str, limit: int, offset: int,
                 start: Optional[datetime] = None, end: Optional[datetime] = None) -> List[dict]:
    """Tìm công khai: chỉ phòng AVAILABLE của studio đã được duyệt. Có start/end thì loại phòng trùng lịch."""
    sql, params = ROOM_SELECT, []
    if q:
        sql += (" AND (rm.name LIKE ? OR s.name LIKE ? OR s.address LIKE ? OR s.city LIKE ? "
                "OR rm.art_style LIKE ? OR rm.amenities LIKE ?)")
        params += [f"%{q}%"] * 6
    for clause, value in ((" AND rm.room_type = ?", room_type), (" AND s.city = ?", city),
                          (" AND rm.price_per_hour >= ?", min_price), (" AND rm.price_per_hour <= ?", max_price),
                          (" AND rm.capacity >= ?", capacity)):
        if value is not None and value != "":
            sql += clause
            params.append(value)
    if start and end:
        sql += (" AND NOT EXISTS (SELECT 1 FROM dbo.Reservations r WHERE r.room_id = rm.room_id "
                "AND r.status IN ('PENDING','CONFIRMED','IN_USE') AND r.start_time < ? AND r.end_time > ?)")
        params += [end, start]
    sql += " ORDER BY " + SORTS.get(sort, SORTS["rating"]) + " OFFSET ? ROWS FETCH NEXT ? ROWS ONLY"
    with _db() as cur:
        cur.execute(sql, *params, offset, limit)
        return [_fix_room(r) for r in _rows(cur)]


def list_cities() -> List[str]:
    with _db() as cur:
        cur.execute("SELECT DISTINCT city FROM dbo.Studios WHERE status = 'APPROVED' ORDER BY city")
        return [r[0] for r in cur.fetchall()]


def room_detail(room_id: int) -> dict:
    """Phòng + thiết bị cho thuê + gói dịch vụ + đánh giá gần đây của studio."""
    with _db() as cur:
        cur.execute(ROOM_SELECT + " AND rm.room_id = ?", room_id)
        room = _one(cur)
        if room is None:
            raise _err(404, "Không tìm thấy phòng (hoặc phòng đang tạm ngừng)")
        _fix_room(room)
        sid = room["studio_id"]
        cur.execute("SELECT equipment_id, name, equipment_type, category, rental_price, quantity "
                    "FROM dbo.Equipment WHERE studio_id = ? AND status IN ('GOOD','NEEDS_MAINTENANCE') "
                    "ORDER BY category, name", sid)
        room["equipment"] = _rows(cur)
        cur.execute("SELECT sp.package_id, sp.name, sp.price, sp.duration_hours, sp.room_type, sp.description, "
                    "u.full_name AS instructor_name FROM dbo.ServicePackages sp "
                    "LEFT JOIN dbo.Users u ON u.user_id = sp.instructor_id "
                    "WHERE sp.studio_id = ? AND sp.is_active = 1 "
                    "AND (sp.room_type IS NULL OR sp.room_type = ?) ORDER BY sp.price", sid, room["room_type"])
        room["packages"] = _rows(cur)
        cur.execute("SELECT TOP 5 rv.rating, rv.comment, rv.created_at, u.full_name AS customer_name "
                    "FROM dbo.Reviews rv JOIN dbo.Users u ON u.user_id = rv.customer_id "
                    "WHERE rv.studio_id = ? ORDER BY rv.created_at DESC, rv.review_id DESC", sid)
        room["reviews"] = _rows(cur)
        return room


def busy_slots(room_id: int, day: date) -> List[dict]:
    """Khung giờ đã có người đặt trong ngày (để khách chọn giờ trống)."""
    start, end = datetime.combine(day, datetime.min.time()), datetime.combine(day + timedelta(days=1),
                                                                               datetime.min.time())
    with _db() as cur:
        cur.execute("SELECT start_time, end_time, status FROM dbo.Reservations WHERE room_id = ? "
                    "AND status IN ('PENDING','CONFIRMED','IN_USE') AND start_time < ? AND end_time > ? "
                    "ORDER BY start_time", room_id, end, start)
        return _rows(cur)


# --------------------------------------------------------------- đơn của khách
BOOKING_SELECT = (
    "SELECT v.reservation_id, v.status, v.start_time, v.end_time, v.room_id, v.room_name, v.studio_id, "
    "v.studio_name, v.total_amount, v.paid_amount, v.balance_due, r.qr_code, r.customer_note, r.created_at, "
    "CASE WHEN EXISTS (SELECT 1 FROM dbo.Reviews rv WHERE rv.reservation_id = r.reservation_id) THEN 1 ELSE 0 END "
    "AS has_review "
    "FROM dbo.vw_ReservationDetail v JOIN dbo.Reservations r ON r.reservation_id = v.reservation_id "
    "WHERE v.customer_id = ?"
)


def list_bookings(user: dict, status_filter: Optional[str], limit: int, offset: int) -> List[dict]:
    sql, params = BOOKING_SELECT, [user["user_id"]]
    if status_filter:
        sql += " AND v.status = ?"
        params.append(status_filter)
    sql += " ORDER BY v.start_time DESC, v.reservation_id DESC OFFSET ? ROWS FETCH NEXT ? ROWS ONLY"
    with _db() as cur:
        cur.execute(sql, *params, offset, limit)
        rows = _rows(cur)
        for r in rows:
            r["has_review"] = bool(r["has_review"])
        return rows


def booking_detail(user: dict, reservation_id: int, cur=None) -> dict:
    if cur is None:
        with _db() as c:
            return booking_detail(user, reservation_id, c)
    cur.execute(BOOKING_SELECT + " AND v.reservation_id = ?", user["user_id"], reservation_id)
    b = _one(cur)
    if b is None:
        raise _err(404, "Không tìm thấy đơn đặt phòng của bạn")
    b["has_review"] = bool(b["has_review"])
    cur.execute("SELECT re.equipment_id, e.name, re.quantity, re.unit_price FROM dbo.ReservationEquipments re "
                "JOIN dbo.Equipment e ON e.equipment_id = re.equipment_id WHERE re.reservation_id = ?",
                reservation_id)
    b["equipment"] = _rows(cur)
    cur.execute("SELECT rp.package_id, sp.name, rp.price FROM dbo.ReservationPackages rp "
                "JOIN dbo.ServicePackages sp ON sp.package_id = rp.package_id WHERE rp.reservation_id = ?",
                reservation_id)
    b["packages"] = _rows(cur)
    cur.execute("SELECT payment_id, amount, payment_method, status, transaction_code, paid_at FROM dbo.Payments "
                "WHERE reservation_id = ? ORDER BY payment_id", reservation_id)
    b["payments"] = _rows(cur)
    try:   # bảng khuyến mãi thuộc file 07; chưa chạy thì bỏ qua
        cur.execute("SELECT p.code, p.discount_type, p.discount_value, rp.discount_amount "
                    "FROM dbo.ReservationPromotions rp JOIN dbo.Promotions p ON p.promo_id = rp.promo_id "
                    "WHERE rp.reservation_id = ?", reservation_id)
        b["promotion"] = _one(cur)
    except pyodbc.Error:
        b["promotion"] = None
    cur.execute("SELECT dispute_id, reason, status, resolution, created_at FROM dbo.Disputes "
                "WHERE reservation_id = ? AND raised_by = ? ORDER BY dispute_id DESC",
                reservation_id, user["user_id"])
    b["disputes"] = _rows(cur)
    return b


def _proc(user: dict, reservation_id: int, sql: str, *params) -> dict:
    with _db() as cur:
        booking_detail(user, reservation_id, cur)          # chỉ chủ đơn mới thao tác được
        cur.execute(sql, *params)
        _drain(cur)
        return booking_detail(user, reservation_id, cur)


def add_equipment(user: dict, reservation_id: int, equipment_id: int, quantity: int) -> dict:
    return _proc(user, reservation_id,
                 "EXEC dbo.sp_AddReservationEquipment @reservation_id = ?, @equipment_id = ?, @quantity = ?, "
                 "@actor_id = ?", reservation_id, equipment_id, quantity, user["user_id"])


def add_package(user: dict, reservation_id: int, package_id: int, notes: Optional[str]) -> dict:
    return _proc(user, reservation_id,
                 "EXEC dbo.sp_AddReservationPackage @reservation_id = ?, @package_id = ?, @actor_id = ?, "
                 "@notes = ?", reservation_id, package_id, user["user_id"], notes)


def pay(user: dict, reservation_id: int, amount: float, method: str, transaction_code: Optional[str]) -> dict:
    return _proc(user, reservation_id,
                 "EXEC dbo.sp_ProcessPayment @reservation_id = ?, @amount = ?, @payment_method = ?, "
                 "@actor_id = ?, @transaction_code = ?",
                 reservation_id, Decimal(str(amount)), method, user["user_id"], transaction_code)


def cancel(user: dict, reservation_id: int) -> dict:
    return _proc(user, reservation_id, "EXEC dbo.sp_CancelReservation @reservation_id = ?, @actor_id = ?",
                 reservation_id, user["user_id"])


def raise_dispute(user: dict, reservation_id: int, reason: str) -> dict:
    with _db() as cur:
        booking_detail(user, reservation_id, cur)
        cur.execute("SELECT 1 FROM dbo.Disputes WHERE reservation_id = ? AND raised_by = ? "
                    "AND status IN ('OPEN','IN_REVIEW')", reservation_id, user["user_id"])
        if cur.fetchone():
            raise _err(409, "Bạn đã có khiếu nại đang xử lý cho đơn này.")
        cur.execute("INSERT INTO dbo.Disputes (reservation_id, raised_by, reason) VALUES (?, ?, ?)",
                    reservation_id, user["user_id"], reason.strip())
        did = _new_id(cur)
        cur.execute("SELECT dispute_id, reason, status, resolution, created_at FROM dbo.Disputes "
                    "WHERE dispute_id = ?", did)
        return _one(cur)


def review_booking(user: dict, reservation_id: int, rating: int, comment: Optional[str]) -> dict:
    """Đánh giá studio sau buổi thuê. Trigger trg_Reviews_Validate chỉ cho đơn COMPLETED của chính khách."""
    with _db() as cur:
        b = booking_detail(user, reservation_id, cur)
        if b["has_review"]:
            raise _err(409, "Bạn đã đánh giá đơn này rồi.")
        cur.execute("INSERT INTO dbo.Reviews (reservation_id, studio_id, customer_id, rating, comment) "
                    "VALUES (?, ?, ?, ?, ?)", reservation_id, b["studio_id"], user["user_id"], rating,
                    (comment or "").strip() or None)
        rid = _new_id(cur)
        cur.execute("SELECT review_id, reservation_id, studio_id, rating, comment, created_at FROM dbo.Reviews "
                    "WHERE review_id = ?", rid)
        return _one(cur)


# ------------------------------------------------------------------ tổng quan
def overview(user: dict) -> dict:
    """Số liệu trang chủ của khách: đơn sắp tới, chi tiêu 6 tháng, số đơn theo trạng thái."""
    uid = user["user_id"]
    with _db() as cur:
        cur.execute("SELECT status, COUNT(*) AS n FROM dbo.Reservations WHERE customer_id = ? GROUP BY status", uid)
        by_status = {r["status"]: r["n"] for r in _rows(cur)}
        cur.execute("SELECT TOP 1 v.reservation_id, v.room_name, v.studio_name, v.start_time, v.end_time, v.status "
                    "FROM dbo.vw_ReservationDetail v WHERE v.customer_id = ? AND v.status IN ('PENDING','CONFIRMED') "
                    "AND v.end_time >= GETDATE() ORDER BY v.start_time", uid)
        upcoming = _one(cur)
        cur.execute("SELECT FORMAT(p.paid_at, 'yyyy-MM') AS ym, SUM(p.amount) AS spent FROM dbo.Payments p "
                    "JOIN dbo.Reservations r ON r.reservation_id = p.reservation_id "
                    "WHERE r.customer_id = ? AND p.status = 'SUCCESS' AND p.paid_at >= DATEADD(MONTH, -5, "
                    "DATEFROMPARTS(YEAR(GETDATE()), MONTH(GETDATE()), 1)) GROUP BY FORMAT(p.paid_at, 'yyyy-MM')", uid)
        spent = {r["ym"]: r["spent"] for r in _rows(cur)}
        cur.execute("SELECT COUNT(*) FROM dbo.Reservations r WHERE r.customer_id = ? AND r.status = 'COMPLETED' "
                    "AND NOT EXISTS (SELECT 1 FROM dbo.Reviews rv WHERE rv.reservation_id = r.reservation_id)", uid)
        to_review = cur.fetchone()[0]
    today = date.today().replace(day=1)
    months = []
    for i in range(5, -1, -1):
        y, m = today.year, today.month - i
        while m <= 0:
            y, m = y - 1, m + 12
        key = f"{y}-{m:02d}"
        months.append({"month": key, "spent": spent.get(key, 0)})
    return {"by_status": by_status, "total_bookings": sum(by_status.values()), "upcoming": upcoming,
            "spending": months, "to_review": to_review}
