"""Studio và đánh giá (bảng Studios, Reviews)."""
from typing import List, Optional

from fastapi import HTTPException

from database import get_db_connection


class StudioNotFoundError(Exception):
    pass


STUDIO_SELECT = """
    SELECT s.studio_id, s.provider_id, s.name, s.address, s.description, s.phone,
           AVG(CAST(rv.rating AS FLOAT)) AS avg_rating, COUNT(rv.review_id) AS review_count
    FROM dbo.Studios s
    LEFT JOIN dbo.Reviews rv ON rv.studio_id = s.studio_id
"""
STUDIO_GROUP = " GROUP BY s.studio_id, s.provider_id, s.name, s.address, s.description, s.phone"


def _studio_dict(row) -> dict:
    return {
        "studio_id": row.studio_id,
        "provider_id": row.provider_id,
        "name": row.name,
        "address": row.address,
        "description": row.description,
        "phone": row.phone,
        "avg_rating": round(float(row.avg_rating), 2) if row.avg_rating is not None else None,
        "review_count": int(row.review_count),
    }


def list_studios(limit: int = 20, offset: int = 0, keyword: Optional[str] = None) -> List[dict]:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        sql = STUDIO_SELECT + " WHERE s.status = 'APPROVED'"      # công khai: chỉ studio đã được admin duyệt
        params = []
        if keyword:
            sql += " AND (s.name LIKE ? OR s.address LIKE ?)"
            like = f"%{keyword}%"
            params += [like, like]
        sql += STUDIO_GROUP + " ORDER BY s.studio_id OFFSET ? ROWS FETCH NEXT ? ROWS ONLY"
        params += [offset, limit]
        cur.execute(sql, *params)
        return [_studio_dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def get_studio(studio_id: int) -> dict:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(STUDIO_SELECT + " WHERE s.studio_id = ?" + STUDIO_GROUP, studio_id)
        row = cur.fetchone()
        if row is None:
            raise StudioNotFoundError("Không tìm thấy studio")
        return _studio_dict(row)
    finally:
        conn.close()


def create_studio(provider_id: int, name: str, address: str, description, phone, city: str = "Chưa cập nhật") -> dict:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO dbo.Studios (provider_id, name, address, city, description, phone)
            OUTPUT INSERTED.studio_id
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            provider_id, name, address, city, description, phone,
        )
        new_id = int(cur.fetchone()[0])
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    return get_studio(new_id)


def list_reviews(studio_id: int, limit: int = 20, offset: int = 0) -> List[dict]:
    get_studio(studio_id)  # 404 nếu studio không tồn tại
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT review_id, studio_id, customer_id, rating, comment, created_at
            FROM dbo.Reviews WHERE studio_id = ?
            ORDER BY created_at DESC, review_id DESC OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
            """,
            studio_id, offset, limit,
        )
        return [
            {"review_id": r.review_id, "studio_id": r.studio_id, "customer_id": r.customer_id,
             "rating": r.rating, "comment": r.comment, "created_at": r.created_at}
            for r in cur.fetchall()
        ]
    finally:
        conn.close()


def add_review(studio_id: int, customer_id: int, rating: int, comment) -> dict:
    """Đánh giá studio: gắn vào đơn COMPLETED gần nhất của khách tại studio này mà chưa được đánh giá.
    (Bảng Reviews bắt buộc có reservation_id; trigger trg_Reviews_Validate kiểm tra lại.)"""
    get_studio(studio_id)
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT TOP 1 r.reservation_id FROM dbo.Reservations r
            JOIN dbo.Rooms rm ON rm.room_id = r.room_id
            WHERE rm.studio_id = ? AND r.customer_id = ? AND r.status = 'COMPLETED'
              AND NOT EXISTS (SELECT 1 FROM dbo.Reviews rv WHERE rv.reservation_id = r.reservation_id)
            ORDER BY r.end_time DESC
            """,
            studio_id, customer_id,
        )
        res = cur.fetchone()
        if res is None:
            raise HTTPException(status_code=409,
                                detail="Bạn cần có một đơn đã hoàn thành tại studio này (chưa đánh giá) mới đánh giá được.")
        cur.execute(
            """
            INSERT INTO dbo.Reviews (reservation_id, studio_id, customer_id, rating, comment)
            OUTPUT INSERTED.review_id, INSERTED.created_at
            VALUES (?, ?, ?, ?, ?)
            """,
            res.reservation_id, studio_id, customer_id, rating, comment,
        )
        row = cur.fetchone()
        conn.commit()
        return {"review_id": int(row[0]), "studio_id": studio_id, "customer_id": customer_id,
                "rating": rating, "comment": comment, "created_at": row[1]}
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
