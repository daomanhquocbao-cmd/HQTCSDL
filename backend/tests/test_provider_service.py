"""Kiểm tra logic của provider.service bằng cursor giả (không cần SQL Server).

Mỗi câu SQL được kiểm tra số dấu `?` khớp số tham số truyền vào, rồi so với kịch bản trả về.
Việc chạy SQL thật vẫn cần SQL Server (xem README)."""
import os
import re
import sys
from collections import namedtuple
from decimal import Decimal
from types import SimpleNamespace

import pyodbc
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import HTTPException  # noqa: E402
from provider import service  # noqa: E402

PROVIDER = {"user_id": 5, "role": "PROVIDER"}
OTHER = {"user_id": 6, "role": "PROVIDER"}
ADMIN = {"user_id": 1, "role": "ADMIN"}


def sql_error(msg: str, code: int = 50000) -> pyodbc.Error:
    return pyodbc.Error(f"('{code}', '[{code}] [Microsoft][ODBC Driver 17][SQL Server]{msg} ({code}) (SQLExecDirectW)')")


class FakeCursor:
    """script: [(regex, columns, rows | Exception)]; câu SQL khớp đầu tiên được dùng."""

    def __init__(self, script):
        self.script, self.log = script, []
        self.description, self._rows = None, []

    def execute(self, sql, *params):
        assert sql.count("?") == len(params), f"Số ? khác số tham số:\n{sql}\n{params}"
        self.log.append((sql, params))
        self.description, self._rows = None, []
        for pattern, cols, rows in self.script:
            if re.search(pattern, sql, re.S):
                if isinstance(rows, Exception):
                    raise rows
                if cols:
                    row_t = namedtuple("Row", cols)
                    self.description = [(c,) for c in cols]
                    self._rows = [row_t(*r) for r in rows]
                return self
        return self

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def fetchall(self):
        return list(self._rows)

    def nextset(self):
        return False

    def sqls(self, needle):
        return [(s, p) for s, p in self.log if needle in s]


class FakeConn:
    def __init__(self, cursor):
        self.cur, self.commits, self.rollbacks, self.closed = cursor, 0, 0, False

    def cursor(self):
        return self.cur

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def close(self):
        self.closed = True


@pytest.fixture
def db(monkeypatch):
    def install(script):
        conn = FakeConn(FakeCursor(script))
        monkeypatch.setattr(service, "get_db_connection", lambda: conn)
        return conn
    return install


BOOKING_COLS = ["reservation_id", "status", "start_time", "end_time", "customer_id", "customer",
                "customer_name", "room_id", "room_name", "studio_id", "studio_name", "total_amount",
                "paid_amount", "balance_due", "qr_code", "customer_note", "provider_id"]


def booking_row(provider_id=5, status="PENDING"):
    return (7, status, "2026-11-20 09:00", "2026-11-20 11:00", 9, "kh1", "Khách 1", 3, "Phòng A", 1,
            "Studio", Decimal("500000"), Decimal("0"), Decimal("500000"), None, None, provider_id)


def detail_script(provider_id=5, status="PENDING"):
    return [(r"FROM dbo.vw_ReservationDetail", BOOKING_COLS, [booking_row(provider_id, status)]),
            (r"FROM dbo.ReservationEquipments", ["equipment_id", "name", "quantity", "unit_price"], []),
            (r"FROM dbo.ReservationPackages", ["package_id", "name", "price", "notes"], []),
            (r"FROM dbo.Payments", ["payment_id", "amount"], []),
            (r"FROM dbo.ReservationStatusHistory", ["old_status", "new_status"], [(None, "PENDING")]),
            (r"FROM dbo.ServiceSessions", ["checkin_time"], [])]


# ---------------------------------------------------------------- phạm vi dữ liệu
def test_provider_list_is_scoped_admin_is_not(db):
    conn = db([(r"FROM dbo.Studios s", ["studio_id", "open_time"], [(1, __import__("datetime").time(8, 0))])])
    assert service.list_studios(PROVIDER) == [{"studio_id": 1, "open_time": "08:00"}]
    sql, params = conn.cur.log[0]
    assert "s.provider_id = ?" in sql and params == (5,)

    conn = db([(r"FROM dbo.Studios s", ["studio_id"], [])])
    service.list_studios(ADMIN)
    assert conn.cur.log[0][1] == ()


def test_booking_of_other_provider_is_403_and_sp_not_called(db):
    conn = db(detail_script(provider_id=5))
    with pytest.raises(HTTPException) as e:
        service.confirm(OTHER, 7)
    assert e.value.status_code == 403
    assert not conn.cur.sqls("sp_ConfirmReservation")
    assert conn.rollbacks == 1 and conn.closed


def test_missing_booking_is_404(db):
    db([(r"FROM dbo.vw_ReservationDetail", BOOKING_COLS, [])])
    with pytest.raises(HTTPException) as e:
        service.get_booking(PROVIDER, 999)
    assert e.value.status_code == 404


# ------------------------------------------------------------ gọi stored procedure
@pytest.mark.parametrize("fn,sp", [(service.confirm, "sp_ConfirmReservation"),
                                    (service.cancel, "sp_CancelReservation"),
                                    (service.checkout, "sp_CheckOut")])
def test_status_actions_call_sp_with_actor(db, fn, sp):
    conn = db(detail_script())
    result = fn(PROVIDER, 7)
    (sql, params), = conn.cur.sqls(sp)
    assert params == (7, 5)
    assert result["reservation_id"] == 7 and "provider_id" not in result
    assert result["history"] and result["equipment"] == [] and result["session"] is None
    assert conn.commits == 1 and conn.closed


def test_admin_can_act_on_any_booking(db):
    conn = db(detail_script(provider_id=5))
    service.confirm(ADMIN, 7)
    assert conn.cur.sqls("sp_ConfirmReservation")[0][1] == (7, 1)


def test_payment_passes_decimal_and_method(db):
    conn = db(detail_script())
    service.pay(PROVIDER, 7, SimpleNamespace(amount=250000.0, payment_method="CASH", transaction_code=None))
    (sql, params), = conn.cur.sqls("sp_ProcessPayment")
    assert params == (7, Decimal("250000.0"), "CASH", 5, None)


def test_add_equipment_and_package(db):
    conn = db(detail_script())
    service.add_equipment(PROVIDER, 7, SimpleNamespace(equipment_id=2, quantity=3))
    service.add_package(PROVIDER, 7, SimpleNamespace(package_id=4, notes="ghi chú"))
    assert conn.cur.sqls("sp_AddReservationEquipment")[0][1] == (7, 2, 3, 5)
    assert conn.cur.sqls("sp_AddReservationPackage")[0][1] == (7, 4, 5, "ghi chú")


@pytest.mark.parametrize("message,code", [
    ("Chỉ xác nhận được đơn đang PENDING.", 409),
    ("Chưa đến giờ check-in (sớm nhất 30 phút) hoặc đã quá giờ.", 409),
    ("Số tiền thanh toán vượt quá tổng tiền của đơn.", 409),
    ("Chỉ chủ studio hoặc admin mới được xác nhận đơn.", 403),
    ("Bạn không có quyền thao tác đơn này.", 403),
    ("Không tìm thấy đơn.", 404),
])
def test_sql_errors_keep_vietnamese_message_and_map_status(db, message, code):
    conn = db(detail_script() + [(r"EXEC dbo.sp_ConfirmReservation", None, sql_error(message))])
    with pytest.raises(HTTPException) as e:
        service.confirm(PROVIDER, 7)
    assert e.value.status_code == code and e.value.detail == message
    assert conn.rollbacks == 1 and conn.commits == 0


def test_check_in_unknown_qr_is_404(db):
    conn = db([(r"FROM dbo.Reservations WHERE qr_code", ["reservation_id"], [])])
    with pytest.raises(HTTPException) as e:
        service.check_in(PROVIDER, "QR-NOPE")
    assert e.value.status_code == 404 and not conn.cur.sqls("sp_CheckIn")


def test_check_in_by_qr(db):
    conn = db([(r"FROM dbo.Reservations WHERE qr_code", ["reservation_id"], [(7,)])] + detail_script(status="CONFIRMED"))
    service.check_in(PROVIDER, "QR-00007-ABC")
    assert conn.cur.sqls("sp_CheckIn")[0][1] == ("QR-00007-ABC", 5)


def test_check_in_qr_of_other_studio_is_403(db):
    conn = db([(r"FROM dbo.Reservations WHERE qr_code", ["reservation_id"], [(7,)])] + detail_script())
    with pytest.raises(HTTPException) as e:
        service.check_in(OTHER, "QR-00007-ABC")
    assert e.value.status_code == 403 and not conn.cur.sqls("sp_CheckIn")


# ----------------------------------------------------------- studio / phòng / thiết bị
def test_provider_studio_starts_pending_admin_approved(db):
    data = SimpleNamespace(name="S", address="A", city="C", description=None, phone=None,
                           open_time="08:00", close_time="21:00")
    for user, expected in ((PROVIDER, "PENDING"), (ADMIN, "APPROVED")):
        conn = db([(r"SELECT status FROM dbo.Users", ["status"], [("ACTIVE",)]),
                   (r"SCOPE_IDENTITY", ["id"], [(11,)]), (r"FROM dbo.Studios s", ["studio_id"], [(11,)])])
        service.create_studio(user, data)
        assert conn.cur.sqls("INSERT INTO dbo.Studios")[0][1][-1] == expected


@pytest.mark.parametrize("status_", ["PENDING", "SUSPENDED"])
def test_unapproved_provider_cannot_create_studio(db, status_):
    conn = db([(r"SELECT status FROM dbo.Users", ["status"], [(status_,)])])
    data = SimpleNamespace(name="S", address="A", city="C", description=None, phone=None,
                           open_time="08:00", close_time="21:00")
    with pytest.raises(HTTPException) as e:
        service.create_studio(PROVIDER, data)
    assert e.value.status_code == 403 and not conn.cur.sqls("INSERT INTO dbo.Studios")


def test_studio_hours_validated(db):
    db([])
    bad = SimpleNamespace(name="S", address="A", city="C", description=None, phone=None,
                          open_time="21:00", close_time="08:00")
    with pytest.raises(HTTPException) as e:
        service.create_studio(PROVIDER, bad)
    assert e.value.status_code == 400
    with pytest.raises(HTTPException):
        service.create_studio(PROVIDER, SimpleNamespace(**{**bad.__dict__, "open_time": "8h"}))


def _studio_script(reservations=0, workshops=0, owner=5):
    return [(r"SELECT provider_id FROM dbo.Studios", ["provider_id"], [(owner,)]),
            (r"FROM dbo.Reservations rs", ["n"], [(reservations,)]),
            (r"FROM dbo.Workshops", ["n"], [(workshops,)])]


def test_delete_studio_removes_children_in_fk_order(db):
    conn = db(_studio_script())
    service.delete_studio(PROVIDER, 1)
    order = [s.split("dbo.")[1].split()[0] for s, _ in conn.cur.log if s.startswith("DELETE")]
    assert order == ["ServicePackages", "Equipment", "Rooms", "Studios"]
    assert conn.commits == 1 and conn.rollbacks == 0


def test_delete_studio_also_clears_pricing_and_promotions_guarded(db):
    conn = db(_studio_script())
    service.delete_studio(PROVIDER, 1)
    guarded = [s for s, _ in conn.cur.log if s.startswith("IF OBJECT_ID")]
    assert len(guarded) == 2 and "PricingRules" in guarded[0] and "Promotions" in guarded[1]


@pytest.mark.parametrize("reservations,workshops", [(3, 0), (0, 1)])
def test_delete_studio_with_history_is_409_and_deletes_nothing(db, reservations, workshops):
    conn = db(_studio_script(reservations, workshops))
    with pytest.raises(HTTPException) as e:
        service.delete_studio(PROVIDER, 1)
    assert e.value.status_code == 409
    assert not conn.cur.sqls("DELETE")


def test_delete_studio_of_other_provider_is_403(db):
    conn = db(_studio_script(owner=99))
    with pytest.raises(HTTPException) as e:
        service.delete_studio(PROVIDER, 1)
    assert e.value.status_code == 403 and not conn.cur.sqls("DELETE")


def test_delete_missing_studio_is_404(db):
    db([(r"SELECT provider_id FROM dbo.Studios", ["provider_id"], [])])
    with pytest.raises(HTTPException) as e:
        service.delete_studio(PROVIDER, 1)
    assert e.value.status_code == 404


def test_create_room_requires_own_studio(db):
    data = SimpleNamespace(studio_id=1, name="R", room_type="STUDIO", capacity=2, area_sqm=None, art_style=None,
                           lighting=None, amenities=None, price_per_hour=100000.0, description=None, status="AVAILABLE")
    conn = db([(r"SELECT provider_id FROM dbo.Studios", ["provider_id"], [(5,)])])
    with pytest.raises(HTTPException) as e:
        service.create_room(OTHER, data)
    assert e.value.status_code == 403 and not conn.cur.sqls("INSERT INTO dbo.Rooms")


def test_update_room_drops_null_for_not_null_columns(db):
    from provider.schemas import RoomPatch
    conn = db([(r"FROM dbo.Rooms r", ["room_id", "studio_id"], [(3, 1)]),
               (r"SELECT provider_id FROM dbo.Studios", ["provider_id"], [(5,)])])
    service.update_room(PROVIDER, 3, RoomPatch(name=None, area_sqm=None, status="INACTIVE"))
    (sql, params), = conn.cur.sqls("UPDATE dbo.Rooms")
    assert "name" not in sql and "area_sqm = ?" in sql and "status = ?" in sql
    assert params == (None, "INACTIVE", 3)


def test_empty_patch_is_400(db):
    from provider.schemas import RoomPatch
    db([(r"FROM dbo.Rooms r", ["room_id", "studio_id"], [(3, 1)]),
        (r"SELECT provider_id FROM dbo.Studios", ["provider_id"], [(5,)])])
    with pytest.raises(HTTPException) as e:
        service.update_room(PROVIDER, 3, RoomPatch())
    assert e.value.status_code == 400


def test_retire_equipment_sets_status(db):
    conn = db([(r"FROM dbo.Equipment e", ["equipment_id", "studio_id"], [(2, 1)]),
               (r"SELECT provider_id FROM dbo.Studios", ["provider_id"], [(5,)])])
    service.retire_equipment(PROVIDER, 2)
    assert "RETIRED" in conn.cur.sqls("UPDATE dbo.Equipment")[0][0]


def test_maintenance_done_updates_equipment(db):
    from datetime import date
    conn = db([(r"FROM dbo.Equipment e", ["equipment_id", "studio_id"], [(2, 1)]),
               (r"SELECT provider_id FROM dbo.Studios", ["provider_id"], [(5,)]),
               (r"SCOPE_IDENTITY", ["id"], [(40,)]),
               (r"FROM dbo.EquipmentMaintenance WHERE", ["maintenance_id"], [(40,)])])
    out = service.add_maintenance(PROVIDER, 2, SimpleNamespace(cost=50000.0, description="x", status="DONE",
                                                              next_maintenance_date=date(2027, 1, 1)))
    assert out == {"maintenance_id": 40}
    assert conn.cur.sqls("SET next_maintenance_date")[0][1] == (date(2027, 1, 1), 2)
    assert conn.cur.sqls("SET status = 'GOOD'")


def test_constraint_violation_becomes_400(db):
    from provider.schemas import RoomPatch
    db([(r"FROM dbo.Rooms r", ["room_id", "studio_id"], [(3, 1)]),
        (r"SELECT provider_id FROM dbo.Studios", ["provider_id"], [(5,)]),
        (r"UPDATE dbo.Rooms", None, sql_error("The UPDATE statement conflicted with the CHECK constraint \"CK_Rooms_capacity\"."))])
    with pytest.raises(HTTPException) as e:
        service.update_room(PROVIDER, 3, RoomPatch(capacity=2))
    assert e.value.status_code == 400


# ------------------------------------------------------- danh sách & tổng quan
def test_list_bookings_filters_and_paging(db):
    conn = db([(r"FROM dbo.vw_ReservationDetail", BOOKING_COLS, [booking_row()])])
    rows = service.list_bookings(PROVIDER, "PENDING", 1, None, 50, 100)
    assert "provider_id" not in rows[0] and rows[0]["total_amount"] == 500000.0
    sql, params = conn.cur.log[0]
    assert params == (5, "PENDING", 1, 100, 50) and "OFFSET ? ROWS FETCH NEXT ? ROWS ONLY" in sql


def test_packages_grouped_with_equipment(db):
    conn = db([(r"FROM dbo.ServicePackages sp JOIN", ["package_id", "studio_id", "name", "is_active"], [(4, 1, "Gói", 1)]),
               (r"FROM dbo.PackageEquipment", ["package_id", "equipment_id", "name", "quantity_included"],
                [(4, 2, "Đèn", 2), (99, 3, "Lạ", 1)])])
    out = service.list_packages(PROVIDER, None)
    assert out[0]["is_active"] is True
    assert out[0]["equipment"] == [{"equipment_id": 2, "name": "Đèn", "quantity_included": 2}]


def test_overview_shape(db):
    conn = db([(r"FROM dbo.Reviews rv", ["n", "avg_rating"], [(10, Decimal("4.50"))]),
               (r"GROUP BY CONVERT", ["month", "revenue", "bookings"], [("2026-11", Decimal("450000"), 2)]),
               (r"GROUP BY rm.room_id", ["room_id", "room_name", "studio_name", "bookings", "revenue"],
                [(3, "A", "S", 4, Decimal("900000"))]),
               (r"SUM\(p.amount\)", ["x"], [(Decimal("900000"),)]),
               (r"COUNT\(\*\)", ["x"], [(2,)])])
    out = service.overview(PROVIDER)
    assert out["studio_count"] == 2 and out["revenue_total"] == 900000.0
    assert out["avg_rating"] == 4.5 and out["review_count"] == 10
    assert out["revenue_by_month"] == [{"month": "2026-11", "revenue": 450000.0, "bookings": 2}]
    assert out["top_rooms"][0]["revenue"] == 900000.0
    for sql, params in conn.cur.log:      # mọi truy vấn đều lọc theo provider
        assert params.count(5) == 1, sql


def test_overview_no_reviews_gives_null_rating(db):
    db([(r"FROM dbo.Reviews rv", ["n", "avg_rating"], [(0, None)]),
        (r"GROUP BY", ["month"], []),
        (r"SUM\(p.amount\)", ["x"], [(Decimal("0"),)]),
        (r"COUNT\(\*\)", ["x"], [(0,)])])
    out = service.overview(ADMIN)
    assert out["avg_rating"] is None and out["top_rooms"] == []


# ------------------------------------------------------------------- hồ sơ
def test_change_password_wrong_current_is_400(db):
    from core.security import hash_password
    conn = db([(r"SELECT password_hash", ["password_hash"], [(hash_password("Right-pass-1"),)])])
    with pytest.raises(HTTPException) as e:
        service.change_password(PROVIDER, "wrong", "New-pass-123")
    assert e.value.status_code == 400 and not conn.cur.sqls("UPDATE dbo.Users")


def test_change_password_ok_stores_new_hash(db):
    from core.security import hash_password, verify_password
    conn = db([(r"SELECT password_hash", ["password_hash"], [(hash_password("Right-pass-1"),)])])
    service.change_password(PROVIDER, "Right-pass-1", "New-pass-123")
    (sql, params), = conn.cur.sqls("UPDATE dbo.Users")
    assert verify_password("New-pass-123", params[0]) and params[1] == 5


def test_update_profile_duplicate_email_is_409(db):
    from provider.schemas import ProfilePatch
    db([(r"SELECT 1 FROM dbo.Users WHERE email", ["x"], [(1,)])])
    with pytest.raises(HTTPException) as e:
        service.update_profile(PROVIDER, ProfilePatch(email="a@b.vn"))
    assert e.value.status_code == 409


# ------------------------------------------------- lý do hủy đơn / khiếu nại / workshop
def _cancel_script(reason_error=None):
    script = detail_script(status="CANCELLED")
    script.insert(0, (r"UPDATE dbo.Reservations SET cancel_reason", None, reason_error or []))
    script.append((r"SELECT cancel_reason", ["cancel_reason"], [("Khách báo bận",)]))
    return script


def test_cancel_saves_reason_after_procedure(db):
    conn = db(_cancel_script())
    out = service.cancel(PROVIDER, 7, "  Khách báo bận ")
    order = [s for s, _ in conn.cur.log if "sp_CancelReservation" in s or "SET cancel_reason" in s]
    assert "sp_CancelReservation" in order[0] and "SET cancel_reason" in order[1]
    assert conn.cur.sqls("SET cancel_reason")[0][1] == ("Khách báo bận", 7)
    assert out["cancel_reason"] == "Khách báo bận" and out["reason_saved"] is True


def test_cancel_without_reason_skips_update(db):
    conn = db(_cancel_script())
    service.cancel(PROVIDER, 7, None)
    assert not conn.cur.sqls("SET cancel_reason")


def test_cancel_still_succeeds_when_column_missing(db):
    import pyodbc
    conn = db(_cancel_script(reason_error=pyodbc.Error("Invalid column name 'cancel_reason'")))
    out = service.cancel(PROVIDER, 7, "Bảo trì phòng")
    assert out["status"] == "CANCELLED" and out["reason_saved"] is False and out["cancel_reason"] is None
    assert conn.commits == 1


DISPUTE_COLS = ["dispute_id", "status", "provider_id"]


def _dispute_script(st="OPEN", owner=5):
    return [(r"SELECT d\.status, s\.provider_id", DISPUTE_COLS, [(3, st, owner)]),
            (r"d\.dispute_id, d\.reservation_id", ["dispute_id", "status"], [(3, "X")])]


def _patch(status, resolution=None):
    from provider.schemas import DisputePatch
    return DisputePatch(status=status, resolution=resolution)


def test_dispute_in_review_does_not_set_resolver(db):
    conn = db(_dispute_script())
    service.update_dispute(PROVIDER, 3, _patch("IN_REVIEW"))
    sql, params = conn.cur.sqls("UPDATE dbo.Disputes")[0]
    assert "resolved_by" not in sql and params == ("IN_REVIEW", 3)


def test_dispute_resolve_requires_text_and_records_resolver(db):
    conn = db(_dispute_script())
    with pytest.raises(HTTPException) as e:
        service.update_dispute(PROVIDER, 3, _patch("RESOLVED", "  "))
    assert e.value.status_code == 400 and not conn.cur.sqls("UPDATE dbo.Disputes")
    conn = db(_dispute_script())
    service.update_dispute(PROVIDER, 3, _patch("RESOLVED", "Hoàn 50% tiền cho khách"))
    assert conn.cur.sqls("UPDATE dbo.Disputes")[0][1] == ("RESOLVED", "Hoàn 50% tiền cho khách", 5, 3)


@pytest.mark.parametrize("st,owner,patch,code", [
    ("RESOLVED", 5, ("IN_REVIEW", None), 409),       # đã xử lý xong
    ("OPEN", 99, ("IN_REVIEW", None), 403),          # của studio khác
    ("OPEN", 5, ("REJECTED", "Không hợp lệ"), 403),  # chỉ admin được bác bỏ
])
def test_dispute_rules(db, st, owner, patch, code):
    conn = db(_dispute_script(st, owner))
    with pytest.raises(HTTPException) as e:
        service.update_dispute(PROVIDER, 3, _patch(*patch))
    assert e.value.status_code == code and not conn.cur.sqls("UPDATE dbo.Disputes")


def test_admin_can_reject_dispute(db):
    conn = db(_dispute_script(owner=99))
    service.update_dispute(ADMIN, 3, _patch("REJECTED", "Không đủ căn cứ"))
    assert conn.cur.sqls("UPDATE dbo.Disputes")[0][1][0] == "REJECTED"


def test_dispute_missing_is_404(db):
    db([(r"SELECT d\.status, s\.provider_id", DISPUTE_COLS, [])])
    with pytest.raises(HTTPException) as e:
        service.update_dispute(PROVIDER, 3, _patch("IN_REVIEW"))
    assert e.value.status_code == 404


def test_lists_of_disputes_and_workshops_are_scoped_and_filtered(db):
    conn = db([(r"FROM dbo.Disputes", ["dispute_id"], [(1,)])])
    assert service.list_disputes(PROVIDER, "OPEN", 50, 0) == [{"dispute_id": 1}]
    sql, params = conn.cur.log[0]
    assert "s.provider_id = ?" in sql and "d.status = ?" in sql and params == (5, "OPEN", 0, 50)
    conn = db([(r"FROM dbo.Workshops", ["workshop_id"], [(2,)])])
    assert service.list_workshops(PROVIDER, None, 50, 10) == [{"workshop_id": 2}]
    sql, params = conn.cur.log[0]
    assert "s.provider_id = ?" in sql and "JOIN dbo.Studios s" in sql and params == (5, 10, 50)
    conn = db([(r"FROM dbo.Workshops", ["workshop_id"], [])])
    service.list_workshops(ADMIN, None, 50, 0)
    assert conn.cur.log[0][1] == (0, 50)
