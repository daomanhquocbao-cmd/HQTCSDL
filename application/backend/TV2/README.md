# Booking System API (FastAPI + SQL Server)

Backend cho nền tảng đặt phòng Studio / Phòng tối (Film Photography Platform).

## Cấu trúc
```
├── main.py              # App gốc (chỉ module booking)
├── app_full.py          # App đầy đủ: users, studios, rooms, bookings, stats
├── database.py          # Kết nối SQL Server (pyodbc)
├── sql/                 # 01 tạo bảng, 02 dữ liệu mẫu, 03 stored procedure, 04 báo cáo,
│                        # 05 procedure đổi trạng thái đơn, 06 báo cáo bổ sung, 07 index
├── core/                # config, bảo mật, logging, middleware, phân quyền
├── booking/ users/ rooms/ studios/ workshops/ stats/   # router + service + schemas mỗi module
├── tests/               # pytest (mock service, không cần DB)
├── docs/API.md          # Danh sách endpoint
├── Dockerfile, docker-compose.yml, .github/workflows/ci.yml
```

## Cài đặt database
Chạy lần lượt trong SQL Server Management Studio các file trong `sql/`:
`01_create_tables.sql` → `02_seed_data.sql` (bơm ~10 triệu đơn, chạy khá lâu) → `03_stored_procedures.sql`
→ `05_status_procedure.sql` → `07_indexes.sql`. File `04` và `06` là các truy vấn báo cáo, chạy khi cần xem số liệu.

## Chạy dự án
```bash
python -m venv venv && venv\Scripts\activate      # Mac/Linux: source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                               # chỉnh thông tin DB
uvicorn app_full:app --reload
```
Swagger UI: http://localhost:8000/docs · Docker: `docker compose up --build`

## Test
```bash
pytest
```
