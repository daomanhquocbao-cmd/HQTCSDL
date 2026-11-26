"""Phân quyền và kiểm tra đầu vào của /api/customer, /api/collections, /api/admin (phần mới)."""
import pytest

from core.security import create_access_token
from customer import service as customer_service


def headers(role: str, uid: int = 9) -> dict:
    return {"Authorization": f"Bearer {create_access_token(uid, role)}"}


CUSTOMER_PROTECTED = [
    ("get", "/api/customer/overview"),
    ("get", "/api/customer/bookings"),
    ("get", "/api/customer/bookings/1"),
    ("post", "/api/customer/bookings/1/cancel"),
    ("get", "/api/collections"),
    ("get", "/api/collections/1/photos"),
    ("delete", "/api/collections/photos/1"),
]

ADMIN_ONLY = [
    ("get", "/api/admin/users"),
    ("get", "/api/admin/payments"),
    ("post", "/api/admin/payments/1/refund"),
    ("get", "/api/admin/settings"),
    ("get", "/api/admin/reports"),
]


@pytest.mark.parametrize("method,path", CUSTOMER_PROTECTED)
def test_requires_login(client, method, path):
    assert getattr(client, method)(path).status_code == 401


@pytest.mark.parametrize("method,path", ADMIN_ONLY)
def test_admin_endpoints_forbidden_for_customer(client, method, path):
    assert getattr(client, method)(path, headers=headers("CUSTOMER")).status_code == 403


def test_public_search_does_not_need_login(client, monkeypatch):
    monkeypatch.setattr(customer_service, "search_rooms", lambda *a, **k: [{"room_id": 1}])
    r = client.get("/api/customer/rooms?q=vintage&sort=price_asc")
    assert r.status_code == 200 and r.json() == [{"room_id": 1}]


def test_search_rejects_bad_sort_and_half_time_range(client):
    assert client.get("/api/customer/rooms?sort=hack").status_code == 422
    assert client.get("/api/customer/rooms?start_time=2026-12-01T09:00:00").status_code == 422


def test_payment_body_is_validated(client):
    h = headers("CUSTOMER")
    assert client.post("/api/customer/bookings/1/payments", json={"amount": -5, "payment_method": "CASH"}, headers=h).status_code == 422
    assert client.post("/api/customer/bookings/1/payments", json={"amount": 5, "payment_method": "BITCOIN"}, headers=h).status_code == 422


def test_photo_upload_rejects_non_image_before_db(client):
    r = client.post("/api/collections/1/photos", json={"data": "aGVsbG8gd29ybGQgbm90IGFuIGltYWdl"}, headers=headers("CUSTOMER"))
    assert r.status_code == 400


def test_admin_setting_body_required(client):
    assert client.put("/api/admin/settings/x", json={}, headers=headers("ADMIN", 1)).status_code == 422
