# Tài liệu kỹ thuật

## 1. Kiến trúc
```
Web tĩnh (HTML/JS)  ─┐
App Flutter         ─┼─ HTTPS/JSON + JWT ─▶ FastAPI (modules) ─ pyodbc ─▶ SQL Server (bảng, view, SP, trigger)
                     │                        ├─ ai/, community/, provider/analytics, scheduler  (thuật toán)
                     │                        ├─ photos/ (Pillow) ─▶ thư mục uploads/
                     │                        └─ integrations/ (Google OAuth, VNPay)
```
Tách mô-đun theo thư mục: `users`, `studios`, `rooms`, `booking`, `customer`, `provider`, `admin`, `community`, `workshops`, `pricing`, `ai`, `photos`, `integrations`, `core`. Mỗi mô-đun có `router.py` (HTTP) và `service.py` (nghiệp vụ, truy cập DB). Thêm loại phòng, nhóm thiết bị hoặc dịch vụ mới chủ yếu là thêm giá trị vào cột CHECK và một mô-đun, không đổi kiến trúc.

## 2. Cơ sở dữ liệu
26 bảng chia nhóm: người dùng (`Users`), cơ sở (`Studios`, `StudioImages`, `Rooms`), thiết bị (`Equipment`, `EquipmentMaintenance`), gói (`ServicePackages`, `PackageEquipment`), đặt chỗ (`Reservations`, `ReservationStatusHistory`, `ReservationEquipments`, `ReservationPackages`, `Payments`, `ServiceSessions`, `Disputes`, `Reviews`), cộng đồng (`CommunityPosts`, `PostComments`, `Workshops`, `WorkshopRegistrations`), giá và khuyến mãi (`PricingRules`, `Promotions`, `ReservationPromotions`), ảnh (`PhotoCollections`, `Photos`), cấu hình (`SystemSettings`). Thứ tự chạy script: `01 → 02 → 03 → 06_provider_additions → 07 → 08 → 10`, tùy chọn `04, 05, 06_performance_demo, 09`.

### Điểm nhấn về CSDL
- **Quy tắc nghiệp vụ nằm trong stored procedure** (`sp_CreateReservation`, `sp_ConfirmReservation`, `sp_CheckIn`, `sp_CheckOut`, `sp_ProcessPayment`, `sp_CancelReservation`, `sp_RefundPayment`, `sp_RegisterWorkshop`, `sp_QuotePrice`, `sp_ApplyPromotion`, `sp_ForecastDemand`, `sp_RecommendRooms`, `sp_BackupDatabase`) và trigger (`trg_Reviews_Validate`). Lỗi nghiệp vụ dùng `THROW` mã 50xxx–53xxx, backend ánh xạ sang HTTP 400/403/404/409.
- **Chống đặt trùng khi đồng thời**: `sp_CreateReservation` bọc trong transaction, khóa `UPDLOCK, HOLDLOCK` trên khoảng thời gian của phòng và các thiết bị; `scripts/concurrency_test.py` chạy N luồng cùng đặt một khung giờ và kỳ vọng đúng 1 thành công.
- **Chỉ mục** phục vụ tìm phòng, lịch trống, báo cáo (xem `06_performance_demo.sql` so sánh kế hoạch thực thi trước/sau).
- **Sao lưu và phục hồi**: `09_backup_recovery.sql` (FULL recovery, sao lưu FULL/DIFF/LOG, lịch SQL Agent hoặc Task Scheduler, quy trình khôi phục đến thời điểm).
- `vw_ReservationDetail`, `vw_PaymentLedger`, `vw_StudioRating` gom truy vấn lặp lại.

## 3. Bảo mật
JWT (`core/security.py`, khóa `JWT_SECRET` phải đổi khi triển khai, hết hạn theo `ACCESS_TOKEN_MINUTES`), mật khẩu băm, phân quyền theo vai trò (`require_roles`, `require_customer`, `require_provider`), mọi truy vấn tham số hóa (chống SQL injection), kiểm tra quyền sở hữu (khách chỉ thấy đơn của mình, provider chỉ thấy cơ sở của mình), đăng nhập Google xác thực `aud`, `iss`, `email_verified`, VNPay xác thực chữ ký HMAC-SHA512 và chống ghi trùng bằng mã giao dịch. Tệp ảnh: kiểm tra định dạng, kích thước, chống path traversal.

## 4. Các thuật toán AI (không dùng mô hình học máy)
| Chức năng | Cách làm | Vị trí |
|---|---|---|
| Gợi ý phòng | Chấm điểm trong SQL theo sở thích từ lịch sử (loại phòng, giá), đánh giá, độ phổ biến | `sp_RecommendRooms`, `ai/service.py` |
| Gợi ý thiết bị/gói | Tần suất thuê chung (co-occurrence) trong các đơn cùng loại phòng, dự phòng bằng danh mục điển hình | `ai/service.suggest_for_room` |
| Dự báo nhu cầu | Trung bình số đơn theo thứ trong tuần trên dữ liệu lịch sử | `sp_ForecastDemand`, `provider/analytics.py` |
| Giá động | So sánh lấp đầy theo khung giờ với ngưỡng cao/thấp (cấu hình được) → hệ số giá | `analytics.build_pricing_suggestions` |
| Tối ưu phân bổ | Quét sự kiện tìm thiếu thiết bị; tô màu đồ thị khoảng gán thiết bị; tìm khoảng vụn; best-fit chọn phòng | `provider/scheduler.py` |
| Tìm kiếm ngữ nghĩa | Chuẩn hóa dấu, mở rộng từ đồng nghĩa, TF-IDF (tiêu đề ×3, thưởng cụm từ) | `community/service.py` |
| Trợ lý | Hiểu tiêu chí bằng luật từ khóa (loại phòng, giá, sức chứa, thành phố) + tìm kiến thức | `ai/service.ask` |
| Phục hồi ảnh | Autocontrast, lọc median, unsharp mask, phóng 2× LANCZOS, đảo âm bản (Pillow) | `photos/service.py` |

## 5. Cấu hình
Biến môi trường trong `backend/.env` (mẫu `.env.example`): kết nối SQL Server, `JWT_SECRET`, `CORS_ORIGINS`, `GOOGLE_CLIENT_ID`, `VNPAY_*`, `UPLOAD_DIR`. Cấu hình vận hành thay đổi được lúc chạy qua bảng `SystemSettings` (trang Admin).

## 6. Kiểm thử
- `pytest` trong `backend/` (cursor giả, không cần SQL Server): dịch vụ provider, customer/admin/photos, scheduler, tích hợp. `test_customer_api.py` kiểm quyền HTTP cần `fastapi.testclient`.
- `scripts/concurrency_test.py`: tính đúng khi đặt đồng thời.
- `scripts/measure_latency.py`: đo thời gian phản hồi (< 3 giây).

## 7. Triển khai
Cục bộ: `uvicorn app_full:app --host 0.0.0.0 --port 8000`. Docker: `backend/Dockerfile`, `docker-compose.yml`. Lên đám mây (khuyến nghị): Azure App Service (backend) + Azure SQL/Managed Instance (CSDL, sao lưu tự động) + Blob Storage (thay `uploads/`, chỉ cần thay hàm lưu/xóa tệp trong `photos/service.py`) + biến môi trường qua Key Vault.
