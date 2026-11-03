from studios import service


def _studio(**over):
    data = {"studio_id": 1, "provider_id": 7, "name": "Dark Studio", "address": "1 Nguyen Hue, Q1",
            "description": None, "phone": None, "avg_rating": 4.5, "review_count": 12}
    data.update(over)
    return data


def _review():
    return {"review_id": 1, "studio_id": 1, "customer_id": 1, "rating": 5, "comment": "Tuyệt", "created_at": None}


def test_list_studios_public(client, monkeypatch):
    monkeypatch.setattr(service, "list_studios", lambda limit, offset, keyword: [_studio()])
    r = client.get("/api/studios?keyword=dark")
    assert r.status_code == 200 and r.json()[0]["avg_rating"] == 4.5


def test_list_studios_invalid_limit(client):
    assert client.get("/api/studios?limit=1000").status_code == 422


def test_get_studio_not_found(client, monkeypatch):
    def boom(sid):
        raise service.StudioNotFoundError("Không tìm thấy studio")
    monkeypatch.setattr(service, "get_studio", boom)
    assert client.get("/api/studios/999").status_code == 404


def test_create_studio_customer_forbidden(client, user_headers):
    r = client.post("/api/studios", json={"name": "Studio X", "address": "123 ABC"}, headers=user_headers)
    assert r.status_code == 403


def test_create_studio_as_admin(client, monkeypatch, admin_headers):
    monkeypatch.setattr(service, "create_studio", lambda pid, n, a, d, p: _studio(provider_id=pid, name=n))
    r = client.post("/api/studios", json={"name": "Studio X", "address": "123 ABC"}, headers=admin_headers)
    assert r.status_code == 201 and r.json()["provider_id"] == 99


def test_list_reviews(client, monkeypatch):
    monkeypatch.setattr(service, "list_reviews", lambda sid, limit, offset: [_review()])
    assert client.get("/api/studios/1/reviews").status_code == 200


def test_add_review_requires_login(client):
    assert client.post("/api/studios/1/reviews", json={"rating": 5}).status_code == 403


def test_add_review_success(client, monkeypatch, user_headers):
    monkeypatch.setattr(service, "add_review", lambda sid, cid, rt, cm: _review())
    r = client.post("/api/studios/1/reviews", json={"rating": 5, "comment": "Tuyệt"}, headers=user_headers)
    assert r.status_code == 201


def test_add_review_invalid_rating(client, user_headers):
    assert client.post("/api/studios/1/reviews", json={"rating": 6}, headers=user_headers).status_code == 422
