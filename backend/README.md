# Backend – Booking System API (FastAPI + SQL Server)

## Yêu cầu
- Python 3.11
- SQL Server (hoặc Docker)
- ODBC Driver 17 for SQL Server

## 1. Tạo database
Mở SSMS hoặc Azure Data Studio, chạy lần lượt trong thư mục `../database/`:
1. `01_create_tables.sql`
2. `02_seed_data.sql`
3. `03_stored_procedures.sql`
4. `06_provider_additions.sql` (cột lý do hủy)
5. `07_pricing_promotions_ai.sql` (giá động, khuyến mãi, gợi ý AI)
6. `08_collections_settings_ledger.sql` (bộ sưu tập ảnh, cấu hình admin, sổ giao dịch, hoàn tiền)
7. `09_backup_recovery.sql` (sao lưu / khôi phục; cần tạo thư mục `C:\SQLBackups` trước khi chạy thử)

Ảnh khách tải lên lưu ở `backend/uploads/` (đã nằm trong `.gitignore`). Phục hồi ảnh cần `Pillow` (có trong `requirements.txt`).

Kiểm tra đặt phòng đồng thời: `python scripts/concurrency_test.py --room 1 --customer 5 --threads 12` (đúng thiết kế thì chỉ 1 luồng thành công).
5. `07_pricing_promotions_ai.sql` (giá theo khung giờ, khuyến mãi, AI, phân tích). Nếu chạy lại 03 thì phải chạy lại 07.

(Các file 04, 05 và 06_performance_demo là truy vấn báo cáo, dữ liệu lớn và demo hiệu năng, chạy sau nếu cần.)

## 2. Cài đặt
```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```
Mở `.env`, sửa `DB_SERVER`, `DB_USER`, `DB_PASSWORD` cho đúng máy bạn.

## 3. Chạy
```bash
uvicorn app_full:app --reload
```
- API: http://localhost:8000
- Swagger (thử API): http://localhost:8000/docs
- Giao diện: http://localhost:8000/web/provider/provider-login.html

## Chạy bằng Docker
```bash
docker compose up --build
```
Sau khi container `db` lên, vẫn phải chạy các script trong `database/` vào SQL Server (cổng 1433).

## Chạy test
```bash
pytest
```

## Cấu trúc thư mục
| Thư mục | Nội dung |
|---|---|
| `core/` | cấu hình, bảo mật JWT, middleware, xử lý lỗi |
| `users/` | đăng ký, đăng nhập |
| `studios/`, `rooms/` | studio, phòng |
| `booking/` | đặt phòng (gọi stored procedure) |
| `workshops/` | workshop |
| `provider/` | API cho chủ studio |
| `stats/` | thống kê (ADMIN) |
| `tests/` | test tự động |

## Lỗi thường gặp
- **`Data source name not found` / `Can't open lib 'ODBC Driver 17'`**: chưa cài ODBC Driver 17.
- **`Login failed for user 'sa'`**: sai `DB_PASSWORD` trong `.env`.
- **Frontend báo lỗi CORS**: thêm địa chỉ frontend vào `CORS_ORIGINS`.
- **401 hoặc 403**: thiếu header `Authorization: Bearer <token>`; token lấy từ `POST /api/users/login`.
