"""Thống kê cho admin."""
from database import get_db_connection


def booking_summary() -> dict:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT status, COUNT(1) AS total FROM Bookings GROUP BY status")
        by_status = {row.status: int(row.total) for row in cur.fetchall()}
        cur.execute("SELECT COUNT(1) FROM Users")
        users = int(cur.fetchone()[0])
        cur.execute("SELECT COUNT(1) FROM Rooms WHERE is_active = 1")
        rooms = int(cur.fetchone()[0])
        return {
            "total_bookings": sum(by_status.values()),
            "by_status": by_status,
            "total_users": users,
            "active_rooms": rooms,
        }
    finally:
        conn.close()
