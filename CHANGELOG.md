# Changelog

## 1.6.0
- **App Flutter đủ 4 vai trò** (`mobile/`): Khách, Nhà cung cấp, Chuyên gia, Quản trị; đăng nhập tự chuyển giao diện theo role
- **Chia sẻ bộ sưu tập** bằng link công khai chỉ đọc (`/api/collections/{id}/share`, `GET /api/collections/shared/{token}`, trang `frontend/customer/shared.html`)
- **Hoa hồng nền tảng** (`platform.commission_percent`, mặc định 10%): báo cáo admin có `commission_total`, `provider_payout`, hoa hồng theo tháng
- `database/13_share_commission_indexes.sql`: cột `share_token`, setting hoa hồng, 5 index bổ sung
- `docs/TEST_CASES.xlsx`: bảng test case theo vai trò kèm sheet tổng hợp
- `.gitignore`: bỏ qua file mật khẩu dev, cache, build Flutter

## 1.5.0
- **Hồ sơ phòng**: thêm thông gió, âm học, chính sách sử dụng (`database/10_room_profile.sql`), có trên form provider và trang chi tiết khách
- **Tối ưu phân bổ tài nguyên** (`provider/scheduler.py`, `GET /api/provider/ai/schedule-optimize`): phát hiện thiếu thiết bị theo khung giờ, gán thiết bị cho đơn, tìm khoảng trống vụn, gợi ý đổi phòng best-fit; thẻ mới ở trang Phân tích
- **OAuth 2.0 Google** (`integrations/google_oauth.py`) và **VNPay sandbox** (`integrations/vnpay.py`: tạo link, return, IPN, idempotent, kiểm tra chữ ký HMAC-SHA512)
- **App Flutter** `mobile/` cho khách hàng; bản đồ Google nhúng ở chi tiết phòng
- `scripts/measure_latency.py` đo thời gian phản hồi; bộ tài liệu `docs/USER_MANUAL.md`, `TECHNICAL.md`, `CAPSTONE_REPORT.md`, `RBL.md`
- Sửa: `POST /api/studios` thiếu `city` (NOT NULL)

## 1.4.0
- **Khách hàng**: giao diện PC/mobile responsive `frontend/customer/customer-pc.html` nối API thật (tìm, lọc, so sánh phòng; xem lịch trống; đặt phòng kèm thiết bị, gói, mã giảm giá; thanh toán; hủy; đánh giá; khiếu nại; mã QR check-in; cộng đồng; workshop; hồ sơ) thay cho bản tĩnh `customer_PC.html`
- **Bộ sưu tập ảnh + phục hồi ảnh** (`/api/collections`, bảng ở file 08, Pillow): phục hồi ảnh cũ, tăng chất lượng ảnh scan, đảo âm bản
- **Quản trị**: trang riêng `frontend/admin/admin-pc.html` (duyệt nhà cung cấp/cơ sở, người dùng, sổ giao dịch + hoàn tiền, khiếu nại, kiểm duyệt bài, cấu hình AI, báo cáo toàn hệ thống); cấu hình thực sự điều khiển AI, ngưỡng giá, số giờ tối đa mỗi đơn, chế độ bảo trì
- **Chuyên gia**: trang `frontend/expert/expert-pc.html` (tạo workshop, viết bài / review thiết bị, trả lời thảo luận)
- **AI**: tìm kiếm kho kiến thức (đồng nghĩa + TF-IDF), trợ lý trả lời kèm bài viết liên quan, gợi ý thiết bị / gói theo phòng
- **CSDL**: `09_backup_recovery.sql` (mô hình FULL, `sp_BackupDatabase` FULL/DIFF/LOG, quy trình khôi phục, lịch tự động); `scripts/concurrency_test.py`
- Sửa: `08_collections_settings_ledger.sql` dùng nhầm tên database; đánh giá studio thiếu `reservation_id`; danh sách studio/phòng công khai chỉ hiện studio đã duyệt
- Đăng ký có thể chọn vai trò Chuyên gia; đăng nhập chuyển trang theo vai trò

## 1.3.0
- Provider: phân tích tỉ lệ lấp đầy, hiệu suất thiết bị, dự báo nhu cầu, chính sách giá theo khung giờ, khuyến mãi (`database/07`)
- Admin duyệt nhà cung cấp và cơ sở; cộng đồng; gợi ý phòng AI; báo giá

## 1.2.0
- Provider frontend (PC + mobile) và `/api/provider/*` khớp CSDL; `06_provider_additions.sql`

## 1.1.0
- Cập nhật database: thêm `sp_RegisterWorkshop`, báo cáo 04 mới, dữ liệu mẫu ~10 triệu đơn
- Thêm module workshops (danh sách, đăng ký qua stored procedure, hủy đăng ký)
- Thêm `07_indexes.sql` để truy vấn nhanh trên bảng 10 triệu dòng
- Khớp code với database thật (Users, Studios, Rooms, Reservations, Reviews, Payments...)
- Đặt phòng gọi stored procedure `sp_CreateReservation`; đổi trạng thái gọi `sp_UpdateReservationStatus` (ghi ReservationStatusHistory)
- Thêm module users (đăng ký/đăng nhập JWT), studios + reviews, rooms (CRUD, tìm phòng trống), stats
- Phân quyền theo role ADMIN / PROVIDER / CUSTOMER
- Thêm 04_business_queries.sql (13 truy vấn báo cáo)
- Thêm CORS, logging, middleware đo thời gian, xử lý lỗi chung
- Thêm Dockerfile, docker-compose, GitHub Actions CI

## 1.0.0
- Module booking: tạo / xem / hủy đơn, chống trùng giờ
