"""Phân tích vận hành, giá, khuyến mãi và AI cho Provider.

- Tỉ lệ lấp đầy phòng, bản đồ nhiệt theo thứ x giờ, hiệu suất thiết bị: truy vấn tổng hợp trong SQL,
  phần tính phần trăm và nhận xét làm bằng Python (dễ kiểm thử).
- Quy tắc giá, khuyến mãi: bảng PricingRules / Promotions (database/07_pricing_promotions_ai.sql).
- AI: dự báo nhu cầu (sp_ForecastDemand) và gợi ý điều chỉnh giá. Cả hai chạy trên dữ liệu đặt phòng
  của chính studio, không gọi dịch vụ ngoài. Mô hình đơn giản, cần đủ lịch sử mới đáng tin.
"""
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from math import ceil
from typing import Dict, List, Optional

from fastapi import HTTPException

from provider.service import (_assert_studio, _db, _dump, _err, _new_id, _one, _rows, _scope,
                              _update)

WEEKDAYS = ["Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy", "Chủ Nhật"]
ACTIVE_BOOKING = "('CONFIRMED','IN_USE','COMPLETED')"
MISSING_MIGRATION = ("Chưa có bảng/thủ tục mới trong CSDL. Hãy chạy database/07_pricing_promotions_ai.sql "
                     "(sau 01, 02, 03) rồi thử lại.")


@contextmanager
def _db_ext():
    """Như _db() nhưng báo 503 rõ ràng khi chưa chạy file SQL 07."""
    try:
        with _db() as cur:
            yield cur
    except HTTPException as exc:
        low = str(exc.detail).lower()
        if "invalid object name" in low or "could not find stored procedure" in low or "invalid column name" in low:
            raise HTTPException(status_code=503, detail=MISSING_MIGRATION) from exc
        raise


def _pct(part: float, whole: float) -> float:
    return round(min(100.0, part / whole * 100.0), 1) if whole > 0 else 0.0


def _studio_filter(user: dict, studio_id: Optional[int], column: str = "s.provider_id",
                   studio_col: str = "s.studio_id"):
    clause, params = _scope(user, column)
    if studio_id:
        clause += f" AND {studio_col} = ?"
        params.append(studio_id)
    return clause, params


def _minutes(value) -> int:
    """'08:30' hoặc đối tượng time -> số phút từ 0h."""
    text = value if isinstance(value, str) else value.strftime("%H:%M")
    h, m = text.split(":")[:2]
    return int(h) * 60 + int(m)


def _count_weekdays(days: int, today: Optional[date] = None) -> List[int]:
    """Số ngày của mỗi thứ (0 = Thứ Hai) trong `days` ngày liền trước hôm nay."""
    today = today or date.today()
    counts = [0] * 7
    for i in range(1, days + 1):
        counts[(today - timedelta(days=i)).weekday()] += 1
    return counts


# ------------------------------------------------------------ tỉ lệ lấp đầy
def occupancy(user: dict, days: int, studio_id: Optional[int]) -> dict:
    """Mỗi phòng: giờ đã dùng / giờ mở cửa trong `days` ngày qua (chỉ đơn CONFIRMED, IN_USE, COMPLETED đã bắt đầu)."""
    with _db_ext() as cur:
        clause, params = _studio_filter(user, studio_id)
        cur.execute(
            "SELECT rm.room_id, rm.name AS room_name, rm.status AS room_status, s.studio_id, s.name AS studio_name, "
            "DATEDIFF(MINUTE, s.open_time, s.close_time) AS open_minutes, "
            "ISNULL(SUM(DATEDIFF(MINUTE, r.start_time, r.end_time)), 0) AS booked_minutes, "
            "COUNT(r.reservation_id) AS bookings "
            "FROM dbo.Rooms rm JOIN dbo.Studios s ON s.studio_id = rm.studio_id "
            "LEFT JOIN dbo.Reservations r ON r.room_id = rm.room_id "
            f"AND r.status IN {ACTIVE_BOOKING} AND r.start_time >= DATEADD(DAY, -?, GETDATE()) "
            "AND r.start_time < GETDATE() "
            "WHERE rm.status <> 'INACTIVE'" + clause +
            " GROUP BY rm.room_id, rm.name, rm.status, s.studio_id, s.name, s.open_time, s.close_time "
            "ORDER BY s.studio_id, rm.room_id", days, *params)
        rooms = _rows(cur)

    booked_total = available_total = 0.0
    for r in rooms:
        r["booked_hours"] = round(r["booked_minutes"] / 60.0, 1)
        r["available_hours"] = round(days * r["open_minutes"] / 60.0, 1)
        r["occupancy_pct"] = _pct(r["booked_minutes"], days * r["open_minutes"])
        booked_total += r["booked_minutes"]
        available_total += days * r["open_minutes"]
        del r["booked_minutes"], r["open_minutes"]
    return {
        "days": days,
        "rooms": rooms,
        "summary": {"booked_hours": round(booked_total / 60.0, 1),
                    "available_hours": round(available_total / 60.0, 1),
                    "occupancy_pct": _pct(booked_total, available_total)},
    }


# ------------------------------------------------ bản đồ nhiệt thứ x giờ
HOURS = "(VALUES " + ",".join(f"({h})" for h in range(24)) + ") h(h)"


def _hourly_rows(cur, user: dict, studio_id: Optional[int], days: int) -> List[dict]:
    clause, params = _studio_filter(user, studio_id)
    cur.execute(
        "SELECT DATEDIFF(DAY, 0, r.start_time) % 7 AS weekday_index, h.h AS hour, "
        "SUM((CASE WHEN t.em < (h.h + 1) * 60 THEN t.em ELSE (h.h + 1) * 60 END) "
        "  - (CASE WHEN t.sm > h.h * 60 THEN t.sm ELSE h.h * 60 END)) AS booked_minutes "
        "FROM dbo.Reservations r JOIN dbo.Rooms rm ON rm.room_id = r.room_id "
        "JOIN dbo.Studios s ON s.studio_id = rm.studio_id "
        "CROSS APPLY (SELECT DATEPART(HOUR, r.start_time) * 60 + DATEPART(MINUTE, r.start_time) AS sm, "
        "                    DATEPART(HOUR, r.end_time) * 60 + DATEPART(MINUTE, r.end_time) AS em) t "
        f"CROSS JOIN {HOURS} "
        f"WHERE r.status IN {ACTIVE_BOOKING} "
        "AND r.start_time >= DATEADD(DAY, -?, CAST(GETDATE() AS DATE)) AND r.start_time < CAST(GETDATE() AS DATE) "
        "AND t.em > h.h * 60 AND t.sm < (h.h + 1) * 60" + clause +
        " GROUP BY DATEDIFF(DAY, 0, r.start_time) % 7, h.h", days, *params)
    booked = _rows(cur)

    clause, params = _studio_filter(user, studio_id)
    cur.execute(
        "SELECT s.studio_id, s.open_time, s.close_time, "
        "(SELECT COUNT(*) FROM dbo.Rooms rm WHERE rm.studio_id = s.studio_id AND rm.status = 'AVAILABLE') AS room_count "
        "FROM dbo.Studios s WHERE s.status = 'APPROVED'" + clause, *params)
    studios = _rows(cur)
    return _grid(booked, studios, days)


def _grid(booked: List[dict], studios: List[dict], days: int, today: Optional[date] = None) -> List[dict]:
    """Ghép số phút đã đặt với số phút có thể bán trong từng ô (thứ, giờ)."""
    per_weekday = _count_weekdays(days, today)
    avail: Dict[tuple, float] = {}
    for st in studios:
        o, c, rooms = _minutes(st["open_time"]), _minutes(st["close_time"]), st["room_count"]
        for wd in range(7):
            for h in range(24):
                overlap = max(0, min(c, (h + 1) * 60) - max(o, h * 60))
                if overlap:
                    avail[(wd, h)] = avail.get((wd, h), 0) + overlap * rooms * per_weekday[wd]
    got = {(b["weekday_index"], b["hour"]): b["booked_minutes"] for b in booked}
    cells = []
    for (wd, h), minutes in sorted(avail.items()):
        if minutes <= 0:
            continue
        b = got.get((wd, h), 0)
        cells.append({"weekday_index": wd, "weekday": WEEKDAYS[wd], "hour": h,
                      "booked_hours": round(b / 60.0, 2), "available_hours": round(minutes / 60.0, 1),
                      "occupancy_pct": _pct(b, minutes)})
    return cells


def heatmap(user: dict, days: int, studio_id: Optional[int]) -> dict:
    with _db_ext() as cur:
        return {"days": days, "cells": _hourly_rows(cur, user, studio_id, days)}


# ------------------------------------------------------ hiệu suất thiết bị
def _equipment_alerts(e: dict, days: int, today: Optional[date] = None) -> List[str]:
    today = today or date.today()
    alerts = []
    if e["status"] in ("BROKEN", "NEEDS_MAINTENANCE", "UNDER_MAINTENANCE"):
        alerts.append({"BROKEN": "Đang hỏng", "NEEDS_MAINTENANCE": "Cần bảo trì",
                       "UNDER_MAINTENANCE": "Đang bảo trì"}[e["status"]])
    nxt = e.get("next_maintenance_date")
    if nxt:
        nxt_date = nxt if isinstance(nxt, date) and not isinstance(nxt, datetime) else datetime.fromisoformat(str(nxt)[:10]).date()
        left = (nxt_date - today).days
        e["maintenance_in_days"] = left
        if left < 0:
            alerts.append("Quá hạn bảo trì")
        elif left <= 14:
            alerts.append("Sắp đến hạn bảo trì")
    else:
        e["maintenance_in_days"] = None
    if e["equipment_type"] == "CONSUMABLE" and e["quantity"] < 10:
        alerts.append("Vật tư sắp hết")
    util = e.get("utilization_pct")
    if util is not None and days >= 30:
        if util >= 85:
            alerts.append("Dùng rất nhiều - cân nhắc mua thêm")
        elif util < 10 and e["status"] == "GOOD":
            alerts.append("Ít được thuê")
    return alerts


def equipment_utilization(user: dict, days: int, studio_id: Optional[int]) -> dict:
    """Hiệu suất = số đơn-vị-giờ thiết bị được thuê / (số lượng x giờ mở cửa) trong `days` ngày qua."""
    with _db_ext() as cur:
        clause, params = _studio_filter(user, studio_id)
        window = (f"r.status IN {ACTIVE_BOOKING} AND r.start_time >= DATEADD(DAY, -?, GETDATE()) "
                  "AND r.start_time < GETDATE()")
        cur.execute(
            "SELECT e.equipment_id, e.name, e.category, e.equipment_type, e.quantity, e.status, e.rental_price, "
            "e.next_maintenance_date, s.studio_id, s.name AS studio_name, "
            "DATEDIFF(MINUTE, s.open_time, s.close_time) AS open_minutes, "
            "ISNULL(u.rentals, 0) AS rentals, ISNULL(u.units, 0) AS units, ISNULL(u.unit_minutes, 0) AS unit_minutes, "
            "ISNULL(u.revenue, 0) AS rental_revenue, "
            "ISNULL(m.cnt, 0) AS maintenance_count, ISNULL(m.cost, 0) AS maintenance_cost "
            "FROM dbo.Equipment e JOIN dbo.Studios s ON s.studio_id = e.studio_id "
            "LEFT JOIN (SELECT x.equipment_id, COUNT(*) AS rentals, SUM(x.q) AS units, "
            "                  SUM(x.q * x.mins) AS unit_minutes, SUM(x.rev) AS revenue FROM ("
            "    SELECT re.equipment_id, re.quantity AS q, DATEDIFF(MINUTE, r.start_time, r.end_time) AS mins, "
            "           re.quantity * re.unit_price AS rev "
            "    FROM dbo.ReservationEquipments re JOIN dbo.Reservations r ON r.reservation_id = re.reservation_id "
            f"    WHERE {window} "
            "    UNION ALL "
            "    SELECT pe.equipment_id, pe.quantity_included, DATEDIFF(MINUTE, r.start_time, r.end_time), 0 "
            "    FROM dbo.ReservationPackages rp JOIN dbo.PackageEquipment pe ON pe.package_id = rp.package_id "
            "    JOIN dbo.Reservations r ON r.reservation_id = rp.reservation_id "
            f"    WHERE {window}) x GROUP BY x.equipment_id) u ON u.equipment_id = e.equipment_id "
            "LEFT JOIN (SELECT equipment_id, COUNT(*) AS cnt, SUM(cost) AS cost FROM dbo.EquipmentMaintenance "
            "           WHERE status = 'DONE' AND maintenance_date >= DATEADD(DAY, -?, GETDATE()) "
            "           GROUP BY equipment_id) m ON m.equipment_id = e.equipment_id "
            "WHERE e.status <> 'RETIRED'" + clause + " ORDER BY s.studio_id, e.category, e.equipment_id",
            days, days, days, *params)
        items = _rows(cur)

    for e in items:
        if e["equipment_type"] == "REUSABLE":
            e["utilization_pct"] = _pct(e["unit_minutes"], e["quantity"] * days * e["open_minutes"])
        else:
            e["utilization_pct"] = None          # vật tư tiêu hao: xem số lượng đã dùng
        e["unit_hours"] = round(e["unit_minutes"] / 60.0, 1)
        e["alerts"] = _equipment_alerts(e, days)
        del e["unit_minutes"], e["open_minutes"]
    reusable = [e for e in items if e["utilization_pct"] is not None]
    return {
        "days": days,
        "items": items,
        "summary": {
            "equipment_count": len(items),
            "avg_utilization_pct": round(sum(e["utilization_pct"] for e in reusable) / len(reusable), 1) if reusable else None,
            "with_alerts": sum(1 for e in items if e["alerts"]),
            "rental_revenue": round(sum(e["rental_revenue"] for e in items), 0),
            "maintenance_cost": round(sum(e["maintenance_cost"] for e in items), 0),
        },
    }


# ----------------------------------------------------------- AI: dự báo
def _pick_studio(cur, user: dict, studio_id: Optional[int]) -> int:
    if studio_id:
        _assert_studio(cur, user, studio_id)
        return studio_id
    clause, params = _scope(user, "s.provider_id")
    cur.execute("SELECT TOP 1 s.studio_id FROM dbo.Studios s WHERE 1 = 1" + clause + " ORDER BY s.studio_id", *params)
    row = cur.fetchone()
    if row is None:
        raise _err(404, "Bạn chưa có cơ sở nào")
    return row.studio_id


def level_of(value: float, mean: float) -> str:
    if mean <= 0:
        return "NORMAL"
    ratio = value / mean
    return "HIGH" if ratio >= 1.25 else "LOW" if ratio <= 0.6 else "NORMAL"


def forecast(user: dict, studio_id: Optional[int], horizon: int, lookback: int) -> dict:
    with _db_ext() as cur:
        sid = _pick_studio(cur, user, studio_id)
        cur.execute("EXEC dbo.sp_ForecastDemand @studio_id = ?, @horizon_days = ?, @lookback_days = ?",
                    sid, horizon, lookback)
        rows = _rows(cur)
    mean = sum(r["expected_bookings"] for r in rows) / len(rows) if rows else 0
    for r in rows:
        r["weekday"] = WEEKDAYS[r["weekday_index"]]
        r["level"] = level_of(r["expected_bookings"], mean)
    sample = max((r["sample_days"] for r in rows), default=0)
    return {
        "studio_id": sid, "horizon_days": horizon, "lookback_days": lookback,
        "method": "Trung bình số đơn của cùng thứ trong lịch sử (mô hình nền, không dùng dịch vụ AI ngoài).",
        "reliable": sample >= 4 and any(r["expected_bookings"] > 0 for r in rows),
        "forecast": rows,
    }


# ------------------------------------------------- AI: gợi ý điều chỉnh giá
BANDS = [("Sáng", 0, 12), ("Chiều", 12, 17), ("Tối", 17, 24)]


def build_pricing_suggestions(cells: List[dict], studio_open: int, studio_close: int,
                              rules: List[dict]) -> List[dict]:
    """Gộp ô (thứ, giờ) thành khung giờ x loại ngày rồi gợi ý hệ số giá theo mức lấp đầy."""
    out = []
    for day_type, wds in (("WEEKDAY", range(0, 5)), ("WEEKEND", range(5, 7))):
        for label, b_start, b_end in BANDS:
            start_h = max(b_start, studio_open // 60)
            end_h = min(b_end, ceil(studio_close / 60))
            if start_h >= end_h:
                continue
            sel = [c for c in cells if c["weekday_index"] in wds and start_h <= c["hour"] < end_h]
            booked = sum(c["booked_hours"] for c in sel)
            avail = sum(c["available_hours"] for c in sel)
            if avail <= 0:
                continue
            occ = _pct(booked, avail)
            if occ >= 75:
                mult, why = 1.15, "Lấp đầy rất cao, có thể tăng giá để tối ưu doanh thu."
            elif occ >= 60:
                mult, why = 1.08, "Lấp đầy cao, có thể tăng nhẹ giá."
            elif occ <= 20:
                mult, why = 0.90, "Lấp đầy thấp, giảm giá để kích cầu."
            else:
                continue
            has_rule = any(r["status"] == "ACTIVE" and r["day_type"] in ("ALL", day_type)
                           and r["start_hour"] < end_h and r["end_hour"] > start_h for r in rules)
            out.append({"day_type": day_type, "band": label, "start_hour": start_h, "end_hour": end_h,
                        "occupancy_pct": occ, "suggested_multiplier": mult, "reason": why,
                        "already_has_rule": has_rule})
    return out


def pricing_suggestions(user: dict, studio_id: Optional[int], days: int) -> dict:
    with _db_ext() as cur:
        sid = _pick_studio(cur, user, studio_id)
        cells = _hourly_rows(cur, user, sid, days)
        cur.execute("SELECT open_time, close_time FROM dbo.Studios WHERE studio_id = ?", sid)
        st = cur.fetchone()
        cur.execute("SELECT rule_id, room_id, day_type, start_hour, end_hour, multiplier, status "
                    "FROM dbo.PricingRules WHERE studio_id = ?", sid)
        rules = _rows(cur)
    total_booked = sum(c["booked_hours"] for c in cells)
    enough = total_booked >= 5
    return {
        "studio_id": sid, "days": days,
        "method": "So sánh mức lấp đầy theo khung giờ và loại ngày: >= 75% gợi ý tăng 15%, >= 60% tăng 8%, <= 20% giảm 10%.",
        "insufficient_data": not enough,
        "suggestions": build_pricing_suggestions(cells, _minutes(st.open_time), _minutes(st.close_time), rules) if enough else [],
    }


# ------------------------------------------------------------ quy tắc giá
RULE_SELECT = ("SELECT pr.rule_id, pr.studio_id, s.name AS studio_name, pr.room_id, rm.name AS room_name, "
               "pr.name, pr.day_type, pr.start_hour, pr.end_hour, pr.multiplier, pr.status, pr.created_at "
               "FROM dbo.PricingRules pr JOIN dbo.Studios s ON s.studio_id = pr.studio_id "
               "LEFT JOIN dbo.Rooms rm ON rm.room_id = pr.room_id WHERE 1 = 1")
RULE_NULLABLE = {"room_id"}


def list_rules(user: dict, studio_id: Optional[int]) -> List[dict]:
    with _db_ext() as cur:
        clause, params = _studio_filter(user, studio_id, studio_col="pr.studio_id")
        cur.execute(RULE_SELECT + clause + " ORDER BY pr.studio_id, pr.rule_id", *params)
        return _rows(cur)


def _assert_room_in_studio(cur, studio_id: int, room_id: Optional[int]) -> None:
    if room_id is None:
        return
    cur.execute("SELECT studio_id FROM dbo.Rooms WHERE room_id = ?", room_id)
    row = cur.fetchone()
    if row is None or row.studio_id != studio_id:
        raise _err(400, "Phòng không thuộc cơ sở đã chọn")


def create_rule(user: dict, data) -> dict:
    with _db_ext() as cur:
        _assert_studio(cur, user, data.studio_id)
        _assert_room_in_studio(cur, data.studio_id, data.room_id)
        cur.execute("INSERT INTO dbo.PricingRules (studio_id, room_id, name, day_type, start_hour, end_hour, "
                    "multiplier, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    data.studio_id, data.room_id, data.name, data.day_type, data.start_hour,
                    data.end_hour, data.multiplier, data.status)
        rule_id = _new_id(cur)
        cur.execute(RULE_SELECT + " AND pr.rule_id = ?", rule_id)
        return _one(cur)


def _rule_owner(cur, user: dict, rule_id: int) -> dict:
    cur.execute("SELECT studio_id, room_id, start_hour, end_hour FROM dbo.PricingRules WHERE rule_id = ?", rule_id)
    row = cur.fetchone()
    if row is None:
        raise _err(404, "Không tìm thấy quy tắc giá")
    _assert_studio(cur, user, row.studio_id)
    return {"studio_id": row.studio_id, "room_id": row.room_id,
            "start_hour": row.start_hour, "end_hour": row.end_hour}


def update_rule(user: dict, rule_id: int, data) -> dict:
    fields = _dump(data, RULE_NULLABLE)
    with _db_ext() as cur:
        cur_rule = _rule_owner(cur, user, rule_id)
        if "room_id" in fields:
            _assert_room_in_studio(cur, cur_rule["studio_id"], fields["room_id"])
        start = fields.get("start_hour", cur_rule["start_hour"])
        end = fields.get("end_hour", cur_rule["end_hour"])
        if end <= start:
            raise _err(400, "Giờ kết thúc phải lớn hơn giờ bắt đầu")
        _update(cur, "PricingRules", "rule_id", rule_id, fields)
        cur.execute(RULE_SELECT + " AND pr.rule_id = ?", rule_id)
        return _one(cur)


def delete_rule(user: dict, rule_id: int) -> None:
    with _db_ext() as cur:
        _rule_owner(cur, user, rule_id)
        cur.execute("DELETE FROM dbo.PricingRules WHERE rule_id = ?", rule_id)


# ------------------------------------------------------------- khuyến mãi
PROMO_SELECT = ("SELECT p.promo_id, p.studio_id, s.name AS studio_name, p.code, p.title, p.discount_type, "
                "p.discount_value, p.max_discount, p.min_order_amount, p.start_date, p.end_date, p.max_uses, "
                "p.used_count, p.status, p.created_at, "
                "CASE WHEN p.status <> 'ACTIVE' THEN 'INACTIVE' "
                "     WHEN CAST(GETDATE() AS DATE) < p.start_date THEN 'UPCOMING' "
                "     WHEN CAST(GETDATE() AS DATE) > p.end_date THEN 'EXPIRED' "
                "     WHEN p.max_uses IS NOT NULL AND p.used_count >= p.max_uses THEN 'USED_UP' "
                "     ELSE 'RUNNING' END AS state "
                "FROM dbo.Promotions p JOIN dbo.Studios s ON s.studio_id = p.studio_id WHERE 1 = 1")
PROMO_NULLABLE = {"max_discount", "max_uses"}


def list_promotions(user: dict, studio_id: Optional[int]) -> List[dict]:
    with _db_ext() as cur:
        clause, params = _studio_filter(user, studio_id, studio_col="p.studio_id")
        cur.execute(PROMO_SELECT + clause + " ORDER BY p.studio_id, p.promo_id DESC", *params)
        rows = _rows(cur)
    for r in rows:
        for k in ("start_date", "end_date"):
            r[k] = str(r[k])[:10]
    return rows


def create_promotion(user: dict, data) -> dict:
    with _db_ext() as cur:
        _assert_studio(cur, user, data.studio_id)
        cur.execute("SELECT COUNT(*) FROM dbo.Promotions WHERE studio_id = ? AND code = ?", data.studio_id, data.code)
        if cur.fetchone()[0]:
            raise _err(409, f"Mã {data.code} đã tồn tại ở cơ sở này")
        cur.execute("INSERT INTO dbo.Promotions (studio_id, code, title, discount_type, discount_value, "
                    "max_discount, min_order_amount, start_date, end_date, max_uses, status) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    data.studio_id, data.code, data.title, data.discount_type, data.discount_value,
                    data.max_discount, data.min_order_amount, data.start_date, data.end_date,
                    data.max_uses, data.status)
        promo_id = _new_id(cur)
        cur.execute(PROMO_SELECT + " AND p.promo_id = ?", promo_id)
        row = _one(cur)
    for k in ("start_date", "end_date"):
        row[k] = str(row[k])[:10]
    return row


def _promo_owner(cur, user: dict, promo_id: int) -> dict:
    cur.execute("SELECT studio_id, discount_type, discount_value, start_date, end_date, used_count "
                "FROM dbo.Promotions WHERE promo_id = ?", promo_id)
    row = cur.fetchone()
    if row is None:
        raise _err(404, "Không tìm thấy khuyến mãi")
    _assert_studio(cur, user, row.studio_id)
    return {"discount_type": row.discount_type, "discount_value": float(row.discount_value),
            "start_date": str(row.start_date)[:10], "end_date": str(row.end_date)[:10],
            "used_count": row.used_count}


def update_promotion(user: dict, promo_id: int, data) -> dict:
    fields = _dump(data, PROMO_NULLABLE)
    with _db_ext() as cur:
        now = _promo_owner(cur, user, promo_id)
        merged = {**now, **{k: (str(v)[:10] if k.endswith("_date") else v) for k, v in fields.items()}}
        if merged["end_date"] < merged["start_date"]:
            raise _err(400, "Ngày kết thúc phải sau hoặc bằng ngày bắt đầu")
        if merged["discount_type"] == "PERCENT" and merged["discount_value"] > 100:
            raise _err(400, "Giảm theo % không được vượt 100")
        if fields.get("max_uses") is not None and fields["max_uses"] < now["used_count"]:
            raise _err(400, f"Số lượt tối đa không được nhỏ hơn số lượt đã dùng ({now['used_count']})")
        _update(cur, "Promotions", "promo_id", promo_id, fields)
        cur.execute(PROMO_SELECT + " AND p.promo_id = ?", promo_id)
        row = _one(cur)
    for k in ("start_date", "end_date"):
        row[k] = str(row[k])[:10]
    return row


def delete_promotion(user: dict, promo_id: int) -> None:
    with _db_ext() as cur:
        now = _promo_owner(cur, user, promo_id)
        if now["used_count"]:
            raise _err(409, "Mã đã được dùng nên không thể xóa. Hãy chuyển sang tạm ngưng.")
        cur.execute("DELETE FROM dbo.Promotions WHERE promo_id = ?", promo_id)
