"""CRUD phòng (bảng Rooms)."""
from datetime import datetime
from typing import List, Optional

from database import get_db_connection

COLUMNS = "room_id, studio_id, name, room_type, capacity, price_per_hour, description, status"
UPDATABLE_FIELDS = ("name", "room_type", "capacity", "price_per_hour", "description", "status")


class RoomNotFoundError(Exception):
    pass


class StudioNotFoundError(Exception):
    pass


def _to_dict(row) -> dict:
    return {
        "room_id": row.room_id,
        "studio_id": row.studio_id,
        "name": row.name,
        "room_type": row.room_type,
        "capacity": row.capacity,
        "price_per_hour": float(row.price_per_hour),
        "description": row.description,
        "status": row.status,
    }


def list_rooms(studio_id: Optional[int] = None, room_type: Optional[str] = None,
               include_inactive: bool = False, limit: int = 20, offset: int = 0) -> List[dict]:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        sql = f"SELECT {COLUMNS} FROM dbo.Rooms WHERE 1 = 1"
        params = []
        if not include_inactive:
            sql += " AND status = 'AVAILABLE'"
        if studio_id is not None:
            sql += " AND studio_id = ?"
            params.append(studio_id)
        if room_type:
            sql += " AND room_type = ?"
            params.append(room_type)
        sql += " ORDER BY room_id OFFSET ? ROWS FETCH NEXT ? ROWS ONLY"
        params += [offset, limit]
        cur.execute(sql, *params)
        return [_to_dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def list_available_rooms(start_time: datetime, end_time: datetime,
                         room_type: Optional[str] = None, limit: int = 20, offset: int = 0) -> List[dict]:
    """Các phòng AVAILABLE chưa có đơn PENDING/CONFIRMED trùng khung giờ."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        sql = f"""
            SELECT {COLUMNS} FROM dbo.Rooms r
            WHERE r.status = 'AVAILABLE'
              AND NOT EXISTS (
                  SELECT 1 FROM dbo.Reservations res
                  WHERE res.room_id = r.room_id
                    AND res.status IN ('PENDING', 'CONFIRMED')
                    AND ? < res.end_time AND ? > res.start_time)
        """
        params = [start_time, end_time]
        if room_type:
            sql += " AND r.room_type = ?"
            params.append(room_type)
        sql += " ORDER BY r.room_id OFFSET ? ROWS FETCH NEXT ? ROWS ONLY"
        params += [offset, limit]
        cur.execute(sql, *params)
        return [_to_dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def get_room(room_id: int) -> dict:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(f"SELECT {COLUMNS} FROM dbo.Rooms WHERE room_id = ?", room_id)
        row = cur.fetchone()
        if row is None:
            raise RoomNotFoundError("Không tìm thấy phòng")
        return _to_dict(row)
    finally:
        conn.close()


def get_studio_provider_id(studio_id: int) -> Optional[int]:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT provider_id FROM dbo.Studios WHERE studio_id = ?", studio_id)
        row = cur.fetchone()
        if row is None:
            raise StudioNotFoundError("Không tìm thấy studio")
        return row.provider_id
    finally:
        conn.close()


def create_room(studio_id: int, name: str, room_type: str, capacity: int,
                price_per_hour: float, description, status: str) -> dict:
    get_studio_provider_id(studio_id)  # ném StudioNotFoundError nếu studio không tồn tại
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO dbo.Rooms (studio_id, name, room_type, capacity, price_per_hour, description, status)
            OUTPUT INSERTED.room_id
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            studio_id, name, room_type, capacity, price_per_hour, description, status,
        )
        new_id = int(cur.fetchone()[0])
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    return get_room(new_id)


def update_room(room_id: int, changes: dict) -> dict:
    fields = {k: v for k, v in changes.items() if k in UPDATABLE_FIELDS}
    if not fields:
        return get_room(room_id)
    set_clause = ", ".join(f"{col} = ?" for col in fields)  # tên cột lấy từ whitelist
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(f"UPDATE dbo.Rooms SET {set_clause} WHERE room_id = ?", *fields.values(), room_id)
        if cur.rowcount == 0:
            raise RoomNotFoundError("Không tìm thấy phòng")
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    return get_room(room_id)


def deactivate_room(room_id: int) -> None:
    """Xóa mềm: đặt status = INACTIVE để giữ lịch sử đặt phòng."""
    update_room(room_id, {"status": "INACTIVE"})
