"""Kiểm tra logic khách hàng, bộ sưu tập ảnh, admin mở rộng, tìm tri thức bằng cursor giả (không cần SQL Server)."""
import base64
import io
import os
import sys
from datetime import date, datetime
from decimal import Decimal

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import HTTPException  # noqa: E402
from admin import service as admin_service  # noqa: E402
from ai import service as ai_service  # noqa: E402
from booking import service as booking_service  # noqa: E402
from booking.schemas import BookingCreate  # noqa: E402
from community import service as community  # noqa: E402
from core import platform_settings  # noqa: E402
from customer import service as customer  # noqa: E402
from photos import service as photos  # noqa: E402
from provider import analytics, service  # noqa: E402
from tests.test_provider_service import ADMIN, FakeConn, FakeCursor, sql_error  # noqa: E402

CUSTOMER = {"user_id": 9, "role": "CUSTOMER"}


@pytest.fixture
def db(monkeypatch):
    def install(script):
        conn = FakeConn(FakeCursor(script))
        monkeypatch.setattr(service, "get_db_connection", lambda: conn)
        return conn
    return install


# ------------------------------------------------------------------ tìm phòng
ROOM_COLS = ["room_id", "room_name", "avg_rating", "studio_id", "room_type"]


def test_search_rooms_builds_filters_and_params(db):
    conn = db([(r"FROM dbo.Rooms rm", ROOM_COLS, [(1, "Phòng A", Decimal("4.50"), 3, "STUDIO")])])
    out = customer.search_rooms("vintage", "STUDIO", "Hà Nội", 100000, 500000, 4, "price_asc", 10, 0,
                                datetime(2026, 12, 1, 9), datetime(2026, 12, 1, 11))
    sql, params = conn.cur.log[0]
    assert "s.status = 'APPROVED'" in sql and "rm.status = 'AVAILABLE'" in sql      # chỉ phòng công khai
    assert "NOT EXISTS" in sql and "ORDER BY rm.price_per_hour ASC" in sql
    assert params[-2:] == (0, 10) and "STUDIO" in params and out[0]["avg_rating"] == 4.5


def test_search_rooms_unknown_sort_falls_back_to_rating(db):
    conn = db([(r"FROM dbo.Rooms rm", ROOM_COLS, [])])
    customer.search_rooms(None, None, None, None, None, None, "'; DROP TABLE x;--", 5, 0)
    assert "DROP" not in conn.cur.log[0][0] and "ISNULL(v.avg_rating, 0) DESC" in conn.cur.log[0][0]


def test_room_detail_404_when_not_public(db):
    db([(r"FROM dbo.Rooms rm", ROOM_COLS, [])])
    with pytest.raises(HTTPException) as e:
        customer.room_detail(99)
    assert e.value.status_code == 404


def test_room_detail_collects_equipment_packages_reviews(db):
    db([(r"FROM dbo.Rooms rm", ROOM_COLS, [(1, "A", Decimal("4"), 3, "DARKROOM")]),
        (r"FROM dbo.Equipment", ["equipment_id", "name"], [(5, "Máy phóng")]),
        (r"FROM dbo.ServicePackages", ["package_id", "name"], [(2, "Tráng phim")]),
        (r"FROM dbo.Reviews", ["rating"], [(5,)])])
    d = customer.room_detail(1)
    assert d["equipment"][0]["name"] == "Máy phóng" and d["packages"][0]["package_id"] == 2 and d["reviews"]


# ------------------------------------------------------------- đơn của khách
BK_COLS = ["reservation_id", "status", "start_time", "end_time", "room_id", "room_name", "studio_id", "studio_name",
           "total_amount", "paid_amount", "balance_due", "qr_code", "customer_note", "created_at", "has_review"]


def bk_script(owner=True):
    row = (7, "PENDING", "2026-12-01 09:00", "2026-12-01 11:00", 3, "A", 1, "S", Decimal("500000"), Decimal("0"),
           Decimal("500000"), None, None, None, 0)
    return [(r"FROM dbo.vw_ReservationDetail v JOIN", BK_COLS, [row] if owner else []),
            (r"FROM dbo.ReservationEquipments", ["equipment_id", "name", "quantity", "unit_price"], []),
            (r"FROM dbo.ReservationPackages", ["package_id", "name", "price"], []),
            (r"FROM dbo.Payments", ["payment_id", "amount"], []),
            (r"FROM dbo.ReservationPromotions", ["code"], []),
            (r"FROM dbo.Disputes", ["dispute_id"], [])]


def test_booking_detail_only_for_owner(db):
    conn = db(bk_script(owner=False))
    with pytest.raises(HTTPException) as e:
        customer.booking_detail(CUSTOMER, 7)
    assert e.value.status_code == 404
    assert conn.cur.log[0][1] == (9, 7)                       # lọc theo customer_id của người đăng nhập


def test_add_equipment_calls_procedure_with_customer_as_actor(db):
    conn = db(bk_script())
    out = customer.add_equipment(CUSTOMER, 7, 5, 2)
    sql, params = conn.cur.sqls("sp_AddReservationEquipment")[0]
    assert params == (7, 5, 2, 9) and out["reservation_id"] == 7 and conn.commits == 1


def test_pay_passes_decimal_and_maps_sql_error(db):
    conn = db(bk_script())
    customer.pay(CUSTOMER, 7, 250000.0, "MOMO", "TX1")
    assert conn.cur.sqls("sp_ProcessPayment")[0][1][1] == Decimal("250000.0")
    script = bk_script() + []
    script.insert(0, (r"sp_ProcessPayment", None, sql_error("Số tiền thanh toán vượt quá tổng tiền của đơn.", 50804)))
    conn2 = db(script)
    with pytest.raises(HTTPException) as e:
        customer.pay(CUSTOMER, 7, 999999999, "CASH", None)
    assert e.value.status_code == 409 and "vượt quá" in e.value.detail and conn2.rollbacks == 1


def test_dispute_rejects_duplicate_open_one(db):
    script = bk_script()
    script.insert(0, (r"SELECT 1 FROM dbo.Disputes", ["x"], [(1,)]))
    db(script)
    with pytest.raises(HTTPException) as e:
        customer.raise_dispute(CUSTOMER, 7, "Thiết bị hỏng giữa buổi")
    assert e.value.status_code == 409


# ------------------------------------------------------------------- cấu hình
def test_cast_types():
    assert platform_settings.cast("1", "BOOL") is True and platform_settings.cast("0", "BOOL") is False
    assert platform_settings.cast("75", "INT") == 75 and platform_settings.cast("1.5", "NUMBER") == 1.5


def test_get_setting_uses_default_when_db_down(monkeypatch):
    def boom():
        raise RuntimeError("no db")
    monkeypatch.setattr(platform_settings, "get_db_connection", boom)
    assert platform_settings.get_setting("booking.max_hours_per_booking") == 12
    assert platform_settings.get_setting("platform.maintenance_mode") is False


def test_maintenance_mode_blocks_booking(monkeypatch):
    monkeypatch.setattr(booking_service, "get_setting", lambda k: True if k == "platform.maintenance_mode" else 12)
    data = BookingCreate(room_id=1, start_time=datetime(2026, 12, 1, 9), end_time=datetime(2026, 12, 1, 11))
    with pytest.raises(booking_service.BookingError) as e:
        booking_service.create_booking(9, data)
    assert "bảo trì" in str(e.value)


def test_max_hours_blocks_long_booking(monkeypatch):
    monkeypatch.setattr(booking_service, "get_setting", lambda k: False if k.startswith("platform") else 4)
    data = BookingCreate(room_id=1, start_time=datetime(2026, 12, 1, 8), end_time=datetime(2026, 12, 1, 20))
    with pytest.raises(booking_service.BookingError) as e:
        booking_service.create_booking(9, data)
    assert "tối đa 4 giờ" in str(e.value)


def test_require_enabled_raises_403(monkeypatch):
    monkeypatch.setattr(platform_settings, "get_setting", lambda k, d=None: False)
    with pytest.raises(HTTPException) as e:
        platform_settings.require_enabled("ai.assistant.enabled", "tắt")
    assert e.value.status_code == 403


SETTING_ROW = [(r"SELECT value_type FROM dbo.SystemSettings", ["value_type"], [("INT",)])]


@pytest.mark.parametrize("value", [-1, "abc"])
def test_update_setting_rejects_bad_numbers(db, value):
    db(SETTING_ROW)
    with pytest.raises(HTTPException) as e:
        admin_service.update_setting(ADMIN, "booking.max_hours_per_booking", value)
    assert e.value.status_code == 400


def test_update_setting_pct_over_100_rejected(db):
    db(SETTING_ROW)
    with pytest.raises(HTTPException):
        admin_service.update_setting(ADMIN, "pricing.high_occupancy_pct", 150)


def test_update_setting_unknown_key_404(db):
    db([(r"SELECT value_type FROM dbo.SystemSettings", ["value_type"], [])])
    with pytest.raises(HTTPException) as e:
        admin_service.update_setting(ADMIN, "nope", 1)
    assert e.value.status_code == 404


def test_update_setting_threshold_order_rolls_back(db):
    script = [(r"SELECT value_type FROM dbo.SystemSettings", ["value_type"], [("INT",)]),
              (r"SELECT MAX\(CASE", ["h", "l"], [(60, 80)])]
    conn = db(script)
    with pytest.raises(HTTPException) as e:
        admin_service.update_setting(ADMIN, "pricing.low_occupancy_pct", 80)
    assert e.value.status_code == 400 and conn.rollbacks == 1 and conn.commits == 0


# -------------------------------------------------------------- admin: người dùng
def test_admin_cannot_suspend_self_or_admin_or_provider(db):
    with pytest.raises(HTTPException) as e:
        admin_service.set_user_status(ADMIN, 1, "SUSPENDED")
    assert e.value.status_code == 409
    for role, code in (("ADMIN", 403), ("PROVIDER", 409)):
        db([(r"SELECT role, status FROM dbo.Users", ["role", "status"], [(role, "ACTIVE")])])
        with pytest.raises(HTTPException) as e:
            admin_service.set_user_status(ADMIN, 50, "SUSPENDED")
        assert e.value.status_code == code


def test_admin_suspends_customer(db):
    conn = db([(r"SELECT role, status FROM dbo.Users", ["role", "status"], [("CUSTOMER", "ACTIVE")]),
               (r"SELECT user_id, username", ["user_id", "status"], [(50, "SUSPENDED")])])
    assert admin_service.set_user_status(ADMIN, 50, "SUSPENDED")["status"] == "SUSPENDED"
    assert conn.cur.sqls("UPDATE dbo.Users")[0][1] == ("SUSPENDED", 50)


def test_admin_payments_missing_view_gives_503(db):
    db([(r"vw_PaymentLedger", None, sql_error("Invalid object name 'dbo.vw_PaymentLedger'."))])
    with pytest.raises(HTTPException) as e:
        admin_service.list_payments(None, None, 20, 0)
    assert e.value.status_code == 503 and "08_collections" in e.value.detail


def test_admin_refund_calls_procedure(db):
    conn = db([(r"SELECT \* FROM dbo.vw_PaymentLedger", ["payment_id", "status"], [(3, "REFUNDED")])])
    assert admin_service.refund_payment(ADMIN, 3)["status"] == "REFUNDED"
    assert conn.cur.sqls("sp_RefundPayment")[0][1] == (3, 1)


# ------------------------------------------------------- tìm tri thức / giá động
def test_synonym_expansion_links_tráng_phim_to_develop():
    w = community.expand_query("cách tráng phim đen trắng")
    assert w["trang"] == 1.0 and "develop" in w and w["develop"] == 0.5


def test_rank_documents_prefers_title_and_rare_terms():
    docs = [
        {"title": "Review Pentax K1000", "content": "Máy cơ bền, dễ dùng cho người mới."},
        {"title": "Tráng phim đen trắng tại nhà", "content": "Chuẩn bị hóa chất developer, fixer và tank tráng."},
        {"title": "Chọn đèn studio", "content": "Đèn liên tục và đèn flash khác nhau."},
    ]
    out = community.rank_documents("làm sao tráng phim B&W", docs, 3)
    assert out[0]["title"].startswith("Tráng phim") and all(d["score"] > 0 for d in out)
    assert community.rank_documents("xyz không có", docs, 3) == []


def test_snippet_centers_on_match():
    text = "a " * 80 + "hóa chất developer rất quan trọng " + "b " * 80
    sn = community.snippet(text, community.expand_query("hóa chất"))
    assert "hóa chất" in sn and sn.startswith("…")


def test_pricing_thresholds_are_configurable():
    cells = [{"weekday_index": 0, "hour": h, "booked_hours": 5.0, "available_hours": 10.0} for h in range(8, 12)]
    assert analytics.build_pricing_suggestions(cells, 8 * 60, 21 * 60, []) == []          # 50%: mặc định không gợi ý
    out = analytics.build_pricing_suggestions(cells, 8 * 60, 21 * 60, [], high=45, low=10)  # hạ ngưỡng -> gợi ý tăng
    assert out and out[0]["suggested_multiplier"] == 1.15


def test_ai_ask_blocked_when_assistant_disabled(monkeypatch):
    monkeypatch.setattr(ai_service, "require_enabled",
                        lambda k, m: (_ for _ in ()).throw(HTTPException(status_code=403, detail=m)))
    with pytest.raises(HTTPException) as e:
        ai_service.ask("phòng tối dưới 300k", 5)
    assert e.value.status_code == 403


# ----------------------------------------------------------------- ảnh
def _png_b64(size=(64, 48), color=(120, 90, 60)):
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def test_decode_image_accepts_data_url_and_rejects_garbage():
    raw, img, fmt = photos.decode_image("data:image/png;base64," + _png_b64())
    assert fmt == "PNG" and img.size == (64, 48)
    for bad in ("not base64!!!", base64.b64encode(b"hello world, not an image").decode()):
        with pytest.raises(HTTPException) as e:
            photos.decode_image(bad)
        assert e.value.status_code == 400


def test_decode_image_rejects_oversize(monkeypatch):
    monkeypatch.setattr(photos, "MAX_BYTES", 100)
    with pytest.raises(HTTPException) as e:
        photos.decode_image(_png_b64((300, 300)))
    assert e.value.status_code == 413


@pytest.mark.parametrize("mode", ["restore", "enhance", "negative"])
def test_restore_modes_return_rgb_image(mode):
    from PIL import Image
    out = photos.restore_image(Image.new("RGB", (50, 40), (200, 180, 160)), mode)
    assert out.mode == "RGB" and out.width >= 50
    if mode == "enhance":
        assert out.width == 100            # ảnh nhỏ được phóng 2 lần


def test_negative_inverts_dark_to_light():
    from PIL import Image
    px = Image.new("RGB", (10, 10), (20, 20, 20))
    px.putpixel((0, 0), (240, 240, 240))
    out = photos.restore_image(px, "negative")
    assert out.getpixel((5, 5))[0] > out.getpixel((0, 0))[0]


def test_add_photo_saves_file_and_cleans_up_on_db_error(db, tmp_path, monkeypatch):
    monkeypatch.setattr(photos, "UPLOAD_DIR", tmp_path)
    db([(r"SELECT owner_id FROM dbo.PhotoCollections", ["owner_id"], [(9,)]),
        (r"INSERT INTO dbo.Photos", None, sql_error("conflict"))])
    with pytest.raises(HTTPException):
        photos.add_photo(CUSTOMER, 1, _png_b64(), "x")
    assert list(tmp_path.rglob("*.png")) == []              # DB lỗi thì không để lại file mồ côi


def test_add_photo_other_users_collection_404(db, tmp_path, monkeypatch):
    monkeypatch.setattr(photos, "UPLOAD_DIR", tmp_path)
    db([(r"SELECT owner_id FROM dbo.PhotoCollections", ["owner_id"], [(77,)])])
    with pytest.raises(HTTPException) as e:
        photos.add_photo(CUSTOMER, 1, _png_b64(), None)
    assert e.value.status_code == 404 and list(tmp_path.rglob("*")) == []


def test_restore_photo_creates_new_restored_photo(db, tmp_path, monkeypatch):
    monkeypatch.setattr(photos, "UPLOAD_DIR", tmp_path)
    monkeypatch.setattr("core.platform_settings.get_setting", lambda k, d=None: True)
    src = tmp_path / "9" / "orig.png"
    src.parent.mkdir()
    src.write_bytes(base64.b64decode(_png_b64()))
    conn = db([(r"SCOPE_IDENTITY", ["id"], [(5,)]),
               (r"FROM dbo.Photos p JOIN dbo.PhotoCollections", ["photo_id", "collection_id", "file_path", "caption", "kind"],
                [(4, 1, "9/orig.png", "Ảnh cũ", "ORIGINAL")]),
               (r"WHERE photo_id = \?", ["photo_id", "file_path", "kind"], [(5, "9/new.jpg", "RESTORED")])])
    out = photos.restore_photo(CUSTOMER, 4, "restore")
    insert = conn.cur.sqls("INSERT INTO dbo.Photos")[0]
    assert "'RESTORED'" in insert[0] and insert[1][0] == 1 and "(phục hồi ảnh cũ)" in insert[1][2]
    assert out["url"] == "/uploads/9/new.jpg" and src.exists()      # ảnh gốc còn nguyên
    assert len(list(tmp_path.rglob("*.jpg"))) == 1


def test_restore_photo_invalid_mode():
    with pytest.raises(HTTPException) as e:
        photos.restore_photo(CUSTOMER, 1, "magic")
    assert e.value.status_code == 400


def test_remove_file_refuses_path_traversal(tmp_path, monkeypatch):
    monkeypatch.setattr(photos, "UPLOAD_DIR", tmp_path / "up")
    (tmp_path / "up").mkdir()
    victim = tmp_path / "secret.txt"
    victim.write_text("x")
    photos._remove_file("../secret.txt")
    assert victim.exists()


# ------------------------------------------------------------------ chia sẻ bộ sưu tập
def test_share_collection_generates_token(db):
    conn = db([(r"SELECT owner_id FROM dbo.PhotoCollections", ["owner_id"], [(9,)]),
               (r"SELECT share_token FROM dbo.PhotoCollections", ["share_token"], [(None,)])])
    out = photos.set_sharing(CUSTOMER, 1, True)
    assert out["shared"] and 16 <= len(out["share_token"]) <= 22
    assert out["share_path"] == "/api/collections/shared/" + out["share_token"]
    assert conn.cur.sqls("UPDATE dbo.PhotoCollections SET share_token = ?")


def test_share_keeps_existing_token(db):
    db([(r"SELECT owner_id FROM dbo.PhotoCollections", ["owner_id"], [(9,)]),
        (r"SELECT share_token FROM dbo.PhotoCollections", ["share_token"], [("abc123",)])])
    assert photos.set_sharing(CUSTOMER, 1, True)["share_token"] == "abc123"


def test_unshare_clears_token(db):
    conn = db([(r"SELECT owner_id FROM dbo.PhotoCollections", ["owner_id"], [(9,)])])
    out = photos.set_sharing(CUSTOMER, 1, False)
    assert out == {"collection_id": 1, "shared": False, "share_token": None, "share_path": None}
    assert conn.cur.sqls("share_token = NULL")


def test_share_other_users_collection_404(db):
    db([(r"SELECT owner_id FROM dbo.PhotoCollections", ["owner_id"], [(77,)])])
    with pytest.raises(HTTPException) as e:
        photos.set_sharing(CUSTOMER, 1, True)
    assert e.value.status_code == 404


def test_shared_collection_unknown_token_404(db):
    db([(r"WHERE c.share_token = \?", ["collection_id", "name", "description", "owner_name"], [])])
    with pytest.raises(HTTPException) as e:
        photos.shared_collection("khong-co")
    assert e.value.status_code == 404


def test_shared_collection_hides_internal_id(db):
    db([(r"WHERE c.share_token = \?", ["collection_id", "name", "description", "owner_name"], [(1, "Phim 2026", None, "An")]),
        (r"FROM dbo.Photos WHERE collection_id", ["photo_id", "collection_id", "file_path", "caption", "kind"],
         [(3, 1, "9/a.jpg", None, "ORIGINAL")])])
    out = photos.shared_collection("tok")
    assert "collection_id" not in out and out["photos"][0]["url"] == "/uploads/9/a.jpg"
