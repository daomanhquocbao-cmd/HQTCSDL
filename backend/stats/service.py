"""Thống kê cho admin."""
from database import get_db_connection


def booking_summary() -> dict:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT status, COUNT(1) AS total FROM dbo.Reservations GROUP BY status")
        by_status = {row.status: int(row.total) for row in cur.fetchall()}

        cur.execute("SELECT role, COUNT(1) AS total FROM dbo.Users GROUP BY role")
        users_by_role = {row.role: int(row.total) for row in cur.fetchall()}

        cur.execute("SELECT COUNT(1) FROM dbo.Studios")
        studios = int(cur.fetchone()[0])
        cur.execute("SELECT COUNT(1) FROM dbo.Rooms WHERE status = 'AVAILABLE'")
        rooms = int(cur.fetchone()[0])
        cur.execute("SELECT COALESCE(SUM(amount), 0) FROM dbo.Payments WHERE status = 'SUCCESS'")
        revenue = float(cur.fetchone()[0])

        return {
            "total_reservations": sum(by_status.values()),
            "by_status": by_status,
            "users_by_role": users_by_role,
            "total_studios": studios,
            "available_rooms": rooms,
            "total_revenue": revenue,
        }
    finally:
        conn.close()
