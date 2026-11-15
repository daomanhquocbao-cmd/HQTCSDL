from datetime import datetime, timedelta, timezone
from jose import jwt

from core.security import JWT_ALGORITHM, JWT_SECRET, create_access_token
from users import service


def _user(role="CUSTOMER", status="ACTIVE"):
    return {
        "user_id": 1,
        "username": "nguyenvana",
        "email": "a@example.com",
        "full_name": "Nguyễn Văn A",
        "phone": "0901234567",
        "role": role,
        "status": status,
    }


REGISTER = {
    "username": "nguyenvana",
    "email": "a@example.com",
    "password": "12345678",
    "full_name": "Nguyễn Văn A",
    "phone": "0901234567",
    "role": "CUSTOMER",
}


def test_register_success(client, monkeypatch):
    monkeypatch.setattr(service, "register_user", lambda **kwargs: _user(role=kwargs.get("role", "CUSTOMER")))
    r = client.post("/api/users/register", json=REGISTER)
    assert r.status_code == 201
    assert r.json()["role"] == "CUSTOMER"
    assert r.json()["full_name"] == "Nguyễn Văn A"


def test_register_cannot_self_assign_admin(client):
    r = client.post("/api/users/register", json={**REGISTER, "role": "ADMIN"})
    assert r.status_code == 422


def test_register_duplicate(client, monkeypatch):
    def boom(**kwargs):
        raise service.DuplicateUserError("Username hoặc email đã được đăng ký")

    monkeypatch.setattr(service, "register_user", boom)
    assert client.post("/api/users/register", json=REGISTER).status_code == 409


def test_register_short_password(client):
    assert client.post("/api/users/register", json={**REGISTER, "password": "123"}).status_code == 422


def test_register_invalid_email(client):
    assert client.post("/api/users/register", json={**REGISTER, "email": "abc"}).status_code == 422


def test_register_invalid_username(client):
    assert client.post("/api/users/register", json={**REGISTER, "username": "a b"}).status_code == 422


def test_login_success(client, monkeypatch):
    monkeypatch.setattr(service, "authenticate", lambda u, p: _user())
    r = client.post("/api/users/login", json={"username": "nguyenvana", "password": "12345678"})
    assert r.status_code == 200
    body = r.json()
    assert body["access_token"]
    assert body["user"]["username"] == "nguyenvana"


def test_login_wrong_credentials(client, monkeypatch):
    def boom(u, p):
        raise service.InvalidCredentialsError("Username hoặc mật khẩu không đúng")

    monkeypatch.setattr(service, "authenticate", boom)
    assert client.post("/api/users/login", json={"username": "x", "password": "y"}).status_code == 401


def test_login_suspended_account(client, monkeypatch):
    def boom(u, p):
        raise service.AccountLockedError("Tài khoản đã bị khóa")

    monkeypatch.setattr(service, "authenticate", boom)
    assert client.post("/api/users/login", json={"username": "nguyenvana", "password": "12345678"}).status_code == 403


def test_me_requires_token(client):
    assert client.get("/api/users/me").status_code in (401, 403)


def test_me_invalid_token(client):
    r = client.get("/api/users/me", headers={"Authorization": "Bearer token-gia-mao-khong-hop-le"})
    assert r.status_code == 401


def test_me_expired_token(client):
    expired_payload = {
        "sub": "1",
        "role": "CUSTOMER",
        "exp": datetime.now(timezone.utc) - timedelta(minutes=10),
    }
    expired_token = jwt.encode(expired_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    r = client.get("/api/users/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert r.status_code == 401


def test_me_success(client, monkeypatch, user_headers):
    monkeypatch.setattr(service, "get_user", lambda uid: _user())
    r = client.get("/api/users/me", headers=user_headers)
    assert r.status_code == 200 and r.json()["user_id"] == 1


def test_rbac_customer_forbidden_on_admin_and_provider_routes(client, user_headers):
    # CUSTOMER gọi API chỉ dành cho ADMIN (/api/stats/summary) -> phải bị chặn 403
    r_admin = client.get("/api/stats/summary", headers=user_headers)
    assert r_admin.status_code == 403

    # CUSTOMER gọi API chỉ dành cho PROVIDER/ADMIN (/api/provider/overview) -> phải bị chặn 403
    r_provider = client.get("/api/provider/overview", headers=user_headers)
    assert r_provider.status_code == 403


def test_rbac_customer_forbidden_on_create_workshop(client, user_headers):
    # CUSTOMER tạo workshop (chỉ EXPERT/ADMIN được phép) -> phải bị chặn 403
    payload = {
        "title": "Tráng phim đen trắng cơ bản",
        "description": "Hướng dẫn phòng tối",
        "capacity": 10,
        "start_time": "2026-12-01T09:00:00",
        "end_time": "2026-12-01T12:00:00",
    }
    r = client.post("/api/workshops", json=payload, headers=user_headers)
    assert r.status_code == 403
