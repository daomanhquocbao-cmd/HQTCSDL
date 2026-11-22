"""Kiểm tra phần phân tích / giá / khuyến mãi / admin / cộng đồng / AI bằng cursor giả."""
import os
import sys
from datetime import date, time
from decimal import Decimal
from types import SimpleNamespace

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import HTTPException  # noqa: E402
from provider import analytics, service  # noqa: E402
from tests.test_provider_service import ADMIN, OTHER, PROVIDER, FakeConn, FakeCursor, sql_error  # noqa: E402


@pytest.fixture
def db(monkeypatch):
    def install(script):
        conn = FakeConn(FakeCursor(script))
        monkeypatch.setattr(service, "get_db_connection", lambda: conn)
        return conn
    return install


OWN = (r"SELECT provider_id FROM dbo.Studios", ["provider_id"], [(5,)])


# ---- hàm thuần
def test_pct_caps_and_handles_zero():
    assert analytics._pct(30, 120) == 25.0
    assert analytics._pct(200, 100) == 100.0
    assert analytics._pct(5, 0) == 0.0


def test_count_weekdays_over_28_days_is_4_each():
    assert analytics._count_weekdays(28, date(2026, 11, 22)) == [4] * 7


def test_grid_computes_available_and_booked():
    studios = [{"open_time": "08:00", "close_time": "10:00", "room_count": 2}]
    booked = [{"weekday_index": 0, "hour": 8, "booked_minutes": 120}]
    cells = analytics._grid(booked, studios, 28, date(2026, 11, 22))
    mon8 = next(c for c in cells if c["weekday_index"] == 0 and c["hour"] == 8)
    # 2 phòng x 60 phút x 4 thứ Hai = 480 phút = 8 giờ; đã đặt 2 giờ
    assert mon8["available_hours"] == 8.0 and mon8["booked_hours"] == 2.0 and mon8["occupancy_pct"] == 25.0
    assert not any(c["hour"] >= 10 for c in cells)


def test_level_of():
    assert analytics.level_of(10, 5) == "HIGH" and analytics.level_of(2, 5) == "LOW"
    assert analytics.level_of(5, 5) == "NORMAL" and analytics.level_of(1, 0) == "NORMAL"


def test_pricing_suggestions_raise_busy_and_cut_quiet():
    cells = []
    for wd in range(5):
        cells.append({"weekday_index": wd, "hour": 18, "booked_hours": 9, "available_hours": 10})   # tối: 90%
        cells.append({"weekday_index": wd, "hour": 9, "booked_hours": 1, "available_hours": 10})    # sáng: 10%
        cells.append({"weekday_index": wd, "hour": 14, "booked_hours": 4, "available_hours": 10})   # chiều: 40%
    out = analytics.build_pricing_suggestions(cells, 8 * 60, 21 * 60, [])
    by = {(o["day_type"], o["band"]): o for o in out}
    assert by[("WEEKDAY", "Tối")]["suggested_multiplier"] == 1.15
    assert by[("WEEKDAY", "Sáng")]["suggested_multiplier"] == 0.90
    assert ("WEEKDAY", "Chiều") not in by
    assert not any(o["day_type"] == "WEEKEND" for o in out)       # cuối tuần không có dữ liệu


def test_pricing_suggestion_flags_existing_rule():
    cells = [{"weekday_index": 0, "hour": 18, "booked_hours": 9, "available_hours": 10}]
    rules = [{"status": "ACTIVE", "day_type": "ALL", "start_hour": 17, "end_hour": 21}]
    out = analytics.build_pricing_suggestions(cells, 8 * 60, 21 * 60, rules)
    assert out[0]["already_has_rule"] is True


def test_equipment_alerts():
    e = {"status": "NEEDS_MAINTENANCE", "equipment_type": "REUSABLE", "quantity": 2,
         "next_maintenance_date": date(2026, 11, 1), "utilization_pct": 90.0}
    alerts = analytics._equipment_alerts(e, 30, date(2026, 11, 22))
    assert "Cần bảo trì" in alerts and "Quá hạn bảo trì" in alerts and any("mua thêm" in a for a in alerts)
    assert e["maintenance_in_days"] == -21
    idle = {"status": "GOOD", "equipment_type": "REUSABLE", "quantity": 1, "next_maintenance_date": None,
            "utilization_pct": 2.0}
    assert analytics._equipment_alerts(idle, 30, date(2026, 11, 22)) == ["Ít được thuê"]
    chem = {"status": "GOOD", "equipment_type": "CONSUMABLE", "quantity": 3, "next_maintenance_date": None,
            "utilization_pct": None}
    assert analytics._equipment_alerts(chem, 30) == ["Vật tư sắp hết"]


# ---- truy vấn
def test_occupancy_scoped_and_computed(db):
    conn = db([(r"FROM dbo.Rooms rm", ["room_id", "room_name", "room_status", "studio_id", "studio_name",
                                       "open_minutes", "booked_minutes", "bookings"],
                [(1, "A", "AVAILABLE", 1, "S", 600, 1800, 12)])])
    out = analytics.occupancy(PROVIDER, 30, None)
    sql, params = conn.cur.log[0]
    assert "s.provider_id = ?" in sql and params == (30, 5)
    room = out["rooms"][0]
    assert room["booked_hours"] == 30.0 and room["available_hours"] == 300.0 and room["occupancy_pct"] == 10.0
    assert out["summary"]["occupancy_pct"] == 10.0


def test_missing_migration_gives_503(db):
    db([(r"FROM dbo.Rooms rm", None, sql_error("Invalid object name 'dbo.PricingRules'."))])
    with pytest.raises(HTTPException) as e:
        analytics.occupancy(PROVIDER, 30, None)
    assert e.value.status_code == 503 and "07_pricing" in e.value.detail


def test_equipment_utilization_math(db):
    cols = ["equipment_id", "name", "category", "equipment_type", "quantity", "status", "rental_price",
            "next_maintenance_date", "studio_id", "studio_name", "open_minutes", "rentals", "units",
            "unit_minutes", "rental_revenue", "maintenance_count", "maintenance_cost"]
    row = (1, "Đèn", "LIGHTING", "REUSABLE", 2, "GOOD", Decimal("50000"), None, 1, "S", 600, 5, 5, 3600,
           Decimal("250000"), 0, Decimal("0"))
    conn = db([(r"FROM dbo.Equipment e", cols, [row])])
    out = analytics.equipment_utilization(PROVIDER, 30, 1)
    assert conn.cur.log[0][1] == (30, 30, 30, 5, 1)
    item = out["items"][0]
    assert item["utilization_pct"] == 10.0 and item["unit_hours"] == 60.0     # 3600 / (2 x 30 x 600) = 10%
    assert out["summary"]["rental_revenue"] == 250000


# ---- chính sách giá
def rule(**kw):
    base = dict(studio_id=1, room_id=None, name="Cuối tuần", day_type="WEEKEND", start_hour=8, end_hour=21,
                multiplier=1.15, status="ACTIVE")
    base.update(kw)
    return SimpleNamespace(**base)


def test_create_rule_checks_ownership(db):
    conn = db([OWN])
    with pytest.raises(HTTPException) as e:
        analytics.create_rule(OTHER, rule())
    assert e.value.status_code == 403 and not conn.cur.sqls("INSERT INTO dbo.PricingRules")


def test_create_rule_rejects_room_of_other_studio(db):
    conn = db([OWN, (r"SELECT studio_id FROM dbo.Rooms", ["studio_id"], [(2,)])])
    with pytest.raises(HTTPException) as e:
        analytics.create_rule(PROVIDER, rule(room_id=9))
    assert e.value.status_code == 400 and not conn.cur.sqls("INSERT INTO dbo.PricingRules")


def test_create_rule_inserts(db):
    conn = db([OWN, (r"SCOPE_IDENTITY", ["id"], [(4,)]), (r"FROM dbo.PricingRules pr", ["rule_id"], [(4,)])])
    assert analytics.create_rule(PROVIDER, rule()) == {"rule_id": 4}
    sql, params = conn.cur.sqls("INSERT INTO dbo.PricingRules")[0]
    assert params == (1, None, "Cuối tuần", "WEEKEND", 8, 21, 1.15, "ACTIVE") and conn.commits == 1


def test_update_rule_validates_hours_against_current(db):
    from provider.schemas import PricingRulePatch
    db([(r"FROM dbo.PricingRules WHERE rule_id", ["studio_id", "room_id", "start_hour", "end_hour"], [(1, None, 8, 21)]),
        OWN])
    with pytest.raises(HTTPException) as e:
        analytics.update_rule(PROVIDER, 4, PricingRulePatch(end_hour=7))
    assert e.value.status_code == 400


def test_delete_missing_rule_404(db):
    db([(r"FROM dbo.PricingRules WHERE rule_id", ["studio_id"], [])])
    with pytest.raises(HTTPException) as e:
        analytics.delete_rule(PROVIDER, 4)
    assert e.value.status_code == 404


def test_rule_schema_validation():
    from pydantic import ValidationError
    from provider.schemas import PricingRuleIn
    with pytest.raises(ValidationError):
        PricingRuleIn(studio_id=1, name="x", start_hour=10, end_hour=9, multiplier=1.1)
    with pytest.raises(ValidationError):
        PricingRuleIn(studio_id=1, name="x", start_hour=8, end_hour=9, multiplier=5)


# ---- khuyến mãi
def test_promotion_schema_rules():
    from pydantic import ValidationError
    from provider.schemas import PromotionIn
    ok = PromotionIn(studio_id=1, code="welcome10", title="t", discount_type="PERCENT", discount_value=10,
                     start_date=date(2026, 1, 1), end_date=date(2026, 2, 1))
    assert ok.code == "WELCOME10"
    with pytest.raises(ValidationError):
        PromotionIn(studio_id=1, code="ABC", title="t", discount_type="PERCENT", discount_value=150,
                    start_date=date(2026, 1, 1), end_date=date(2026, 2, 1))
    with pytest.raises(ValidationError):
        PromotionIn(studio_id=1, code="ABC", title="t", discount_type="FIXED", discount_value=5,
                    start_date=date(2026, 3, 1), end_date=date(2026, 2, 1))


def promo(**kw):
    base = dict(studio_id=1, code="SALE", title="t", discount_type="FIXED", discount_value=50000,
                max_discount=None, min_order_amount=0, start_date=date(2026, 1, 1), end_date=date(2026, 2, 1),
                max_uses=None, status="ACTIVE")
    base.update(kw)
    return SimpleNamespace(**base)


def test_create_promotion_duplicate_code_409(db):
    conn = db([OWN, (r"SELECT COUNT\(\*\) FROM dbo.Promotions", ["n"], [(1,)])])
    with pytest.raises(HTTPException) as e:
        analytics.create_promotion(PROVIDER, promo())
    assert e.value.status_code == 409 and not conn.cur.sqls("INSERT INTO dbo.Promotions")


def test_create_promotion_inserts(db):
    conn = db([OWN, (r"SELECT COUNT\(\*\) FROM dbo.Promotions", ["n"], [(0,)]),
               (r"SCOPE_IDENTITY", ["id"], [(8,)]),
               (r"FROM dbo.Promotions p", ["promo_id", "start_date", "end_date"], [(8, date(2026, 1, 1), date(2026, 2, 1))])])
    out = analytics.create_promotion(PROVIDER, promo())
    assert out["promo_id"] == 8 and out["start_date"] == "2026-01-01"
    assert conn.cur.sqls("INSERT INTO dbo.Promotions")[0][1][1] == "SALE"


def test_used_promotion_cannot_be_deleted(db):
    conn = db([(r"FROM dbo.Promotions WHERE promo_id",
                ["studio_id", "discount_type", "discount_value", "start_date", "end_date", "used_count"],
                [(1, "FIXED", Decimal("50000"), date(2026, 1, 1), date(2026, 2, 1), 3)]), OWN])
    with pytest.raises(HTTPException) as e:
        analytics.delete_promotion(PROVIDER, 8)
    assert e.value.status_code == 409 and not conn.cur.sqls("DELETE")


def test_max_uses_cannot_drop_below_used(db):
    from provider.schemas import PromotionPatch
    db([(r"FROM dbo.Promotions WHERE promo_id",
         ["studio_id", "discount_type", "discount_value", "start_date", "end_date", "used_count"],
         [(1, "FIXED", Decimal("50000"), date(2026, 1, 1), date(2026, 2, 1), 5)]), OWN])
    with pytest.raises(HTTPException) as e:
        analytics.update_promotion(PROVIDER, 8, PromotionPatch(max_uses=2))
    assert e.value.status_code == 400


# ---- forecast
def test_forecast_labels_levels(db):
    cols = ["forecast_date", "weekday_index", "expected_bookings", "expected_hours", "sample_days", "already_booked"]
    rows = [("2026-11-23", 0, 1.0, 2.0, 12, 0), ("2026-11-28", 5, 4.0, 8.0, 12, 1), ("2026-11-24", 1, 0.2, 0.4, 12, 0)]
    db([OWN, (r"sp_ForecastDemand", cols, rows)])
    out = analytics.forecast(PROVIDER, 1, 7, 84)
    levels = {r["weekday_index"]: r["level"] for r in out["forecast"]}
    assert levels[5] == "HIGH" and levels[1] == "LOW" and out["reliable"] is True


def test_forecast_unreliable_with_few_samples(db):
    cols = ["forecast_date", "weekday_index", "expected_bookings", "expected_hours", "sample_days", "already_booked"]
    db([OWN, (r"sp_ForecastDemand", cols, [("2026-11-23", 0, 1.0, 2.0, 2, 0)])])
    assert analytics.forecast(PROVIDER, 1, 7, 84)["reliable"] is False


# ---- admin / community / ai
def test_admin_cannot_approve_studio_of_unapproved_provider(db):
    from admin import service as admin
    conn = db([(r"FROM dbo.Studios s WITH", ["status", "provider_status"], [("PENDING", "PENDING")])])
    with pytest.raises(HTTPException) as e:
        admin.set_studio_status(1, "APPROVED")
    assert e.value.status_code == 409 and not conn.cur.sqls("UPDATE dbo.Studios")


def test_admin_suspend_provider_suspends_open_studios(db):
    from admin import service as admin
    conn = db([(r"SELECT status FROM dbo.Users WITH", ["status"], [("ACTIVE",)]),
               (r"SELECT user_id, username", ["user_id", "status"], [(5, "SUSPENDED")])])
    assert admin.set_provider_status(ADMIN, 5, "SUSPENDED")["status"] == "SUSPENDED"
    assert conn.cur.sqls("UPDATE dbo.Studios") and conn.commits == 1


def test_admin_approve_unknown_provider_404(db):
    from admin import service as admin
    db([(r"SELECT status FROM dbo.Users WITH", ["status"], [])])
    with pytest.raises(HTTPException) as e:
        admin.set_provider_status(ADMIN, 99, "ACTIVE")
    assert e.value.status_code == 404


def test_customer_cannot_post_workshop_announcement(db):
    from community import service as community
    conn = db([])
    data = SimpleNamespace(post_type="WORKSHOP_ANNOUNCEMENT", title="t", content="c", image_url=None)
    with pytest.raises(HTTPException) as e:
        community.create_post({"user_id": 9, "role": "CUSTOMER"}, data)
    assert e.value.status_code == 403 and not conn.cur.sqls("INSERT")


def test_only_author_or_admin_deletes_post(db):
    from community import service as community
    script = [(r"SELECT author_id FROM dbo.CommunityPosts", ["author_id"], [(9,)])]
    conn = db(script)
    with pytest.raises(HTTPException) as e:
        community.delete_post({"user_id": 10, "role": "CUSTOMER"}, 1)
    assert e.value.status_code == 403 and not conn.cur.sqls("DELETE")
    conn = db(script)
    community.delete_post(ADMIN, 1)
    assert conn.cur.sqls("DELETE FROM dbo.CommunityPosts")


def test_ai_parse_query():
    from ai.service import parse_query
    out = parse_query("Cần phòng tối dưới 300k ở Hà Nội cho 4 người", ["Hà Nội", "TP.HCM"])
    assert out == {"room_type": "DARKROOM", "max_price": 300000.0, "capacity": 4, "city": "Hà Nội"}
    assert parse_query("studio chụp ảnh tối đa 1,5tr", [])["max_price"] == 1500000.0
    assert parse_query("xin chào", []) == {"room_type": None, "max_price": None, "capacity": None, "city": None}
