"""Quản trị viên: duyệt nhà cung cấp và cơ sở, thống kê tổng quan."""
from contextlib import contextmanager
from typing import List, Optional

from fastapi import HTTPException

from core.platform_settings import DEFAULTS, cast, get_setting
from provider.service import _db, _drain, _err, _one, _rows

MISSING_08 = ("Chưa có bảng/view mới trong CSDL. Hãy chạy database/08_collections_settings_ledger.sql "
              "(sau 01, 02, 03, 06_provider_additions, 07) rồi thử lại.")


@contextmanager
def _db08():
    """Như _db() nhưng báo 503 rõ ràng khi chưa chạy file SQL 08."""
    try:
        with _db() as cur:
            yield cur
    except HTTPException as exc:
        low = str(exc.detail).lower()
        if "invalid object name" in low or "could not find stored procedure" in low:
            raise HTTPException(status_code=503, detail=MISSING_08) from exc
        raise


def overview() -> dict:
    with _db() as cur:
        cur.execute(
            "SELECT (SELECT COUNT(*) FROM dbo.Users WHERE role = 'PROVIDER' AND status = 'PENDING') AS pending_providers, "
            "(SELECT COUNT(*) FROM dbo.Users WHERE role = 'PROVIDER' AND status = 'ACTIVE') AS active_providers, "
            "(SELECT COUNT(*) FROM dbo.Studios WHERE status = 'PENDING') AS pending_studios, "
            "(SELECT COUNT(*) FROM dbo.Studios WHERE status = 'APPROVED') AS approved_studios, "
            "(SELECT COUNT(*) FROM dbo.Disputes WHERE status IN ('OPEN','IN_REVIEW')) AS open_disputes, "
            "(SELECT COUNT(*) FROM dbo.Users WHERE role = 'CUSTOMER') AS customers, "
            "(SELECT COUNT(*) FROM dbo.Reservations) AS reservations")
        return _one(cur)


def list_providers(status_filter: Optional[str]) -> List[dict]:
    with _db() as cur:
        sql = ("SELECT u.user_id, u.username, u.full_name, u.email, u.phone, u.status, u.created_at, "
               "(SELECT COUNT(*) FROM dbo.Studios s WHERE s.provider_id = u.user_id) AS studio_count, "
               "(SELECT COUNT(*) FROM dbo.Studios s WHERE s.provider_id = u.user_id AND s.status = 'PENDING') "
               "AS pending_studio_count FROM dbo.Users u WHERE u.role = 'PROVIDER'")
        params = []
        if status_filter:
            sql += " AND u.status = ?"
            params.append(status_filter)
        cur.execute(sql + " ORDER BY CASE u.status WHEN 'PENDING' THEN 0 ELSE 1 END, u.created_at DESC", *params)
        return _rows(cur)


def set_provider_status(admin: dict, user_id: int, new_status: str) -> dict:
    """PENDING/SUSPENDED -> ACTIVE (duyệt / mở khóa); ACTIVE/PENDING -> SUSPENDED (từ chối / khóa)."""
    with _db() as cur:
        cur.execute("SELECT status FROM dbo.Users WITH (UPDLOCK) WHERE user_id = ? AND role = 'PROVIDER'", user_id)
        row = cur.fetchone()
        if row is None:
            raise _err(404, "Không tìm thấy nhà cung cấp")
        if row.status == new_status:
            raise _err(409, f"Nhà cung cấp đã ở trạng thái {new_status}")
        cur.execute("UPDATE dbo.Users SET status = ? WHERE user_id = ?", new_status, user_id)
        if new_status == "SUSPENDED":
            # khóa nhà cung cấp thì các cơ sở đang mở cũng ngừng nhận đặt (sp_CreateReservation chỉ nhận studio APPROVED)
            cur.execute("UPDATE dbo.Studios SET status = 'SUSPENDED' WHERE provider_id = ? AND status = 'APPROVED'",
                        user_id)
        cur.execute("SELECT user_id, username, full_name, email, status FROM dbo.Users WHERE user_id = ?", user_id)
        return _one(cur)


def list_studios(status_filter: Optional[str]) -> List[dict]:
    with _db() as cur:
        sql = ("SELECT s.studio_id, s.name, s.address, s.city, s.status, s.created_at, u.user_id AS provider_id, "
               "u.full_name AS provider_name, u.status AS provider_status, "
               "(SELECT COUNT(*) FROM dbo.Rooms r WHERE r.studio_id = s.studio_id) AS room_count "
               "FROM dbo.Studios s JOIN dbo.Users u ON u.user_id = s.provider_id WHERE 1 = 1")
        params = []
        if status_filter:
            sql += " AND s.status = ?"
            params.append(status_filter)
        cur.execute(sql + " ORDER BY CASE s.status WHEN 'PENDING' THEN 0 ELSE 1 END, s.studio_id DESC", *params)
        return _rows(cur)


def set_studio_status(studio_id: int, new_status: str) -> dict:
    with _db() as cur:
        cur.execute("SELECT s.status, u.status AS provider_status FROM dbo.Studios s WITH (UPDLOCK) "
                    "JOIN dbo.Users u ON u.user_id = s.provider_id WHERE s.studio_id = ?", studio_id)
        row = cur.fetchone()
        if row is None:
            raise _err(404, "Không tìm thấy cơ sở")
        if new_status == "APPROVED" and row.provider_status != "ACTIVE":
            raise _err(409, "Hãy duyệt nhà cung cấp trước khi duyệt cơ sở của họ")
        cur.execute("UPDATE dbo.Studios SET status = ? WHERE studio_id = ?", new_status, studio_id)
        cur.execute("SELECT studio_id, name, status FROM dbo.Studios WHERE studio_id = ?", studio_id)
        return _one(cur)


# ---------------------------------------------------------------- người dùng
def list_users(role: Optional[str], status_filter: Optional[str], q: Optional[str],
               limit: int, offset: int) -> List[dict]:
    sql = ("SELECT user_id, username, full_name, email, phone, role, status, created_at FROM dbo.Users WHERE 1 = 1")
    params: list = []
    for clause, value in ((" AND role = ?", role), (" AND status = ?", status_filter)):
        if value:
            sql += clause
            params.append(value)
    if q:
        sql += " AND (username LIKE ? OR full_name LIKE ? OR email LIKE ?)"
        params += [f"%{q}%"] * 3
    with _db() as cur:
        cur.execute(sql + " ORDER BY created_at DESC, user_id DESC OFFSET ? ROWS FETCH NEXT ? ROWS ONLY",
                    *params, offset, limit)
        return _rows(cur)


def set_user_status(admin: dict, user_id: int, new_status: str) -> dict:
    """Khóa / mở khóa tài khoản (ACTIVE <-> SUSPENDED). Không tự khóa mình, không đụng tài khoản admin khác."""
    if user_id == admin["user_id"]:
        raise _err(409, "Bạn không thể tự đổi trạng thái tài khoản của mình")
    with _db() as cur:
        cur.execute("SELECT role, status FROM dbo.Users WITH (UPDLOCK) WHERE user_id = ?", user_id)
        row = cur.fetchone()
        if row is None:
            raise _err(404, "Không tìm thấy người dùng")
        if row.role == "ADMIN":
            raise _err(403, "Không thể đổi trạng thái tài khoản quản trị viên")
        if row.role == "PROVIDER":
            raise _err(409, "Nhà cung cấp được duyệt / khóa ở mục Nhà cung cấp (kèm các cơ sở của họ)")
        cur.execute("UPDATE dbo.Users SET status = ? WHERE user_id = ?", new_status, user_id)
        cur.execute("SELECT user_id, username, full_name, email, role, status FROM dbo.Users WHERE user_id = ?",
                    user_id)
        return _one(cur)


# ------------------------------------------------------- giao dịch và hoàn tiền
def list_payments(status_filter: Optional[str], q: Optional[str], limit: int, offset: int) -> dict:
    """Sổ giao dịch (vw_PaymentLedger) + tổng hợp theo trạng thái cho toàn nền tảng."""
    sql = "SELECT * FROM dbo.vw_PaymentLedger WHERE 1 = 1"
    params: list = []
    if status_filter:
        sql += " AND status = ?"
        params.append(status_filter)
    if q:
        sql += " AND (customer_name LIKE ? OR studio_name LIKE ? OR transaction_code LIKE ?)"
        params += [f"%{q}%"] * 3
    with _db08() as cur:
        cur.execute(sql + " ORDER BY created_at DESC, payment_id DESC OFFSET ? ROWS FETCH NEXT ? ROWS ONLY",
                    *params, offset, limit)
        items = _rows(cur)
        cur.execute("SELECT status, COUNT(*) AS n, ISNULL(SUM(amount), 0) AS amount FROM dbo.Payments GROUP BY status")
        totals = {r["status"]: {"count": r["n"], "amount": r["amount"]} for r in _rows(cur)}
    return {"items": items, "totals": totals}


def refund_payment(admin: dict, payment_id: int) -> dict:
    with _db08() as cur:
        cur.execute("EXEC dbo.sp_RefundPayment @payment_id = ?, @actor_id = ?", payment_id, admin["user_id"])
        _drain(cur)
        cur.execute("SELECT * FROM dbo.vw_PaymentLedger WHERE payment_id = ?", payment_id)
        return _one(cur)


# ------------------------------------------------------------ cấu hình nền tảng
def list_settings() -> List[dict]:
    with _db08() as cur:
        cur.execute("SELECT s.setting_key, s.setting_value, s.value_type, s.description, s.updated_at, "
                    "u.full_name AS updated_by_name FROM dbo.SystemSettings s "
                    "LEFT JOIN dbo.Users u ON u.user_id = s.updated_by ORDER BY s.setting_key")
        rows = _rows(cur)
    for r in rows:
        r["value"] = cast(r["setting_value"], r["value_type"])
        r["default"] = DEFAULTS.get(r["setting_key"])
    return rows


def update_setting(admin: dict, key: str, raw_value) -> dict:
    with _db08() as cur:
        cur.execute("SELECT value_type FROM dbo.SystemSettings WITH (UPDLOCK) WHERE setting_key = ?", key)
        row = cur.fetchone()
        if row is None:
            raise _err(404, "Không có cấu hình này")
        vtype = row.value_type
        if vtype == "BOOL":
            if not isinstance(raw_value, bool) and str(raw_value).lower() not in ("0", "1", "true", "false"):
                raise _err(400, "Giá trị phải là bật hoặc tắt")
            stored = "1" if cast(str(raw_value), "BOOL") else "0"
        elif vtype in ("INT", "NUMBER"):
            try:
                num = cast(str(raw_value), vtype)
            except ValueError:
                raise _err(400, "Giá trị phải là số")
            if num < 0 or ((key.endswith("_pct") or key.endswith("_percent")) and num > 100):
                raise _err(400, "Giá trị ngoài khoảng cho phép")
            stored = str(num)
        else:
            stored = str(raw_value).strip()
            if not stored or len(stored) > 200:
                raise _err(400, "Giá trị không được rỗng và tối đa 200 ký tự")
        cur.execute("UPDATE dbo.SystemSettings SET setting_value = ?, updated_by = ?, updated_at = GETDATE() "
                    "WHERE setting_key = ?", stored, admin["user_id"], key)
        if key in ("pricing.high_occupancy_pct", "pricing.low_occupancy_pct"):
            cur.execute("SELECT MAX(CASE WHEN setting_key = 'pricing.high_occupancy_pct' THEN CAST(setting_value AS INT) END), "
                        "MIN(CASE WHEN setting_key = 'pricing.low_occupancy_pct' THEN CAST(setting_value AS INT) END) "
                        "FROM dbo.SystemSettings WHERE setting_key IN "
                        "('pricing.high_occupancy_pct', 'pricing.low_occupancy_pct')")
            high, low = cur.fetchone()
            if high is not None and low is not None and low >= high:
                raise _err(400, "Ngưỡng giảm giá phải thấp hơn ngưỡng tăng giá")    # _db() rollback cả cập nhật
    return next(r for r in list_settings() if r["setting_key"] == key)


# ------------------------------------------------------------------- báo cáo
def reports(months: int) -> dict:
    """Báo cáo toàn hệ thống: doanh thu theo tháng, top cơ sở / phòng, đơn theo trạng thái, người dùng, khiếu nại."""
    with _db() as cur:
        cur.execute("SELECT FORMAT(paid_at, 'yyyy-MM') AS month, "
                    "SUM(CASE WHEN status = 'SUCCESS' THEN amount ELSE 0 END) AS revenue, "
                    "SUM(CASE WHEN status = 'REFUNDED' THEN amount ELSE 0 END) AS refunded, COUNT(*) AS payments "
                    "FROM dbo.Payments WHERE paid_at IS NOT NULL AND status IN ('SUCCESS', 'REFUNDED') "
                    "AND paid_at >= DATEADD(MONTH, ?, DATEFROMPARTS(YEAR(GETDATE()), MONTH(GETDATE()), 1)) "
                    "GROUP BY FORMAT(paid_at, 'yyyy-MM') ORDER BY month", -(months - 1))
        revenue = _rows(cur)
        cur.execute("SELECT TOP 5 s.studio_id, s.name AS studio_name, COUNT(DISTINCT r.reservation_id) AS bookings, "
                    "ISNULL(SUM(p.amount), 0) AS revenue FROM dbo.Studios s "
                    "JOIN dbo.Rooms rm ON rm.studio_id = s.studio_id JOIN dbo.Reservations r ON r.room_id = rm.room_id "
                    "LEFT JOIN dbo.Payments p ON p.reservation_id = r.reservation_id AND p.status = 'SUCCESS' "
                    "WHERE r.status <> 'CANCELLED' GROUP BY s.studio_id, s.name ORDER BY revenue DESC, bookings DESC")
        top_studios = _rows(cur)
        cur.execute("SELECT TOP 5 rm.room_id, rm.name AS room_name, s.name AS studio_name, COUNT(*) AS bookings "
                    "FROM dbo.Reservations r JOIN dbo.Rooms rm ON rm.room_id = r.room_id "
                    "JOIN dbo.Studios s ON s.studio_id = rm.studio_id WHERE r.status <> 'CANCELLED' "
                    "GROUP BY rm.room_id, rm.name, s.name ORDER BY bookings DESC")
        top_rooms = _rows(cur)
        cur.execute("SELECT status, COUNT(*) AS n FROM dbo.Reservations GROUP BY status")
        by_status = {r["status"]: r["n"] for r in _rows(cur)}
        cur.execute("SELECT role, COUNT(*) AS n FROM dbo.Users GROUP BY role")
        users = {r["role"]: r["n"] for r in _rows(cur)}
        cur.execute("SELECT payment_method, COUNT(*) AS n, SUM(amount) AS amount FROM dbo.Payments "
                    "WHERE status = 'SUCCESS' GROUP BY payment_method ORDER BY amount DESC")
        methods = _rows(cur)
        cur.execute("SELECT status, COUNT(*) AS n FROM dbo.Disputes GROUP BY status")
        disputes = {r["status"]: r["n"] for r in _rows(cur)}
        cur.execute("SELECT (SELECT COUNT(*) FROM dbo.CommunityPosts) AS posts, "
                    "(SELECT COUNT(*) FROM dbo.Workshops) AS workshops, "
                    "(SELECT COUNT(*) FROM dbo.Reviews) AS reviews, "
                    "(SELECT ISNULL(AVG(CAST(rating AS FLOAT)), 0) FROM dbo.Reviews) AS avg_rating")
        content = _one(cur)
    total_revenue = sum(r["revenue"] for r in revenue)
    pct = float(get_setting("platform.commission_percent", 10.0))
    for r in revenue:
        r["commission"] = round(float(r["revenue"] or 0) * pct / 100, 2)
    commission_total = round(float(total_revenue or 0) * pct / 100, 2)
    return {"months": months, "revenue_by_month": revenue, "total_revenue": total_revenue,
            "commission_percent": pct, "commission_total": commission_total,
            "provider_payout": round(float(total_revenue or 0) - commission_total, 2),
            "total_refunded": sum(r["refunded"] for r in revenue), "top_studios": top_studios,
            "top_rooms": top_rooms, "bookings_by_status": by_status, "users_by_role": users,
            "payment_methods": methods, "disputes_by_status": disputes, "content": content}
