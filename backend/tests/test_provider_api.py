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
    ("delete", "/api/provider/studios/1"),
    ("get", "/api/provider/disputes"),
    ("get", "/api/provider/workshops"),
    ("get", "/api/provider/analytics/occupancy"),
    ("get", "/api/provider/analytics/heatmap"),
    ("get", "/api/provider/analytics/equipment"),
    ("get", "/api/provider/ai/forecast"),
    ("get", "/api/provider/ai/pricing-suggestions"),
    ("get", "/api/provider/pricing-rules"),
    ("get", "/api/provider/promotions"),
    ("delete", "/api/provider/promotions/1"),
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


def test_pricing_rule_body_validated(client):
    bad = {"studio_id": 1, "name": "x", "start_hour": 10, "end_hour": 9, "multiplier": 1.2}
    assert client.post("/api/provider/pricing-rules", json=bad, headers=headers("PROVIDER")).status_code == 422
    bad = {"studio_id": 1, "code": "AB", "title": "t", "discount_type": "PERCENT", "discount_value": 10,
           "start_date": "2026-01-01", "end_date": "2026-02-01"}
    assert client.post("/api/provider/promotions", json=bad, headers=headers("PROVIDER")).status_code == 422


ADMIN_ONLY = [("get", "/api/admin/overview"), ("get", "/api/admin/providers"), ("get", "/api/admin/studios"),
              ("patch", "/api/admin/providers/5"), ("patch", "/api/admin/studios/1")]


@pytest.mark.parametrize("method,path", ADMIN_ONLY)
def test_admin_endpoints_reject_provider_and_anonymous(client, method, path):
    assert getattr(client, method)(path).status_code == 401
    assert getattr(client, method)(path, headers=headers("PROVIDER")).status_code == 403


def test_community_write_needs_login_and_validates(client):
    assert client.post("/api/community/posts", json={"title": "abc", "content": "x"}).status_code == 401
    r = client.post("/api/community/posts", json={"title": "a", "content": "x"}, headers=headers("CUSTOMER"))
    assert r.status_code == 422
