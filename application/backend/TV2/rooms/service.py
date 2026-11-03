"""CRUD phòng/studio."""
from typing import List

from database import get_db_connection

COLUMNS = "room_id, name, description, hourly_price, is_active"
UPDATABLE_FIELDS = ("name", "description", "hourly_price", "is_active")


class RoomNotFoundError(Exception):
    pass


def _to_dict(row) -> dict:
    return {
        "room_id": row.room_id,
        "name": row.name,
        "description": row.description,
        "hourly_price": float(row.hourly_price or 0),
        "is_active": bool(row.is_active),
    }


def list_rooms(only_active: bool = True) -> List[dict]:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        sql = f"SELECT {COLUMNS} FROM Rooms"
        if only_active:
            sql += " WHERE is_active = 1"
        cur.execute(sql + " ORDER BY room_id")
        return [_to_dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def get_room(room_id: int) -> dict:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(f"SELECT {COLUMNS} FROM Rooms WHERE room_id = ?", room_id)
        row = cur.fetchone()
        if row is None:
            raise RoomNotFoundError("Không tìm thấy phòng")
        return _to_dict(row)
    finally:
        conn.close()


def create_room(name: str, description, hourly_price: float) -> dict:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO Rooms (name, description, hourly_price, is_active)
            OUTPUT INSERTED.room_id
            VALUES (?, ?, ?, 1)
            """,
            name, description, hourly_price,
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
        cur.execute(f"UPDATE Rooms SET {set_clause} WHERE room_id = ?", *fields.values(), room_id)
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
    """Xóa mềm: chỉ đánh dấu is_active = 0 để giữ lịch sử booking."""
    update_room(room_id, {"is_active": False})
