from datetime import datetime, timedelta

from booking.auth import create_access_token
from workshops import service


def _workshop(**over):
    start = datetime.now() + timedelta(days=7)
    data = {"workshop_id": 1, "expert_id": 3, "expert_name": "expert1", "title": "Tráng phim B&W",
            "description": None, "capacity": 20, "registered": 5, "remaining_slots": 15,
            "start_time": start, "end_time": start + timedelta(hours=3)}
    data.update(over)
    return data


def _payload(**over):
    start = datetime.now() + timedelta(days=7)
    data = {"title": "Tráng phim B&W", "capacity": 20,
            "start_time": start.isoformat(), "end_time": (start + timedelta(hours=3)).isoformat()}
    data.update(over)
    return data


def _expert(uid=3):
    return {"Authorization": f"Bearer {create_access_token(uid, 'EXPERT')}"}


def test_list_workshops_public(client, monkeypatch):
    monkeypatch.setattr(service, "list_workshops", lambda up, limit, offset: [_workshop()])
    r = client.get("/api/workshops?upcoming_only=true")
    assert r.status_code == 200 and r.json()[0]["remaining_slots"] == 15


def test_get_workshop_not_found(client, monkeypatch):
    def boom(wid):
        raise service.WorkshopNotFoundError("Workshop không tồn tại")
    monkeypatch.setattr(service, "get_workshop", boom)
    assert client.get("/api/workshops/999").status_code == 404


def test_create_workshop_customer_forbidden(client, user_headers):
    assert client.post("/api/workshops", json=_payload(), headers=user_headers).status_code == 403


def test_create_workshop_as_expert(client, monkeypatch):
    monkeypatch.setattr(service, "create_workshop", lambda eid, *a: _workshop(expert_id=eid))
    r = client.post("/api/workshops", json=_payload(), headers=_expert(3))
    assert r.status_code == 201 and r.json()["expert_id"] == 3


def test_create_workshop_bad_time_range(client):
    start = datetime.now() + timedelta(days=7)
    bad = _payload(end_time=(start - timedelta(hours=1)).isoformat(), start_time=start.isoformat())
    assert client.post("/api/workshops", json=bad, headers=_expert()).status_code == 422


def test_register_requires_login(client):
    assert client.post("/api/workshops/1/register").status_code == 403


def test_register_success(client, monkeypatch, user_headers):
    monkeypatch.setattr(service, "register", lambda wid, cid: {
        "workshop_id": wid, "customer_id": cid, "message": "ok"})
    r = client.post("/api/workshops/1/register", headers=user_headers)
    assert r.status_code == 201 and r.json()["customer_id"] == 1


def test_register_duplicate(client, monkeypatch, user_headers):
    def boom(wid, cid):
        raise service.AlreadyRegisteredError("Bạn đã đăng ký")
    monkeypatch.setattr(service, "register", boom)
    assert client.post("/api/workshops/1/register", headers=user_headers).status_code == 409


def test_register_full(client, monkeypatch, user_headers):
    def boom(wid, cid):
        raise service.WorkshopFullError("Hết chỗ")
    monkeypatch.setattr(service, "register", boom)
    assert client.post("/api/workshops/1/register", headers=user_headers).status_code == 409


def test_unregister(client, monkeypatch, user_headers):
    monkeypatch.setattr(service, "unregister", lambda wid, cid: None)
    assert client.delete("/api/workshops/1/register", headers=user_headers).status_code == 204


def test_my_registrations(client, monkeypatch, user_headers):
    monkeypatch.setattr(service, "list_my_workshops", lambda cid: [_workshop()])
    assert client.get("/api/workshops/me/registrations", headers=user_headers).status_code == 200


def test_db_error_extraction():
    from core.db_errors import extract_message
    err = Exception("('42000', '[42000] [Microsoft][ODBC Driver 17 for SQL Server][SQL Server]"
                    "Lỗi: Workshop đã đủ số lượng người tham gia tối đa (Hết chỗ). (50000) (SQLExecDirectW)')")
    assert "Hết chỗ" in extract_message(err)
