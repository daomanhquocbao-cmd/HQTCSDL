"""Nghiệp vụ đặt phòng. Tạo đơn và đổi trạng thái gọi stored procedure trong SQL Server."""
import re
from datetime import datetime
from typing import List, Optional

import pyodbc

from database import get_db_connection
from booking.schemas import BookingCreate

COLUMNS = ("reservation_id, room_id, customer_id, start_time, end_time, "
           "total_amount, customer_note, status")


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


def _extract_message(exc: Exception) -> str:
    """Lấy nội dung RAISERROR từ chuỗi lỗi của pyodbc."""
    text = str(exc)
    match = re.search(r"\[SQL Server\](.*?)(?: \(\d+\))", text, re.S)
    return (match.group(1) if match else text).strip()


def _map_db_error(exc: Exception) -> BookingError:
    msg = _extract_message(exc)
    lowered = msg.lower()
    if "đã có người đặt" in lowered:
        return TimeConflictError(msg)
    if "không tìm thấy thông tin phòng" in lowered:
        return RoomNotFoundError(msg)
    if "không tìm thấy đơn" in lowered:
        return BookingNotFoundError(msg)
    if "foreign key" in lowered:
        return BookingError("Dữ liệu tham chiếu không tồn tại (phòng hoặc người dùng)")
    return BookingError(msg)


def _row_to_dict(row) -> dict:
    return {
        "reservation_id": row.reservation_id,
        "room_id": row.room_id,
        "customer_id": row.customer_id,
        "start_time": row.start_time,
        "end_time": row.end_time,
        "total_amount": float(row.total_amount),
        "customer_note": row.customer_note,
        "status": row.status,
    }


def _drain(cursor) -> None:
    """Đọc hết kết quả/thông báo của stored procedure để lỗi RAISERROR được ném ra."""
    try:
        while cursor.nextset():
            pass
    except pyodbc.ProgrammingError:
        pass


def _fetch(cursor, booking_id: int):
    cursor.execute(f"SELECT {COLUMNS} FROM dbo.Reservations WHERE reservation_id = ?", booking_id)
    return cursor.fetchone()


def create_booking(user_id: int, data: BookingCreate) -> dict:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "EXEC dbo.sp_CreateReservation @room_id = ?, @customer_id = ?, "
            "@start_time = ?, @end_time = ?, @customer_note = ?",
            data.room_id, user_id, data.start_time, data.end_time, data.customer_note,
        )
        _drain(cur)
        cur.execute(
            f"SELECT TOP 1 {COLUMNS} FROM dbo.Reservations "
            "WHERE room_id = ? AND customer_id = ? AND start_time = ? AND end_time = ? "
            "ORDER BY reservation_id DESC",
            data.room_id, user_id, data.start_time, data.end_time,
        )
        row = cur.fetchone()
        conn.commit()
        if row is None:
            raise BookingError("Không tạo được đơn đặt phòng")
        return _row_to_dict(row)
    except pyodbc.Error as exc:
        conn.rollback()
        raise _map_db_error(exc) from exc
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_booking(booking_id: int, user_id: int, role: str) -> dict:
    conn = get_db_connection()
    try:
        row = _fetch(conn.cursor(), booking_id)
        if row is None:
            raise BookingNotFoundError("Không tìm thấy đơn đặt phòng")
        if str(role).upper() != "ADMIN" and row.customer_id != user_id:
            raise PermissionDeniedError("Bạn không có quyền xem đơn này")
        return _row_to_dict(row)
    finally:
        conn.close()


def list_my_bookings(user_id: int, status: Optional[str] = None,
                     limit: int = 20, offset: int = 0) -> List[dict]:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        sql = f"SELECT {COLUMNS} FROM dbo.Reservations WHERE customer_id = ?"
        params = [user_id]
        if status:
            sql += " AND status = ?"
            params.append(status)
        sql += " ORDER BY start_time DESC OFFSET ? ROWS FETCH NEXT ? ROWS ONLY"
        params += [offset, limit]
        cur.execute(sql, *params)
        return [_row_to_dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def _change_status(booking_id: int, new_status: str, changed_by: int) -> dict:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "EXEC dbo.sp_UpdateReservationStatus @reservation_id = ?, @new_status = ?, @changed_by = ?",
            booking_id, new_status, changed_by,
        )
        _drain(cur)
        row = _fetch(cur, booking_id)
        conn.commit()
        return _row_to_dict(row)
    except pyodbc.Error as exc:
        conn.rollback()
        msg = _extract_message(exc)
        if "không tìm thấy đơn" in msg.lower():
            raise BookingNotFoundError(msg) from exc
        raise InvalidStateError(msg) from exc
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def cancel_booking(booking_id: int, user_id: int, role: str) -> dict:
    """Khách hủy đơn của mình (hoặc admin hủy bất kỳ đơn nào)."""
    current = get_booking(booking_id, user_id, role)  # kiểm tra tồn tại + quyền
    if current["status"] in ("CANCELLED", "COMPLETED"):
        raise InvalidStateError("Đơn đã kết thúc, không thể hủy")
    if current["start_time"] <= datetime.now():
        raise InvalidStateError("Không thể hủy đơn đã bắt đầu")
    return _change_status(booking_id, "CANCELLED", user_id)


def update_booking_status(booking_id: int, new_status: str, admin_id: int) -> dict:
    """Admin xác nhận / hoàn thành / hủy đơn."""
    return _change_status(booking_id, new_status, admin_id)
