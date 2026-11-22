"""Quản trị viên: duyệt nhà cung cấp và cơ sở, thống kê tổng quan."""
from typing import List, Optional

from provider.service import _db, _err, _one, _rows


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
