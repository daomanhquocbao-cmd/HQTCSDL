"""Nghiệp vụ booking, làm việc trực tiếp với SQL Server qua pyodbc."""
from datetime import datetime
from typing import List, Optional

from database import get_db_connection
from booking.schemas import BookingCreate


class BookingError(Exception):
    """Lỗi nghiệp vụ chung."""


class RoomNotFoundError(BookingError):
    pass


class TimeConflictError(BookingError):
    pass


class BookingNotFoundError(BookingError):
    pass


class PermissionDeniedError(BookingError):
    pass


class InvalidStateError(BookingError):
    pass


COLUMNS = "booking_id, user_id, room_id, start_time, end_time, status, note"


def _row_to_dict(row) -> dict:
    return {
        "booking_id": row.booking_id,
        "user_id": row.user_id,
        "room_id": row.room_id,
        "start_time": row.start_time,
        "end_time": row.end_time,
        "status": row.status,
        "note": row.note,
    }


def create_booking(user_id: int, data: BookingCreate) -> dict:
    conn = get_db_connection()
    try:
        cur = conn.cursor()

        cur.execute("SELECT 1 FROM Rooms WHERE room_id = ? AND is_active = 1", data.room_id)
        if cur.fetchone() is None:
            raise RoomNotFoundError("Phòng không tồn tại hoặc đã ngưng hoạt động")

        # UPDLOCK + HOLDLOCK chống 2 người đặt trùng giờ cùng lúc
        cur.execute(
            """
            SELECT COUNT(1) FROM Bookings WITH (UPDLOCK, HOLDLOCK)
            WHERE room_id = ? AND status IN ('pending', 'confirmed')
              AND start_time < ? AND end_time > ?
            """,
            data.room_id, data.end_time, data.start_time,
        )
        if cur.fetchone()[0] > 0:
            raise TimeConflictError("Khung giờ này đã có người đặt")

        cur.execute(
            f"""
            INSERT INTO Bookings (user_id, room_id, start_time, end_time, status, note)
            OUTPUT INSERTED.booking_id
            VALUES (?, ?, ?, ?, 'pending', ?)
            """,
            user_id, data.room_id, data.start_time, data.end_time, data.note,
        )
        new_id = int(cur.fetchone()[0])
        conn.commit()
        return get_booking(new_id, user_id, "admin")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_booking(booking_id: int, user_id: int, role: str) -> dict:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(f"SELECT {COLUMNS} FROM Bookings WHERE booking_id = ?", booking_id)
        row = cur.fetchone()
        if row is None:
            raise BookingNotFoundError("Không tìm thấy booking")
        if role != "admin" and row.user_id != user_id:
            raise PermissionDeniedError("Bạn không có quyền xem booking này")
        return _row_to_dict(row)
    finally:
        conn.close()


def list_my_bookings(user_id: int, status: Optional[str] = None) -> List[dict]:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        sql = f"SELECT {COLUMNS} FROM Bookings WHERE user_id = ?"
        params = [user_id]
        if status:
            sql += " AND status = ?"
            params.append(status)
        sql += " ORDER BY start_time DESC"
        cur.execute(sql, *params)
        return [_row_to_dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def cancel_booking(booking_id: int, user_id: int, role: str) -> dict:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(f"SELECT {COLUMNS} FROM Bookings WHERE booking_id = ?", booking_id)
        row = cur.fetchone()
        if row is None:
            raise BookingNotFoundError("Không tìm thấy booking")
        if role != "admin" and row.user_id != user_id:
            raise PermissionDeniedError("Bạn không có quyền hủy booking này")
        if row.status == "cancelled":
            raise InvalidStateError("Booking đã bị hủy trước đó")
        if row.start_time <= datetime.now():
            raise InvalidStateError("Không thể hủy booking đã bắt đầu")

        cur.execute("UPDATE Bookings SET status = 'cancelled' WHERE booking_id = ?", booking_id)
        conn.commit()
        result = _row_to_dict(row)
        result["status"] = "cancelled"
        return result
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
