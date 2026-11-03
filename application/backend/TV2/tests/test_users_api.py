from users import service


def _user():
    return {"user_id": 1, "full_name": "Nguyen Van A", "email": "a@example.com", "role": "customer"}


def test_register_success(client, monkeypatch):
    monkeypatch.setattr(service, "register_user", lambda n, e, p: _user())
    r = client.post("/api/users/register",
                    json={"full_name": "Nguyen Van A", "email": "a@example.com", "password": "12345678"})
    assert r.status_code == 201
    assert r.json()["email"] == "a@example.com"


def test_register_duplicate_email(client, monkeypatch):
    def boom(n, e, p):
        raise service.DuplicateEmailError("Email đã được đăng ký")
    monkeypatch.setattr(service, "register_user", boom)
    r = client.post("/api/users/register",
                    json={"full_name": "Nguyen Van A", "email": "a@example.com", "password": "12345678"})
    assert r.status_code == 409


def test_register_short_password(client):
    r = client.post("/api/users/register",
                    json={"full_name": "Nguyen Van A", "email": "a@example.com", "password": "123"})
    assert r.status_code == 422


def test_register_invalid_email(client):
    r = client.post("/api/users/register",
                    json={"full_name": "Nguyen Van A", "email": "khong-phai-email", "password": "12345678"})
    assert r.status_code == 422


def test_login_success(client, monkeypatch):
    monkeypatch.setattr(service, "authenticate", lambda e, p: _user())
    r = client.post("/api/users/login", json={"email": "a@example.com", "password": "12345678"})
    assert r.status_code == 200
    assert r.json()["token_type"] == "bearer"
    assert r.json()["access_token"]


def test_login_wrong_credentials(client, monkeypatch):
    def boom(e, p):
        raise service.InvalidCredentialsError("Sai thông tin")
    monkeypatch.setattr(service, "authenticate", boom)
    r = client.post("/api/users/login", json={"email": "a@example.com", "password": "sai"})
    assert r.status_code == 401


def test_me_requires_token(client):
    assert client.get("/api/users/me").status_code == 403


def test_me_success(client, monkeypatch, user_headers):
    monkeypatch.setattr(service, "get_user", lambda uid: _user())
    r = client.get("/api/users/me", headers=user_headers)
    assert r.status_code == 200
    assert r.json()["user_id"] == 1
