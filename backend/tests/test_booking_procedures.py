"""booking.service phải đổi trạng thái qua stored procedure có thật trong SQL (cursor giả)."""
import pytest

from booking import service
from tests.test_provider_service import FakeConn, FakeCursor, sql_error

ROW_COLS = ["reservation_id", "room_id", "customer_id", "start_time", "end_time",
            "total_amount", "customer_note", "status"]
ROW = [(7, 3, 9, "2026-11-20 09:00", "2026-11-20 11:00", 500000, None, "CONFIRMED")]


@pytest.fixture
def conn(monkeypatch):
    def install(extra=()):
        c = FakeConn(FakeCursor(list(extra) + [(r"FROM dbo.Reservations WHERE reservation_id", ROW_COLS, ROW)]))
        monkeypatch.setattr(service, "get_db_connection", lambda: c)
        return c
    return install


@pytest.mark.parametrize("target,proc", [("CONFIRMED", "sp_ConfirmReservation"),
                                         ("CANCELLED", "sp_CancelReservation"),
                                         ("COMPLETED", "sp_CheckOut")])
def test_status_change_calls_existing_procedure(conn, target, proc):
    c = conn()
    out = service._change_status(7, target, 5)
    (sql, params), = c.cur.sqls(proc)
    assert params == (7, 5) and out["reservation_id"] == 7 and c.commits == 1
    assert not c.cur.sqls("sp_UpdateReservationStatus")


def test_in_use_goes_through_qr_check_in(conn):
    c = conn([(r"SELECT qr_code", ["qr_code"], [("QR-00007-ABC",)])])
    service._change_status(7, "IN_USE", 5)
    assert c.cur.sqls("sp_CheckIn")[0][1] == ("QR-00007-ABC", 5)


def test_in_use_without_qr_is_invalid_state(conn):
    c = conn([(r"SELECT qr_code", ["qr_code"], [(None,)])])
    with pytest.raises(service.InvalidStateError):
        service._change_status(7, "IN_USE", 5)
    assert c.rollbacks == 1 and not c.cur.sqls("sp_CheckIn")


def test_pending_target_rejected(conn):
    conn()
    with pytest.raises(service.InvalidStateError):
        service._change_status(7, "PENDING", 5)


@pytest.mark.parametrize("message,exc", [
    ("Chỉ xác nhận được đơn đang PENDING.", service.InvalidStateError),
    ("Không tìm thấy đơn.", service.BookingNotFoundError),
    ("Chỉ chủ studio hoặc admin mới được xác nhận đơn.", service.PermissionDeniedError),
    ("Bạn không có quyền hủy đơn này.", service.PermissionDeniedError),
])
def test_sql_errors_mapped(conn, message, exc):
    c = conn([(r"EXEC dbo.sp_ConfirmReservation", None, sql_error(message))])
    with pytest.raises(exc) as e:
        service._change_status(7, "CONFIRMED", 5)
    assert str(e.value) == message and c.rollbacks == 1


def _create_data(promo=None):
    from datetime import datetime
    from types import SimpleNamespace
    return SimpleNamespace(room_id=3, start_time=datetime(2026, 11, 30, 9), end_time=datetime(2026, 11, 30, 11),
                           customer_note=None, promo_code=promo)


def test_create_booking_recalculates_price_in_same_transaction(conn):
    c = conn([(r"SELECT TOP 1", ROW_COLS, ROW)])
    service.create_booking(9, _create_data())
    sqls = [s for s, _ in c.cur.log]
    assert any("sp_CreateReservation" in s for s in sqls)
    assert c.cur.sqls("sp_RecalculateReservationTotal")[0][1] == (7,)
    assert not c.cur.sqls("sp_ApplyPromotion") and c.commits == 1


def test_create_booking_with_promo_applies_code_uppercased(conn):
    c = conn([(r"SELECT TOP 1", ROW_COLS, ROW)])
    service.create_booking(9, _create_data(" welcome10 "))
    assert c.cur.sqls("sp_ApplyPromotion")[0][1] == (7, "WELCOME10", 9) and c.commits == 1


def test_create_booking_bad_promo_rolls_back_whole_booking(conn):
    c = conn([(r"SELECT TOP 1", ROW_COLS, ROW),
              (r"sp_ApplyPromotion", None, sql_error("Không tìm thấy mã khuyến mãi ở studio này.", 51005))])
    with pytest.raises(service.BookingError):
        service.create_booking(9, _create_data("NOPE"))
    assert c.commits == 0 and c.rollbacks == 1
