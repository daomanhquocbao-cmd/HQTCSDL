"""AI cho khách hàng: gợi ý phòng (sp_RecommendRooms) và tìm phòng bằng câu hỏi tự nhiên.

Đây là heuristic / luật, không gọi mô hình ngôn ngữ ngoài: điểm gợi ý tính trong SQL từ đánh giá,
độ phổ biến, lịch sử khách và mức giá; "hỏi AI" tách từ khóa (loại phòng, ngân sách, số người, thành phố).
"""
import re
import unicodedata
from typing import List, Optional

from community.service import search_knowledge
from core.platform_settings import get_setting, require_enabled
from provider.analytics import _db_ext
from provider.service import _err, _rows

# Gợi ý thiết bị mặc định theo loại phòng khi studio chưa có lịch sử thuê
TYPICAL_CATEGORIES = {"STUDIO": ("CAMERA", "LENS", "LIGHTING", "TRIPOD"),
                      "DARKROOM": ("ENLARGER", "CHEMICAL", "PAPER")}


def recommend(customer_id: Optional[int], top: int) -> List[dict]:
    require_enabled("ai.recommendations.enabled", "Gợi ý cá nhân hóa đang được quản trị viên tạm tắt")
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
    require_enabled("ai.assistant.enabled", "Trợ lý AI đang được quản trị viên tạm tắt")
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
    knowledge = []
    if get_setting("ai.knowledge_search.enabled"):
        try:
            knowledge = search_knowledge(text, 3)       # trả lời kiến thức nhiếp ảnh từ bài viết cộng đồng
        except Exception:
            knowledge = []
    return {"query": text, "criteria": crit, "understood": understood, "results": rooms if understood else [],
            "knowledge": knowledge,
            "note": "Trợ lý chạy theo luật từ khóa + tìm kiếm trong kho bài viết cộng đồng, không phải mô hình ngôn ngữ lớn."}


def suggest_for_room(room_id: int, limit: int = 5) -> dict:
    """Gợi ý thiết bị và gói dịch vụ nên thêm khi đặt một phòng (dựa trên các đơn trước của cùng loại phòng)."""
    require_enabled("ai.recommendations.enabled", "Gợi ý cá nhân hóa đang được quản trị viên tạm tắt")
    with _db_ext() as cur:
        cur.execute("SELECT studio_id, room_type FROM dbo.Rooms WHERE room_id = ?", room_id)
        room = cur.fetchone()
        if room is None:
            raise _err(404, "Không tìm thấy phòng")
        cur.execute(
            f"SELECT TOP ({int(limit)}) e.equipment_id, e.name, e.category, e.rental_price, "
            "COUNT(DISTINCT re.reservation_id) AS times_rented FROM dbo.ReservationEquipments re "
            "JOIN dbo.Reservations r ON r.reservation_id = re.reservation_id "
            "JOIN dbo.Rooms rm ON rm.room_id = r.room_id JOIN dbo.Equipment e ON e.equipment_id = re.equipment_id "
            "WHERE rm.studio_id = ? AND rm.room_type = ? AND r.status <> 'CANCELLED' "
            "AND e.status IN ('GOOD', 'NEEDS_MAINTENANCE') GROUP BY e.equipment_id, e.name, e.category, e.rental_price "
            "ORDER BY times_rented DESC, e.rental_price", room.studio_id, room.room_type)
        equipment = _rows(cur)
        for e in equipment:
            e["reason"] = f"{e['times_rented']} khách đặt loại phòng này đã thuê kèm"
        if not equipment:
            cats = TYPICAL_CATEGORIES.get(room.room_type, ())
            if cats:
                marks = ",".join("?" * len(cats))
                cur.execute(f"SELECT TOP ({int(limit)}) equipment_id, name, category, rental_price FROM dbo.Equipment "
                            f"WHERE studio_id = ? AND category IN ({marks}) AND status = 'GOOD' "
                            "ORDER BY category, rental_price", room.studio_id, *cats)
                equipment = _rows(cur)
                for e in equipment:
                    e["times_rented"] = 0
                    e["reason"] = "Thiết bị thường dùng cho loại phòng này (chưa đủ lịch sử thuê)"
        cur.execute(
            "SELECT TOP 3 sp.package_id, sp.name, sp.price, sp.duration_hours, COUNT(rp.reservation_id) AS times_chosen "
            "FROM dbo.ServicePackages sp LEFT JOIN dbo.ReservationPackages rp ON rp.package_id = sp.package_id "
            "WHERE sp.studio_id = ? AND sp.is_active = 1 AND (sp.room_type IS NULL OR sp.room_type = ?) "
            "GROUP BY sp.package_id, sp.name, sp.price, sp.duration_hours "
            "ORDER BY times_chosen DESC, sp.price", room.studio_id, room.room_type)
        packages = _rows(cur)
        for p in packages:
            p["reason"] = (f"{p['times_chosen']} đơn đã chọn gói này" if p["times_chosen"]
                           else "Gói phù hợp loại phòng này")
    return {"room_id": room_id, "equipment": equipment, "packages": packages,
            "note": "Gợi ý theo tần suất thuê của các đơn trước (không phải mô hình học máy)."}
