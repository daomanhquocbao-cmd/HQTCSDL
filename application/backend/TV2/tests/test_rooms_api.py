from rooms import service


def _room(**over):
    data = {"room_id": 1, "name": "Studio A", "description": None, "hourly_price": 200000.0, "is_active": True}
    data.update(over)
    return data


def test_list_rooms_is_public(client, monkeypatch):
    monkeypatch.setattr(service, "list_rooms", lambda only_active=True: [_room()])
    r = client.get("/api/rooms")
    assert r.status_code == 200
    assert r.json()[0]["name"] == "Studio A"


def test_get_room_not_found(client, monkeypatch):
    def boom(rid):
        raise service.RoomNotFoundError("Không tìm thấy phòng")
    monkeypatch.setattr(service, "get_room", boom)
    assert client.get("/api/rooms/999").status_code == 404


def test_create_room_requires_admin(client, user_headers):
    r = client.post("/api/rooms", json={"name": "Studio B"}, headers=user_headers)
    assert r.status_code == 403


def test_create_room_as_admin(client, monkeypatch, admin_headers):
    monkeypatch.setattr(service, "create_room", lambda n, d, p: _room(name=n, hourly_price=p))
    r = client.post("/api/rooms", json={"name": "Studio B", "hourly_price": 300000}, headers=admin_headers)
    assert r.status_code == 201
    assert r.json()["name"] == "Studio B"


def test_create_room_negative_price(client, admin_headers):
    r = client.post("/api/rooms", json={"name": "Studio B", "hourly_price": -5}, headers=admin_headers)
    assert r.status_code == 422


def test_update_room_as_admin(client, monkeypatch, admin_headers):
    monkeypatch.setattr(service, "update_room", lambda rid, ch: _room(**ch))
    r = client.patch("/api/rooms/1", json={"name": "Studio Moi"}, headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["name"] == "Studio Moi"


def test_delete_room_as_admin(client, monkeypatch, admin_headers):
    monkeypatch.setattr(service, "deactivate_room", lambda rid: None)
    assert client.delete("/api/rooms/1", headers=admin_headers).status_code == 204
