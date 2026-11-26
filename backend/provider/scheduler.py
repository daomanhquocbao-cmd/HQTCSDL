"""Tối ưu phân bổ tài nguyên trong một ngày (đề tài: "Resource Scheduling and Allocation").

Ba thuật toán thuần Python, không phụ thuộc DB nên dễ kiểm thử:
1. `equipment_load`  : quét sự kiện (sweep line) tìm khung giờ nhu cầu thiết bị vượt số lượng đang có.
2. `assign_units`    : tô màu đồ thị khoảng (greedy theo giờ bắt đầu) gán từng đơn vào một "chiếc" thiết bị cụ thể.
3. `room_gaps` + `best_fit_rooms`: tìm khoảng trống vụn không ai thuê được, và với đơn PENDING gợi ý phòng
   cùng loại khít nhất (best-fit: để lại ít khoảng trống vụn nhất).
"""
from datetime import date, datetime, time, timedelta
from typing import Dict, List, Optional

from provider.analytics import _db_ext, _pick_studio

MIN_USEFUL_GAP = 60  # phút: khoảng trống ngắn hơn mức này coi là "vụn"


def _mins(dt: datetime, day: date) -> int:
    return int((dt - datetime.combine(day, time(0, 0))).total_seconds() // 60)


def equipment_load(items: List[dict], quantity: int) -> List[dict]:
    """items: [{start, end, qty, reservation_id}] (phút). Trả các khung giờ có tổng nhu cầu > quantity."""
    events = []
    for it in items:
        events.append((it["start"], 1, it["qty"]))
        events.append((it["end"], 0, -it["qty"]))  # kết thúc xử lý trước khi bắt đầu ở cùng thời điểm
    events.sort(key=lambda e: (e[0], e[1]))
    out, cur, last = [], 0, None
    for t, _, delta in events:
        if last is not None and t > last and cur > quantity:
            if out and out[-1]["end"] == last and out[-1]["demand"] == cur:
                out[-1]["end"] = t
            else:
                out.append({"start": last, "end": t, "demand": cur, "short_by": cur - quantity})
        cur += delta
        last = t
    return out


def assign_units(items: List[dict], quantity: int) -> dict:
    """Gán mỗi đơn (qty chiếc) vào các chiếc thiết bị 1..quantity còn rảnh. Đơn không gán đủ -> unassigned."""
    free_at = [0] * quantity
    assigned, unassigned = [], []
    for it in sorted(items, key=lambda x: (x["start"], x["end"])):
        picked = []
        # chọn chiếc rảnh muộn nhất nhưng vẫn kịp (best-fit) để dồn lịch
        candidates = sorted((i for i in range(quantity) if free_at[i] <= it["start"]), key=lambda i: -free_at[i])
        if len(candidates) >= it["qty"]:
            picked = candidates[: it["qty"]]
            for i in picked:
                free_at[i] = it["end"]
            assigned.append({"reservation_id": it["reservation_id"], "units": [i + 1 for i in picked]})
        else:
            unassigned.append(it["reservation_id"])
    return {"assigned": assigned, "unassigned": unassigned}


def room_gaps(bookings: List[dict], open_m: int, close_m: int, min_gap: int = MIN_USEFUL_GAP) -> dict:
    """bookings: [{start, end}] của MỘT phòng. Trả các khoảng trống và phần bị lãng phí (< min_gap)."""
    gaps, cursor = [], open_m
    for b in sorted(bookings, key=lambda x: x["start"]):
        if b["start"] > cursor:
            gaps.append((cursor, min(b["start"], close_m)))
        cursor = max(cursor, b["end"])
    if cursor < close_m:
        gaps.append((cursor, close_m))
    gaps = [(s, e) for s, e in gaps if e > s]
    usable = [{"start": s, "end": e, "minutes": e - s} for s, e in gaps if e - s >= min_gap]
    wasted = [{"start": s, "end": e, "minutes": e - s} for s, e in gaps if e - s < min_gap]
    return {"usable": usable, "wasted": wasted, "wasted_minutes": sum(g["minutes"] for g in wasted)}


def _fits(bookings: List[dict], start: int, end: int) -> bool:
    return all(end <= b["start"] or start >= b["end"] for b in bookings)


def best_fit_rooms(booking: dict, rooms: List[dict], by_room: Dict[int, List[dict]], open_m: int, close_m: int) -> List[dict]:
    """Xếp hạng các phòng cùng loại, đủ chỗ, còn trống đúng khung giờ. Điểm thấp = để lại ít khoảng trống vụn."""
    out = []
    for r in rooms:
        if r["room_id"] == booking["room_id"] or r["room_type"] != booking["room_type"]:
            continue
        if r["capacity"] < booking.get("capacity_needed", 1) or r["status"] != "AVAILABLE":
            continue
        existing = by_room.get(r["room_id"], [])
        if not _fits(existing, booking["start"], booking["end"]):
            continue
        after = existing + [{"start": booking["start"], "end": booking["end"]}]
        out.append({"room_id": r["room_id"], "room_name": r["name"],
                    "wasted_minutes_after": room_gaps(after, open_m, close_m)["wasted_minutes"]})
    return sorted(out, key=lambda x: (x["wasted_minutes_after"], x["room_id"]))


def _hhmm(m: int) -> str:
    return f"{m // 60:02d}:{m % 60:02d}"


def _fmt(items: List[dict]) -> List[dict]:
    out = []
    for i in items:
        d = dict(i)
        for k in ("start", "end"):
            if k in d:
                d[k] = _hhmm(d[k])
        out.append(d)
    return out


def optimize_day(user: dict, studio_id: Optional[int], day: date) -> dict:
    with _db_ext() as cur:
        sid = _pick_studio(cur, user, studio_id)
        cur.execute("SELECT open_time, close_time FROM dbo.Studios WHERE studio_id = ?", sid)
        st = cur.fetchone()
        open_m = st.open_time.hour * 60 + st.open_time.minute
        close_m = st.close_time.hour * 60 + st.close_time.minute
        cur.execute("SELECT room_id, name, room_type, capacity, status FROM dbo.Rooms WHERE studio_id = ? "
                    "AND status <> 'INACTIVE'", sid)
        rooms = [dict(zip(("room_id", "name", "room_type", "capacity", "status"), r)) for r in cur.fetchall()]
        d0, d1 = datetime.combine(day, time(0, 0)), datetime.combine(day, time(0, 0)) + timedelta(days=1)
        cur.execute(
            "SELECT r.reservation_id, r.room_id, r.start_time, r.end_time, r.status "
            "FROM dbo.Reservations r JOIN dbo.Rooms rm ON rm.room_id = r.room_id "
            "WHERE rm.studio_id = ? AND r.status IN ('PENDING','CONFIRMED','IN_USE') "
            "AND r.start_time < ? AND r.end_time > ?", sid, d1, d0)
        res = [{"reservation_id": r.reservation_id, "room_id": r.room_id, "status": r.status,
                "start": max(0, _mins(r.start_time, day)), "end": min(1440, _mins(r.end_time, day))}
               for r in cur.fetchall()]
        cur.execute(
            "SELECT re.reservation_id, re.equipment_id, re.quantity, e.name, e.quantity AS stock "
            "FROM dbo.ReservationEquipments re JOIN dbo.Equipment e ON e.equipment_id = re.equipment_id "
            "WHERE e.studio_id = ? AND e.equipment_type = 'REUSABLE' AND re.reservation_id IN ("
            "SELECT r.reservation_id FROM dbo.Reservations r JOIN dbo.Rooms rm ON rm.room_id = r.room_id "
            "WHERE rm.studio_id = ? AND r.status IN ('PENDING','CONFIRMED','IN_USE') "
            "AND r.start_time < ? AND r.end_time > ?)", sid, sid, d1, d0)
        lines = cur.fetchall()
    return build_report(sid, day, open_m, close_m, rooms, res,
                        [{"reservation_id": l.reservation_id, "equipment_id": l.equipment_id, "qty": l.quantity,
                          "name": l.name, "stock": l.stock} for l in lines])


def build_report(studio_id: int, day: date, open_m: int, close_m: int, rooms: List[dict], res: List[dict],
                 eq_lines: List[dict]) -> dict:
    by_id = {r["reservation_id"]: r for r in res}
    by_room: Dict[int, List[dict]] = {}
    for r in res:
        by_room.setdefault(r["room_id"], []).append(r)

    room_out, suggestions, total_wasted = [], [], 0
    for rm in rooms:
        g = room_gaps(by_room.get(rm["room_id"], []), open_m, close_m)
        total_wasted += g["wasted_minutes"]
        room_out.append({"room_id": rm["room_id"], "room_name": rm["name"], "bookings": len(by_room.get(rm["room_id"], [])),
                         "usable_gaps": _fmt(g["usable"]), "wasted_gaps": _fmt(g["wasted"]),
                         "wasted_minutes": g["wasted_minutes"]})
        room_by_id = {x["room_id"]: x for x in rooms}
        for b in by_room.get(rm["room_id"], []):
            if b["status"] != "PENDING":
                continue
            cand = best_fit_rooms({**b, "room_type": rm["room_type"]}, rooms, by_room, open_m, close_m)
            cur_after = g["wasted_minutes"]
            if cand and cand[0]["wasted_minutes_after"] < cur_after:
                suggestions.append({"reservation_id": b["reservation_id"], "from_room": rm["name"],
                                    "suggest_room": cand[0]["room_name"], "start": _hhmm(b["start"]), "end": _hhmm(b["end"]),
                                    "reason": f"Giảm khoảng trống vụn ở phòng hiện tại và phòng mới (còn {cand[0]['wasted_minutes_after']} phút vụn)"})

    equipment, conflicts = {}, []
    for l in eq_lines:
        r = by_id.get(l["reservation_id"])
        if r:
            equipment.setdefault(l["equipment_id"], {"name": l["name"], "stock": l["stock"], "items": []})["items"].append(
                {"reservation_id": l["reservation_id"], "start": r["start"], "end": r["end"], "qty": l["qty"]})
    eq_out = []
    for eid, e in equipment.items():
        over = equipment_load(e["items"], e["stock"])
        plan = assign_units(e["items"], e["stock"])
        if over:
            conflicts.append({"equipment_id": eid, "name": e["name"], "stock": e["stock"], "overloaded": _fmt(over)})
        eq_out.append({"equipment_id": eid, "name": e["name"], "stock": e["stock"], "peak_demand": max((o["demand"] for o in over), default=min(e["stock"], sum(i["qty"] for i in e["items"]))),
                       "assignment": plan["assigned"], "unassigned": plan["unassigned"]})
    return {"studio_id": studio_id, "date": day.isoformat(), "rooms": room_out, "equipment": eq_out,
            "equipment_conflicts": conflicts, "room_move_suggestions": suggestions,
            "summary": {"wasted_minutes": total_wasted, "conflicts": len(conflicts), "suggestions": len(suggestions),
                        "note": "Khoảng trống < 60 phút coi là vụn. Gợi ý chỉ mang tính tham khảo, provider tự quyết định."}}
