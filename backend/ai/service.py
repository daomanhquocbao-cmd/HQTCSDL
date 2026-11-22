"""AI cho khách hàng: gợi ý phòng (sp_RecommendRooms) và tìm phòng bằng câu hỏi tự nhiên.

Đây là heuristic / luật, không gọi mô hình ngôn ngữ ngoài: điểm gợi ý tính trong SQL từ đánh giá,
độ phổ biến, lịch sử khách và mức giá; "hỏi AI" tách từ khóa (loại phòng, ngân sách, số người, thành phố).
"""
import re
import unicodedata
from typing import List, Optional

from provider.analytics import _db_ext
from provider.service import _rows


def recommend(customer_id: Optional[int], top: int) -> List[dict]:
    with _db_ext() as cur:
        cur.execute("EXEC dbo.sp_RecommendRooms @customer_id = ?, @top = ?", customer_id, top)
        return _rows(cur)


def _fold(text: str) -> str:
    text = unicodedata.normalize("NFD", text.lower().replace("đ", "d"))
    return "".join(c for c in text if unicodedata.category(c) != "Mn")


def parse_query(text: str, cities: List[str]) -> dict:
    """Tách điều kiện từ câu tiếng Việt, ví dụ 'phòng tối dưới 300k ở Hà Nội cho 4 người'."""
    t = _fold(text)
    out: dict = {"room_type": None, "max_price": None, "capacity": None, "city": None}
    if re.search(r"phong toi|darkroom|rua phim|in anh", t):
        out["room_type"] = "DARKROOM"
    elif re.search(r"studio|chup|phong chup", t):
        out["room_type"] = "STUDIO"
    m = re.search(r"(?:duoi|toi da|khong qua|<=?)\s*(\d+(?:[.,]\d+)?)\s*(k|nghin|ngan|tr|trieu|m)?", t)
    if m:
        n = float(m.group(1).replace(",", "."))
        unit = m.group(2)
        n *= 1_000_000 if unit in ("tr", "trieu", "m") else 1000 if unit in ("k", "nghin", "ngan") or n < 10000 else 1
        out["max_price"] = n
    m = re.search(r"(\d+)\s*(?:nguoi|khach|mau)", t)
    if m:
        out["capacity"] = int(m.group(1))
    for city in cities:
        if _fold(city) in t:
            out["city"] = city
            break
    return out


def ask(text: str, limit: int) -> dict:
    with _db_ext() as cur:
        cur.execute("SELECT DISTINCT city FROM dbo.Studios WHERE status = 'APPROVED'")
        cities = [r[0] for r in cur.fetchall()]
        crit = parse_query(text, cities)
        where, params = ["rm.status = 'AVAILABLE'", "s.status = 'APPROVED'"], []
        if crit["room_type"]:
            where.append("rm.room_type = ?"); params.append(crit["room_type"])
        if crit["max_price"]:
            where.append("rm.price_per_hour <= ?"); params.append(crit["max_price"])
        if crit["capacity"]:
            where.append("rm.capacity >= ?"); params.append(crit["capacity"])
        if crit["city"]:
            where.append("s.city = ?"); params.append(crit["city"])
        cur.execute(
            f"SELECT TOP ({int(limit)}) rm.room_id, rm.name AS room_name, rm.room_type, rm.capacity, "
            "rm.price_per_hour, s.studio_id, s.name AS studio_name, s.city, "
            "ISNULL(v.avg_rating, 0) AS avg_rating "
            "FROM dbo.Rooms rm JOIN dbo.Studios s ON s.studio_id = rm.studio_id "
            "LEFT JOIN dbo.vw_StudioRating v ON v.studio_id = s.studio_id "
            "WHERE " + " AND ".join(where) + " ORDER BY ISNULL(v.avg_rating, 0) DESC, rm.price_per_hour", *params)
        rooms = _rows(cur)
    understood = [k for k, v in crit.items() if v]
    return {"query": text, "criteria": crit, "understood": understood, "results": rooms,
            "note": "Tìm theo luật từ khóa, không phải mô hình ngôn ngữ."}
