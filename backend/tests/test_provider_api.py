"""Kiểm tra phân quyền của /api/provider/* (không chạm DB: bị chặn trước khi vào service)."""
import pytest

from core.security import create_access_token

PROTECTED = [
    ("get", "/api/provider/overview"),
    ("get", "/api/provider/studios"),
    ("get", "/api/provider/rooms"),
    ("get", "/api/provider/equipment"),
    ("get", "/api/provider/packages"),
    ("get", "/api/provider/reviews"),
    ("get", "/api/provider/bookings"),
    ("get", "/api/provider/bookings/1"),
]


def headers(role: str) -> dict:
    return {"Authorization": f"Bearer {create_access_token(5, role)}"}


@pytest.mark.parametrize("method,path", PROTECTED)
def test_requires_token(client, method, path):
    assert getattr(client, method)(path).status_code == 401


@pytest.mark.parametrize("method,path", PROTECTED)
def test_customer_is_forbidden(client, method, path):
    assert getattr(client, method)(path, headers=headers("CUSTOMER")).status_code == 403


def test_invalid_body_is_422_before_db(client):
    r = client.post("/api/provider/rooms", json={"name": "x"}, headers=headers("PROVIDER"))
    assert r.status_code == 422
    r = client.post("/api/provider/bookings/1/payments", json={"amount": -5, "payment_method": "CASH"},
                    headers=headers("PROVIDER"))
    assert r.status_code == 422


def test_payment_method_must_match_sql_check(client):
    r = client.post("/api/provider/bookings/1/payments", json={"amount": 1000, "payment_method": "BITCOIN"},
                    headers=headers("PROVIDER"))
    assert r.status_code == 422
