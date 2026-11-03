# Booking System API (FastAPI + SQL Server)

Backend đặt phòng/studio cho nền tảng Film & Photography.

## Cấu trúc
```
├── main.py              # Khởi tạo FastAPI app
├── database.py          # Kết nối SQL Server (pyodbc)
├── schema.sql           # Tạo database + bảng
├── booking/
│   ├── auth.py          # JWT (HTTPBearer)
│   ├── schemas.py       # Pydantic models
│   ├── service.py       # Nghiệp vụ + truy vấn SQL
│   └── router.py        # Endpoint /api/bookings
└── tests/               # pytest (mock service, không cần DB)
```

## Chạy dự án
```bash
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                               # chỉnh thông tin DB
# chạy schema.sql trong SQL Server rồi:
uvicorn main:app --reload
```
Swagger UI: http://localhost:8000/docs

## Endpoint
| Method | Đường dẫn | Mô tả |
|---|---|---|
| POST | /api/bookings | Tạo booking (kiểm tra trùng giờ) |
| GET | /api/bookings?status= | Danh sách booking của tôi |
| GET | /api/bookings/{id} | Xem chi tiết |
| PATCH | /api/bookings/{id}/cancel | Hủy booking |

Tất cả cần header `Authorization: Bearer <JWT>`.

## Test
```bash
pytest -v
```

## Bản đầy đủ (v1.1.0)
`main.py` chỉ có module booking. Bản đầy đủ (users, rooms, stats, CORS, logging) chạy bằng:
```bash
uvicorn app_full:app --reload
```
Thứ tự chạy SQL: `schema.sql` → `migrations/002_add_password_and_room_fields.sql` → `seed.sql`.
Chạy bằng Docker: `docker compose up --build`. Chi tiết endpoint xem `docs/API.md`.
