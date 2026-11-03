# Hướng dẫn đóng góp

1. Tạo nhánh mới từ `main`: `git checkout -b feature/ten-tinh-nang`
2. Viết code kèm test trong `tests/`; chạy `pytest` phải xanh.
3. Commit rõ ràng, ví dụ: `feat(rooms): thêm API xóa mềm phòng`, `fix(auth): trả 401 khi token hết hạn`.
4. Mở Pull Request, CI (GitHub Actions) phải pass trước khi merge.

Quy ước: tầng `router` chỉ xử lý HTTP, mọi truy vấn SQL nằm trong `service`.
