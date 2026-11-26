# Ghi chú chạy thử trên máy (25/11/2026)

## Môi trường đã chạy được
- Windows, Python **3.15.2** (lệnh `py --version` và `python --version` đều ra 3.15.2).
- Thư viện cài bản mới nhất (xem `backend/requirements.txt`): fastapi 0.165.0, uvicorn 0.54.0, pyodbc 5.5.0, Pillow 13.0.0, pytest 9.2.0, httpx 0.28.1, python-jose 3.5.0.
- Bản ghim cũ (pydantic 2.6.4, pyodbc 5.1.0, Pillow 10.3.0) không dùng cho 3.15, nên `requirements.txt` đã đổi sang `>=`.

## Cách chạy backend
Trong thư mục `backend` (PowerShell):
```
python -m pip install -r requirements.txt
python -m uvicorn app_full:app --reload
```
Dùng `python -m ...` vì `pip` và `uvicorn` chưa nằm trong PATH. Cảnh báo "Scripts ... is not on PATH" là bình thường, bỏ qua được.
Thành công khi thấy: `Uvicorn running on http://127.0.0.1:8000`.

Nếu máy khác không cài được: cài Python 3.12, `py -3.12 -m venv venv`, `.\venv\Scripts\Activate.ps1`, rồi chạy lại hai lệnh trên.

## Cơ sở dữ liệu đã chạy
`01, 02, 03, 06_provider_additions, 07, 08, 09, 10` không báo lỗi T-SQL. Mật khẩu thử: `12_dev_passwords_by_prefix.sql` (admin `Adm@1234`, expert `Exp@1234`, provider `Pro@1234`, customer `Cus@1234`). Chỉ dùng trên máy thử.

## Đã làm / còn lại
- [x] Chạy `08, 09, 10` không lỗi
- [x] Backend lên được (`127.0.0.1:8000`)
- [ ] Bấm thử từng màn hình web theo vai trò
- [ ] `python -m pytest`
- [ ] Flutter: `flutter create ... .`, `flutter analyze`
- [ ] `concurrency_test.py`, `measure_latency.py`, `06_performance_demo.sql`, thử sao lưu/khôi phục `09`
- [ ] Điền các mục [ĐIỀN] trong `docs/CAPSTONE_REPORT.md`

## Không đưa lên GitHub
`.env`, `11_dev_passwords.sql`, `12_dev_passwords_by_prefix.sql`, `backend/uploads/`, `__pycache__/`, `venv/`.

