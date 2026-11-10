from datetime import datetime, timedelta

from booking.auth import create_access_token
from rooms import service


def _room(**over):
    data = {"room_id": 1, "studio_id": 5, "name": "Studio A", "room_type": "STUDIO", "capacity": 10,
            "price_per_hour": 200000.0, "description": None, "status": "AVAILABLE"}
    data.update(over)
    return data


NEW_ROOM = {"studio_id": 5, "name": "Studio B", "room_type": "STUDIO", "capacity": 8, "price_per_hour": 300000}


def _provider(uid):
    return {"Authorization": f"Bearer {create_access_token(uid, 'PROVIDER')}"}


def test_list_rooms_is_public(client, monkeypatch):
    monkeypatch.setattr(service, "list_rooms", lambda **kw: [_room()])
    r = client.get("/api/rooms")
    assert r.status_code == 200 and r.json()[0]["name"] == "Studio A"


def test_list_rooms_invalid_type(client):
    assert client.get("/api/rooms?room_type=GARAGE").status_code == 422


def test_get_room_not_found(client, monkeypatch):
    def boom(rid):
        raise service.RoomNotFoundError("Không tìm thấy phòng")
    monkeypatch.setattr(service, "get_room", boom)
    assert client.get("/api/rooms/999").status_code == 404


def test_available_rooms(client, monkeypatch):
    monkeypatch.setattr(service, "list_available_rooms", lambda *a, **k: [_room()])
    start = datetime.now() + timedelta(days=1)
    r = client.get("/api/rooms/available", params={
        "start_time": start.isoformat(), "end_time": (start + timedelta(hours=2)).isoformat()})
    assert r.status_code == 200 and len(r.json()) == 1


def test_available_rooms_bad_range(client):
    start = datetime.now() + timedelta(days=1)
    r = client.get("/api/rooms/available", params={
        "start_time": start.isoformat(), "end_time": (start - timedelta(hours=1)).isoformat()})
    assert r.status_code == 400


def test_create_room_customer_forbidden(client, user_headers):
    assert client.post("/api/rooms", json=NEW_ROOM, headers=user_headers).status_code == 403


def test_create_room_as_admin(client, monkeypatch, admin_headers):
    monkeypatch.setattr(service, "create_room", lambda *a, **k: _room(name="Studio B"))
    r = client.post("/api/rooms", json=NEW_ROOM, headers=admin_headers)
    assert r.status_code == 201 and r.json()["name"] == "Studio B"


def test_create_room_provider_owner(client, monkeypatch):
    monkeypatch.setattr(service, "get_studio_provider_id", lambda sid: 7)
    monkeypatch.setattr(service, "create_room", lambda *a, **k: _room())
    assert client.post("/api/rooms", json=NEW_ROOM, headers=_provider(7)).status_code == 201


def test_create_room_provider_not_owner(client, monkeypatch):
    monkeypatch.setattr(service, "get_studio_provider_id", lambda sid: 7)
    assert client.post("/api/rooms", json=NEW_ROOM, headers=_provider(8)).status_code == 403


def test_create_room_invalid_data(client, admin_headers):
    bad = {**NEW_ROOM, "capacity": 0, "room_type": "GARAGE"}
    assert client.post("/api/rooms", json=bad, headers=admin_headers).status_code == 422


def test_update_room_as_admin(client, monkeypatch, admin_headers):
    monkeypatch.setattr(service, "get_room", lambda rid: _room())
    monkeypatch.setattr(service, "update_room", lambda rid, ch: _room(**ch))
    r = client.patch("/api/rooms/1", json={"status": "MAINTENANCE"}, headers=admin_headers)
    assert r.status_code == 200 and r.json()["status"] == "MAINTENANCE"


def test_delete_room_as_admin(client, monkeypatch, admin_headers):
    monkeypatch.setattr(service, "get_room", lambda rid: _room())
    monkeypatch.setattr(service, "deactivate_room", lambda rid: None)
    assert client.delete("/api/rooms/1", headers=admin_headers).status_code == 204
