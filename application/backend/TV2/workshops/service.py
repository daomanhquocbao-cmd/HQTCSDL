"""Workshop. Đăng ký gọi stored procedure sp_RegisterWorkshop (kiểm tra sức chứa, chống đăng ký trùng)."""
from typing import List

import pyodbc

from core.db_errors import extract_message
from database import get_db_connection


class WorkshopError(Exception):
    pass


class WorkshopNotFoundError(WorkshopError):
    pass


class AlreadyRegisteredError(WorkshopError):
    pass


class WorkshopFullError(WorkshopError):
    pass


SELECT_SQL = """
    SELECT w.workshop_id, w.expert_id, u.username AS expert_name, w.title, w.description,
           w.capacity, w.start_time, w.end_time, COUNT(wr.registration_id) AS registered
    FROM dbo.Workshops w
    LEFT JOIN dbo.Users u ON u.user_id = w.expert_id
    LEFT JOIN dbo.WorkshopRegistrations wr ON wr.workshop_id = w.workshop_id
"""
GROUP_SQL = (" GROUP BY w.workshop_id, w.expert_id, u.username, w.title, w.description, "
             "w.capacity, w.start_time, w.end_time")


def _to_dict(row) -> dict:
    registered = int(row.registered)
    return {
        "workshop_id": row.workshop_id,
        "expert_id": row.expert_id,
        "expert_name": row.expert_name,
        "title": row.title,
        "description": row.description,
        "capacity": row.capacity,
        "registered": registered,
        "remaining_slots": max(row.capacity - registered, 0),
        "start_time": row.start_time,
        "end_time": row.end_time,
    }


def list_workshops(upcoming_only: bool = False, limit: int = 20, offset: int = 0) -> List[dict]:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        sql = SELECT_SQL
        if upcoming_only:
            sql += " WHERE w.start_time >= GETDATE()"
        sql += GROUP_SQL + " ORDER BY w.start_time OFFSET ? ROWS FETCH NEXT ? ROWS ONLY"
        cur.execute(sql, offset, limit)
        return [_to_dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def get_workshop(workshop_id: int) -> dict:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(SELECT_SQL + " WHERE w.workshop_id = ?" + GROUP_SQL, workshop_id)
        row = cur.fetchone()
        if row is None:
            raise WorkshopNotFoundError("Workshop không tồn tại trên hệ thống")
        return _to_dict(row)
    finally:
        conn.close()


def create_workshop(expert_id: int, title: str, description, capacity: int, start_time, end_time) -> dict:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO dbo.Workshops (expert_id, title, description, capacity, start_time, end_time)
            OUTPUT INSERTED.workshop_id
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            expert_id, title, description, capacity, start_time, end_time,
        )
        new_id = int(cur.fetchone()[0])
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    return get_workshop(new_id)


def register(workshop_id: int, customer_id: int) -> dict:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("EXEC dbo.sp_RegisterWorkshop @workshop_id = ?, @customer_id = ?",
                    workshop_id, customer_id)
        try:
            while cur.nextset():
                pass
        except pyodbc.ProgrammingError:
            pass
        conn.commit()
        return {"workshop_id": workshop_id, "customer_id": customer_id,
                "message": "Đăng ký tham gia workshop thành công"}
    except pyodbc.Error as exc:
        conn.rollback()
        msg = extract_message(exc)
        lowered = msg.lower()
        if "không tồn tại" in lowered:
            raise WorkshopNotFoundError(msg) from exc
        if "đã đăng ký" in lowered:
            raise AlreadyRegisteredError(msg) from exc
        if "hết chỗ" in lowered:
            raise WorkshopFullError(msg) from exc
        raise WorkshopError(msg) from exc
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def unregister(workshop_id: int, customer_id: int) -> None:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM dbo.WorkshopRegistrations WHERE workshop_id = ? AND customer_id = ?",
                    workshop_id, customer_id)
        if cur.rowcount == 0:
            raise WorkshopNotFoundError("Bạn chưa đăng ký workshop này")
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def list_my_workshops(customer_id: int) -> List[dict]:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        sql = (SELECT_SQL + " WHERE w.workshop_id IN (SELECT workshop_id FROM dbo.WorkshopRegistrations "
               "WHERE customer_id = ?)" + GROUP_SQL + " ORDER BY w.start_time")
        cur.execute(sql, customer_id)
        return [_to_dict(r) for r in cur.fetchall()]
    finally:
        conn.close()
