from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["message"] == "Backend API Booking System đang chạy thành công!"

def test_create_booking_missing_fields():
    # Gửi request thiếu room_id và không truyền token để kiểm tra lỗi 401 từ middleware auth
    response = client.post(
        "/api/bookings",
        json={}
    )
    assert response.status_code == 403