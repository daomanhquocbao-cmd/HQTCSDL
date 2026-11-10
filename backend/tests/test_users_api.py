from users import service


def _user():
    return {"user_id": 1, "username": "nguyenvana", "email": "a@example.com", "phone": None, "role": "CUSTOMER"}


REGISTER = {"username": "nguyenvana", "email": "a@example.com", "password": "12345678"}


def test_register_success(client, monkeypatch):
    monkeypatch.setattr(service, "register_user", lambda u, e, p, ph=None: _user())
    r = client.post("/api/users/register", json=REGISTER)
    assert r.status_code == 201 and r.json()["role"] == "CUSTOMER"


def test_register_duplicate(client, monkeypatch):
    def boom(u, e, p, ph=None):
        raise service.DuplicateUserError("Trùng")
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
    assert r.status_code == 200 and r.json()["access_token"]


def test_login_wrong_credentials(client, monkeypatch):
    def boom(u, p):
        raise service.InvalidCredentialsError("Sai")
    monkeypatch.setattr(service, "authenticate", boom)
    assert client.post("/api/users/login", json={"username": "x", "password": "y"}).status_code == 401


def test_me_requires_token(client):
    assert client.get("/api/users/me").status_code == 403


def test_me_success(client, monkeypatch, user_headers):
    monkeypatch.setattr(service, "get_user", lambda uid: _user())
    r = client.get("/api/users/me", headers=user_headers)
    assert r.status_code == 200 and r.json()["user_id"] == 1
