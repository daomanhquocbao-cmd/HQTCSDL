from datetime import date

from provider import scheduler as s


def test_equipment_overload_detected():
    items = [{"reservation_id": 1, "start": 600, "end": 720, "qty": 1},
             {"reservation_id": 2, "start": 660, "end": 780, "qty": 1}]
    over = s.equipment_load(items, 1)
    assert over == [{"start": 660, "end": 720, "demand": 2, "short_by": 1}]
    assert s.equipment_load(items, 2) == []


def test_back_to_back_is_not_conflict():
    items = [{"reservation_id": 1, "start": 600, "end": 660, "qty": 1},
             {"reservation_id": 2, "start": 660, "end": 720, "qty": 1}]
    assert s.equipment_load(items, 1) == []


def test_assign_units_reuses_and_reports_unassigned():
    items = [{"reservation_id": 1, "start": 600, "end": 660, "qty": 1},
             {"reservation_id": 2, "start": 600, "end": 660, "qty": 1},
             {"reservation_id": 3, "start": 630, "end": 700, "qty": 1}]
    out = s.assign_units(items, 2)
    assert out["unassigned"] == [3]
    assert {a["reservation_id"] for a in out["assigned"]} == {1, 2}
    out = s.assign_units(items[:1] + [{"reservation_id": 4, "start": 660, "end": 720, "qty": 1}], 1)
    assert out["unassigned"] == [] and out["assigned"][1]["units"] == [1]


def test_room_gaps_marks_wasted():
    g = s.room_gaps([{"start": 540, "end": 600}, {"start": 630, "end": 700}], 480, 900)
    assert [x["minutes"] for x in g["wasted"]] == [30]
    assert [(x["start"], x["end"]) for x in g["usable"]] == [(480, 540), (700, 900)]


def test_best_fit_prefers_fewer_wasted():
    rooms = [{"room_id": 1, "name": "A", "room_type": "STUDIO", "capacity": 4, "status": "AVAILABLE"},
             {"room_id": 2, "name": "B", "room_type": "STUDIO", "capacity": 4, "status": "AVAILABLE"},
             {"room_id": 3, "name": "C", "room_type": "DARKROOM", "capacity": 4, "status": "AVAILABLE"}]
    by_room = {2: [{"start": 480, "end": 600}]}
    b = {"room_id": 1, "room_type": "STUDIO", "start": 600, "end": 720}
    out = s.best_fit_rooms(b, rooms, by_room, 480, 900)
    assert [r["room_id"] for r in out] == [2]


def test_build_report_suggests_move_and_conflict():
    rooms = [{"room_id": 1, "name": "A", "room_type": "STUDIO", "capacity": 4, "status": "AVAILABLE"},
             {"room_id": 2, "name": "B", "room_type": "STUDIO", "capacity": 4, "status": "AVAILABLE"}]
    res = [{"reservation_id": 1, "room_id": 1, "status": "CONFIRMED", "start": 480, "end": 570},
           {"reservation_id": 2, "room_id": 1, "status": "PENDING", "start": 600, "end": 660},
           {"reservation_id": 3, "room_id": 2, "status": "CONFIRMED", "start": 480, "end": 600}]
    lines = [{"reservation_id": 1, "equipment_id": 9, "qty": 1, "name": "Đèn", "stock": 1},
             {"reservation_id": 2, "equipment_id": 9, "qty": 1, "name": "Đèn", "stock": 1}]
    rep = s.build_report(1, date(2026, 11, 25), 480, 900, rooms, res, lines)
    assert rep["room_move_suggestions"][0]["suggest_room"] == "B"
    assert rep["equipment_conflicts"] == []  # 480-570 và 600-660 không chồng nhau
    lines[1]["reservation_id"] = 3
    res[2]["start"], res[2]["end"] = 500, 580
    rep = s.build_report(1, date(2026, 11, 25), 480, 900, rooms, res, lines)
    assert rep["equipment_conflicts"][0]["name"] == "Đèn"
