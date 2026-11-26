# Ứng dụng di động Flutter (Android & iOS)

Một ứng dụng cho **cả 4 vai trò** (tự chuyển màn hình theo tài khoản đăng nhập):
- **Khách hàng**: khám phá và tìm phòng, xem chi tiết (kèm Google Maps), báo giá, đặt phòng, xem đơn, thanh toán VNPay,
hủy/đánh giá/khiếu nại, cộng đồng và tìm kiến thức, trợ lý AI, bộ sưu tập ảnh có phục hồi và chia sẻ.
- **Nhà cung cấp**: tổng quan doanh thu, duyệt/check-in/check-out/hủy đơn (có ô nhập mã QR), đổi trạng thái phòng, dự báo, gợi ý giá, tối ưu phân bổ theo ngày, cộng đồng.
- **Chuyên gia**: tạo workshop, viết bài, thảo luận.
- **Quản trị**: tổng quan hệ thống, duyệt nhà cung cấp/studio, bật tắt cấu hình (AI, bảo trì, hoa hồng...).

Dùng chung backend FastAPI với web. Chức năng nặng (sửa chi tiết phòng, thiết bị, khuyến mãi, hoàn tiền, kiểm duyệt) dùng giao diện web.

## Chạy
1. Cài Flutter SDK ≥ 3.19. Trong thư mục này chạy lần đầu để sinh thư mục `android/`, `ios/`:
   ```
   flutter create --org vn.edu.hqtcsdl --project-name film_photo_app .
   flutter pub get
   ```
   (lệnh `create` giữ nguyên `lib/`, `pubspec.yaml`, `test/` đã có)
2. Bật backend: `uvicorn app_full:app --host 0.0.0.0 --port 8000` (cần `--host 0.0.0.0` để điện thoại thật truy cập được).
3. Chạy app:
   - Emulator Android: `flutter run` (mặc định `http://10.0.2.2:8000`).
   - Máy thật: `flutter run --dart-define=API_BASE=http://IP-LAN-MAY-TINH:8000`, hoặc bấm ⚙ ở màn hình đăng nhập để đổi địa chỉ.
4. Android cần cho phép HTTP không mã hóa khi dev: thêm `android:usesCleartextTraffic="true"` vào thẻ `<application>` trong
   `android/app/src/main/AndroidManifest.xml`, và quyền `<uses-permission android:name="android.permission.INTERNET"/>`.
   iOS: thêm `NSAppTransportSecurity` → `NSAllowsArbitraryLoads` vào `Info.plist` khi dev.

## Đăng nhập Google (tùy chọn)
Đặt `GOOGLE_CLIENT_ID` trong `backend/.env` (Web client ID). Android cần thêm OAuth client kiểu Android (package name + SHA-1) trong
Google Cloud Console. Khi server báo `enabled: true`, nút "Đăng nhập bằng Google" tự hiện.

## Thanh toán VNPay
Đặt `VNPAY_TMN_CODE`, `VNPAY_HASH_SECRET` (sandbox). Nút thanh toán mở trình duyệt; sau khi trả tiền VNPay chuyển về backend
(`/api/payments/vnpay/return`), backend ghi nhận rồi chuyển người dùng về trang web. Quay lại app, danh sách đơn tự tải lại.

## Lưu ý
Mã nguồn chưa được biên dịch trong môi trường soạn thảo (không có Flutter SDK). Nếu `flutter analyze` báo lỗi, gửi lại để sửa.
