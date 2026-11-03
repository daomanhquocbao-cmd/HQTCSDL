from stats import service


def test_summary_requires_admin(client, user_headers):
    assert client.get("/api/stats/summary", headers=user_headers).status_code == 403


def test_summary_as_admin(client, monkeypatch, admin_headers):
    monkeypatch.setattr(service, "booking_summary", lambda: {
        "total_reservations": 3, "by_status": {"PENDING": 2, "CANCELLED": 1},
        "users_by_role": {"CUSTOMER": 5}, "total_studios": 2, "available_rooms": 4, "total_revenue": 750000.0})
    r = client.get("/api/stats/summary", headers=admin_headers)
    assert r.status_code == 200 and r.json()["total_reservations"] == 3


def test_health_endpoint(client):
    r = client.get("/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"


def test_process_time_header(client):
    assert "x-process-time-ms" in client.get("/").headers
