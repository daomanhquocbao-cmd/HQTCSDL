"""Test API booking - mock tầng service nên không cần SQL Server."""
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from booking import service
from booking.auth import create_access_token
from booking.schemas import BookingCreate
from main import app

client = TestClient(app)


def _headers(user_id=1, role="customer"):
    return {"Authorization": f"Bearer {create_access_token(user_id, role)}"}


def _payload(**over):
    start = datetime.now() + timedelta(days=1)
    data = {
        "room_id": 1,
        "start_time": start.isoformat(),
        "end_time": (start + timedelta(hours=2)).isoformat(),
        "note": "Chụp ảnh cưới",
    }
    data.update(over)
    return data


def _fake_booking(**over):
    start = datetime.now() + timedelta(days=1)
    data = {
        "booking_id": 10, "user_id": 1, "room_id": 1,
        "start_time": start, "end_time": start + timedelta(hours=2),
        "status": "pending", "note": None,
    }
    data.update(over)
    return data


def test_invalid_token_returns_401():
    r = client.post("/api/bookings", json=_payload(), headers={"Authorization": "Bearer abc"})
    assert r.status_code == 401


def test_create_booking_invalid_body_returns_422():
    r = client.post("/api/bookings", json={}, headers=_headers())
    assert r.status_code == 422


def test_create_booking_end_before_start_returns_422():
    start = datetime.now() + timedelta(days=1)
    r = client.post(
        "/api/bookings",
        json=_payload(end_time=(start - timedelta(hours=1)).isoformat(), start_time=start.isoformat()),
        headers=_headers(),
    )
    assert r.status_code == 422


def test_create_booking_success(monkeypatch):
    monkeypatch.setattr(service, "create_booking", lambda uid, data: _fake_booking(user_id=uid))
    r = client.post("/api/bookings", json=_payload(), headers=_headers(5))
    assert r.status_code == 201
    assert r.json()["user_id"] == 5


def test_create_booking_conflict(monkeypatch):
    def boom(uid, data):
        raise service.TimeConflictError("Khung giờ này đã có người đặt")
    monkeypatch.setattr(service, "create_booking", boom)
    r = client.post("/api/bookings", json=_payload(), headers=_headers())
    assert r.status_code == 409


def test_create_booking_room_not_found(monkeypatch):
    def boom(uid, data):
        raise service.RoomNotFoundError("Phòng không tồn tại")
    monkeypatch.setattr(service, "create_booking", boom)
    r = client.post("/api/bookings", json=_payload(room_id=999), headers=_headers())
    assert r.status_code == 404


def test_list_my_bookings(monkeypatch):
    monkeypatch.setattr(service, "list_my_bookings", lambda uid, st=None: [_fake_booking()])
    r = client.get("/api/bookings", headers=_headers())
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_get_booking_forbidden(monkeypatch):
    def boom(bid, uid, role):
        raise service.PermissionDeniedError("Không có quyền")
    monkeypatch.setattr(service, "get_booking", boom)
    r = client.get("/api/bookings/10", headers=_headers())
    assert r.status_code == 403


def test_cancel_booking_success(monkeypatch):
    monkeypatch.setattr(
        service, "cancel_booking", lambda bid, uid, role: _fake_booking(status="cancelled")
    )
    r = client.patch("/api/bookings/10/cancel", headers=_headers())
    assert r.status_code == 200
    assert r.json()["status"] == "cancelled"


def test_cancel_booking_already_cancelled(monkeypatch):
    def boom(bid, uid, role):
        raise service.InvalidStateError("Booking đã bị hủy")
    monkeypatch.setattr(service, "cancel_booking", boom)
    r = client.patch("/api/bookings/10/cancel", headers=_headers())
    assert r.status_code == 400


def test_schema_rejects_invalid_range():
    now = datetime.now()
    with pytest.raises(ValidationError):
        BookingCreate(room_id=1, start_time=now, end_time=now)
