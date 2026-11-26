# Hướng dẫn sử dụng

Địa chỉ web (chạy cục bộ): `http://127.0.0.1:8000/web/customer/auth.html`. Tài khoản mẫu nằm trong `database/02_seed_data.sql`.

## 1. Khách hàng (Photographer)
1. **Đăng ký / đăng nhập**: trang `auth.html`. Có thể đăng nhập bằng Google nếu server bật. Chọn vai trò *Khách hàng* hoặc *Chuyên gia*.
2. **Tìm phòng**: tab *Khám phá*. Lọc theo loại phòng, thành phố, giá, sức chứa, khung giờ trống; sắp xếp theo đánh giá hoặc giá. Chọn tối đa 3 phòng để **so sánh**.
3. **Xem chi tiết**: diện tích, phong cách, ánh sáng, thông gió, âm học, chính sách sử dụng, thiết bị cho thuê, gói dịch vụ, đánh giá, bản đồ.
4. **Đặt phòng**: chọn ngày, giờ bắt đầu, số giờ. Hệ thống hiện các khung đã có người đặt. Chọn thiết bị/gói (nút *AI gợi ý thêm* đề xuất món hay được thuê cùng), nhập mã khuyến mãi, xem giá tạm tính rồi gửi yêu cầu. Đơn ở trạng thái *Chờ duyệt* đến khi nhà cung cấp xác nhận.
5. **Đơn của tôi**: xem chi tiết, **mã QR check-in** (hiện khi đơn được xác nhận), thanh toán (ghi nhận trực tiếp hoặc VNPay), thêm thiết bị/gói, hủy đơn, đánh giá sau khi hoàn tất, gửi khiếu nại.
6. **Cộng đồng**: đọc bài, bình luận, đăng ký workshop, tìm kiến thức (tìm theo ý nghĩa gần đúng).
7. **Hồ sơ**: tạo bộ sưu tập ảnh, tải ảnh lên; chọn *Phục hồi*, *Tăng chất lượng* hoặc *Đảo âm bản* để tạo bản mới (ảnh gốc được giữ).
8. **Trợ lý AI**: hỏi bằng tiếng Việt như "phòng tối cho 3 người dưới 300k".

## 2. Nhà cung cấp (Provider)
Đăng nhập tại `frontend/provider/provider-login.html`. Tài khoản mới phải được Admin duyệt.
- **Cơ sở và phòng**: tạo studio, thêm phòng với đầy đủ thông số (kích thước, sức chứa, phong cách, ánh sáng, thông gió, âm học, chính sách).
- **Thiết bị**: số lượng, giá thuê, lịch bảo trì; vật tư tiêu hao.
- **Đơn đặt**: duyệt, từ chối, check-in bằng mã QR, check-out, ghi nhận sử dụng.
- **Giá & khuyến mãi**: quy tắc giá theo giờ cao/thấp điểm, mã giảm giá. Trang *Phân tích* gợi ý điều chỉnh giá.
- **Phân tích**: tỉ lệ lấp đầy, bản đồ nhiệt, hiệu suất thiết bị, dự báo 7 ngày, **tối ưu phân bổ** (chọn ngày để xem thiết bị bị thiếu, khoảng trống vụn, gợi ý đổi phòng).

## 3. Chuyên gia (Expert)
`frontend/expert/expert-pc.html`: tạo workshop, viết bài hướng dẫn/review thiết bị, trả lời thảo luận.

## 4. Quản trị (Admin)
`frontend/admin/admin-pc.html`: duyệt nhà cung cấp và cơ sở, quản lý người dùng (khóa/mở), sổ giao dịch và hoàn tiền, xử lý khiếu nại, kiểm duyệt nội dung, **cấu hình hệ thống** (bật/tắt từng chức năng AI, ngưỡng giá, số giờ tối đa mỗi đơn, chế độ bảo trì), báo cáo toàn hệ thống.

## 5. Ứng dụng di động
Xem `mobile/README.md`.

## 6. Xử lý sự cố thường gặp
| Hiện tượng | Cách xử lý |
|---|---|
| Trang báo 503 "chạy file SQL 0x" | Chạy file SQL được nhắc trong SSMS rồi tải lại |
| Không đặt được vì "chế độ bảo trì" | Admin tắt `platform.maintenance_mode` trong Cấu hình |
| Đơn vượt số giờ tối đa | Admin chỉnh `booking.max_hours_per_booking` |
| Không thấy nút Google | Chưa đặt `GOOGLE_CLIENT_ID` trong `backend/.env` |
