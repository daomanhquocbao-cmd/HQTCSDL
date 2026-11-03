"""Test API đặt phòng - mock tầng service nên không cần SQL Server."""
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from booking import service
from booking.auth import create_access_token
from booking.schemas import BookingCreate
from main import app

client = TestClient(app)


def _headers(user_id=1, role="CUSTOMER"):
    return {"Authorization": f"Bearer {create_access_token(user_id, role)}"}


def _payload(**over):
    start = datetime.now() + timedelta(days=1)
    data = {
        "room_id": 1,
        "start_time": start.isoformat(),
        "end_time": (start + timedelta(hours=2)).isoformat(),
        "customer_note": "Chụp ảnh cưới",
    }
    data.update(over)
    return data


def _fake_booking(**over):
    start = datetime.now() + timedelta(days=1)
    data = {
        "reservation_id": 10, "room_id": 1, "customer_id": 1,
        "start_time": start, "end_time": start + timedelta(hours=2),
        "total_amount": 400000.0, "customer_note": None, "status": "PENDING",
    }
    data.update(over)
    return data


def test_invalid_token_returns_401():
    r = client.post("/api/bookings", json=_payload(), headers={"Authorization": "Bearer abc"})
    assert r.status_code == 401


def test_create_booking_invalid_body_returns_422():
    assert client.post("/api/bookings", json={}, headers=_headers()).status_code == 422


def test_create_booking_end_before_start_returns_422():
    start = datetime.now() + timedelta(days=1)
    r = client.post("/api/bookings", json=_payload(
        start_time=start.isoformat(), end_time=(start - timedelta(hours=1)).isoformat()), headers=_headers())
    assert r.status_code == 422


def test_create_booking_success(monkeypatch):
    monkeypatch.setattr(service, "create_booking", lambda uid, data: _fake_booking(customer_id=uid))
    r = client.post("/api/bookings", json=_payload(), headers=_headers(5))
    assert r.status_code == 201
    assert r.json()["customer_id"] == 5
    assert r.json()["status"] == "PENDING"


def test_create_booking_conflict(monkeypatch):
    def boom(uid, data):
        raise service.TimeConflictError("Phòng này đã có người đặt")
    monkeypatch.setattr(service, "create_booking", boom)
    assert client.post("/api/bookings", json=_payload(), headers=_headers()).status_code == 409


def test_create_booking_room_not_found(monkeypatch):
    def boom(uid, data):
        raise service.RoomNotFoundError("Không tìm thấy thông tin phòng")
    monkeypatch.setattr(service, "create_booking", boom)
    assert client.post("/api/bookings", json=_payload(room_id=999), headers=_headers()).status_code == 404


def test_list_my_bookings(monkeypatch):
    monkeypatch.setattr(service, "list_my_bookings", lambda uid, st=None, limit=20, offset=0: [_fake_booking()])
    r = client.get("/api/bookings", headers=_headers())
    assert r.status_code == 200 and len(r.json()) == 1


def test_list_my_bookings_invalid_status():
    assert client.get("/api/bookings?status=ABC", headers=_headers()).status_code == 422


def test_get_booking_forbidden(monkeypatch):
    def boom(bid, uid, role):
        raise service.PermissionDeniedError("Không có quyền")
    monkeypatch.setattr(service, "get_booking", boom)
    assert client.get("/api/bookings/10", headers=_headers()).status_code == 403


def test_cancel_booking_success(monkeypatch):
    monkeypatch.setattr(service, "cancel_booking", lambda bid, uid, role: _fake_booking(status="CANCELLED"))
    r = client.patch("/api/bookings/10/cancel", headers=_headers())
    assert r.status_code == 200 and r.json()["status"] == "CANCELLED"


def test_cancel_booking_already_cancelled(monkeypatch):
    def boom(bid, uid, role):
        raise service.InvalidStateError("Đơn đã kết thúc")
    monkeypatch.setattr(service, "cancel_booking", boom)
    assert client.patch("/api/bookings/10/cancel", headers=_headers()).status_code == 400


def test_update_status_requires_admin():
    r = client.patch("/api/bookings/10/status", json={"status": "CONFIRMED"}, headers=_headers())
    assert r.status_code == 403


def test_update_status_as_admin(monkeypatch):
    monkeypatch.setattr(service, "update_booking_status", lambda bid, st, aid: _fake_booking(status=st))
    r = client.patch("/api/bookings/10/status", json={"status": "CONFIRMED"}, headers=_headers(99, "ADMIN"))
    assert r.status_code == 200 and r.json()["status"] == "CONFIRMED"


def test_update_status_invalid_value():
    r = client.patch("/api/bookings/10/status", json={"status": "XYZ"}, headers=_headers(99, "ADMIN"))
    assert r.status_code == 422


def test_schema_rejects_invalid_range():
    now = datetime.now()
    with pytest.raises(ValidationError):
        BookingCreate(room_id=1, start_time=now, end_time=now)


def test_extract_db_error_message():
    err = Exception("('42000', '[42000] [Microsoft][ODBC Driver 17 for SQL Server][SQL Server]"
                    "Lỗi: Phòng này đã có người đặt trong khung giờ bạn chọn. (50000) (SQLExecDirectW)')")
    assert isinstance(service._map_db_error(err), service.TimeConflictError)
