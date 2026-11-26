# 🎞️ Nền tảng kết nối cộng đồng nhiếp ảnh phim với dịch vụ phòng tối và phòng chụp

> **Bài tập lớn môn Hệ quản trị cơ sở dữ liệu** · Mã học phần: 012012100302
>
> *Film Photography Platform – Platform Connecting the Film Photography Community with Darkroom and Studio Services*

---

## 👥 Danh sách thành viên nhóm

| STT | Họ và Tên | MSSV |
| :---: | :--- | :---: |
| 1 | Đào Mạnh Quốc Bảo | 079206019047 |
| 2 | Trần Huỳnh Gia An | 079206020226 |
| 3 | Võ Anh Duy | 083206001605 |
| 4 | Nguyễn Hoàng Duy | 070206000430 |
| 5 | Nguyễn Ngọc Đoan Tiên | 079306000200 |

---

## 1. Giới thiệu đề tài

Nhiếp ảnh phim đang sống lại mạnh mẽ trong những năm gần đây. Cộng đồng người chơi phim ngày càng đông, kéo theo nhu cầu về **phòng tối (darkroom)**, **phòng chụp (studio)**, thiết bị chuyên dụng và các dịch vụ hỗ trợ.

Tuy nhiên các tài nguyên này đang rời rạc:

- **Với khách hàng (nhiếp ảnh gia):** phải tìm phòng qua nhóm mạng xã hội, người quen hoặc website riêng lẻ; hỏi lịch trống, giá, thiết bị và xác nhận bằng điện thoại hoặc tin nhắn. Quy trình chậm và thiếu minh bạch.
- **Với chủ studio:** quản lý phòng, thiết bị, vật tư, lịch bảo trì và đơn đặt bằng bảng tính hoặc nhiều phần mềm tách rời. Dễ trùng lịch, khó đánh giá hiệu quả kinh doanh.

Đề tài xây dựng một **nền tảng đa bên (multi-sided platform)** để kết nối hai phía, tập trung vào việc **quản lý và chia sẻ tài nguyên sáng tạo** thay vì chỉ là một ứng dụng đặt phòng thông thường.

## 2. Giải pháp

| Phía | Những gì hệ thống mang lại |
|---|---|
| **Khách hàng** | Tìm, so sánh và đặt phòng theo thành phố, loại phòng, sức chứa, giá, giờ mở cửa và đánh giá; thuê thêm thiết bị, chọn gói dịch vụ; check-in bằng mã QR; đánh giá sau khi dùng; đăng ký workshop. |
| **Chủ studio (Provider)** | Quản lý cơ sở, phòng, thiết bị, vật tư, gói dịch vụ; duyệt hoặc hủy đơn; check-in/check-out; theo dõi doanh thu và đánh giá; xử lý khiếu nại. |
| **Chuyên gia (Expert)** | Tổ chức workshop, chia sẻ bài viết và kinh nghiệm trong cộng đồng. |
| **Quản trị viên (Admin)** | Duyệt cơ sở và nhà cung cấp, giám sát giao dịch, xử lý tranh chấp, xem báo cáo toàn hệ thống. |

Điểm cốt lõi của hệ thống: **trước khi xác nhận đơn, hệ thống tự kiểm tra tính khả dụng của mọi tài nguyên liên quan** (phòng, thiết bị, gói) và chống trùng lịch ngay trong cơ sở dữ liệu, kể cả khi nhiều người đặt cùng lúc.

## 3. Các vai trò trong hệ thống

| Vai trò | Mã trong CSDL | Nhiệm vụ chính |
|---|---|---|
| Nhiếp ảnh gia | `CUSTOMER` | Tìm và đặt phòng, thanh toán, đánh giá, tham gia cộng đồng |
| Nhà cung cấp dịch vụ | `PROVIDER` | Vận hành studio, phòng, thiết bị, đơn đặt |
| Chuyên gia | `EXPERT` | Workshop, bài viết, hướng dẫn |
| Quản trị viên | `ADMIN` | Duyệt, giám sát, xử lý tranh chấp, báo cáo |

## 4. Các luồng nghiệp vụ chính

1. **Quản lý không gian sáng tạo:** hồ sơ từng phòng (diện tích, sức chứa, phong cách, ánh sáng, tiện ích, giá, giờ mở cửa).
2. **Quản lý thiết bị và vật tư:** máy ảnh, ống kính, máy phóng, máy scan, đèn, hóa chất, giấy ảnh… kèm tình trạng, lịch bảo trì, giá thuê, tồn kho.
3. **Đặt phòng và phân bổ tài nguyên:** kiểm tra trùng lịch, tồn kho thiết bị theo khung giờ, khóa tài nguyên khi đơn được duyệt.
4. **Phiên sử dụng dịch vụ:** check-in bằng mã QR, ghi nhận thời lượng thực tế, check-out, trừ vật tư tiêu hao.
5. **Gói dịch vụ:** kết hợp phòng, thiết bị, vật tư và người hướng dẫn cho từng mục đích (chân dung, sản phẩm, tráng phim, in ảnh…).
6. **Chia sẻ tri thức cộng đồng:** bài viết, hướng dẫn, review thiết bị, workshop, thảo luận.

## 5. Công nghệ sử dụng

| Thành phần | Công nghệ trong dự án |
|---|---|
| Cơ sở dữ liệu | **Microsoft SQL Server** (T-SQL: stored procedure, function, view, trigger, index) |
| Backend | **Python – FastAPI**, `pyodbc`, xác thực **JWT**, phân quyền theo vai trò |
| Giao diện | HTML + CSS + JavaScript thuần (giao diện khách hàng và giao diện chủ studio, có bản PC và mobile) |
| Kiểm thử | `pytest` |
| Triển khai | Dockerfile, docker-compose |

> Đề cương ban đầu đề xuất Flutter, ReactJS/Next.js, PostgreSQL/MySQL và các dịch vụ AI. Do trọng tâm của môn học là **hệ quản trị cơ sở dữ liệu**, nhóm hiện thực hóa phần lõi bằng SQL Server + FastAPI và giao diện web tĩnh để tập trung vào thiết kế CSDL và xử lý nghiệp vụ.

## 6. Cơ sở dữ liệu (trọng tâm của đề tài)

Database `FilmPhotographyPlatform` gồm **26 bảng** (20 bảng lõi + 3 bảng giá/khuyến mãi + 3 bảng ảnh/cấu hình), cùng hàm, view, trigger, stored procedure và hệ thống index.

**Các bảng chính:** `Users`, `Studios`, `StudioImages`, `Rooms`, `Equipment`, `EquipmentMaintenance`, `ServicePackages`, `PackageEquipment`, `Reservations`, `ReservationEquipments`, `ReservationPackages`, `ServiceSessions`, `ReservationStatusHistory`, `Payments`, `Reviews`, `Workshops`, `WorkshopRegistrations`, `CommunityPosts`, `PostComments`, `Disputes`; mở rộng: `Promotions`, `PricingRules`, `ReservationPromotions`, `PhotoCollections`, `Photos`, `SystemSettings`.

**Những kỹ thuật CSDL được áp dụng:**

| Kỹ thuật | Ví dụ trong dự án |
|---|---|
| **Ràng buộc toàn vẹn** | `PRIMARY KEY`, `FOREIGN KEY`, `UNIQUE` (mỗi đơn đánh giá một lần, một khách đăng ký một workshop một lần), `CHECK` (điểm 1–5, `end_time > start_time`, các trạng thái hợp lệ) |
| **Stored procedure + transaction** | `sp_CreateReservation`, `sp_ConfirmReservation`, `sp_CancelReservation`, `sp_CheckIn`, `sp_CheckOut`, `sp_ProcessPayment`, `sp_RegisterWorkshop`, … dùng `TRY…CATCH`, `THROW`, rollback khi lỗi |
| **Chống trùng lịch khi đặt đồng thời** | Khóa dòng bằng `UPDLOCK, HOLDLOCK` trong `sp_CreateReservation`: các giao dịch cùng một phòng phải xếp hàng |
| **Trigger** | `trg_Reservations_Audit` tự ghi `ReservationStatusHistory`; `trg_Reviews_Validate` chỉ cho đánh giá đơn đã hoàn thành của chính mình |
| **View** | `vw_StudioRating` (điểm đánh giá trung bình), `vw_ReservationDetail` (đơn kèm số tiền đã thanh toán và còn nợ) |
| **Hàm (function)** | `fn_EquipmentAvailable` (tồn kho theo khung giờ), `fn_CanManageReservation` (phân quyền thao tác đơn) |
| **Cột tính toán** | `ServiceSessions.actual_minutes` (persisted computed column) |
| **Index và tối ưu truy vấn** | `IX_Res_Room_Time`, `IX_Res_Customer`, index lọc `UX_Res_QR`; demo có index và không có index, truy vấn SARGable (`06_performance_demo.sql`) |
| **Truy vấn báo cáo** | Doanh thu theo studio và theo tháng (`LAG`), tỉ lệ hủy, tỉ lệ lấp đầy, giờ cao điểm, cảnh báo thiết bị, kiểm tra toàn vẹn dữ liệu (`04_business_queries.sql`) |

### Các script SQL (thư mục `database/`)

| File | Mục đích |
|---|---|
| `01_create_tables.sql` | Tạo database, 20 bảng, ràng buộc và index |
| `02_seed_data.sql` | Dữ liệu mẫu (người dùng, studio, phòng, thiết bị, đơn, đánh giá, workshop…) |
| `03_stored_procedures.sql` | Hàm, view, trigger và stored procedure |
| `04_business_queries.sql` | Truy vấn báo cáo, kiểm tra toàn vẹn, kịch bản demo stored procedure |
| `05_seed_bulk.sql` | Nạp dữ liệu lớn (hàng trăm nghìn đơn) để thử hiệu năng |
| `06_performance_demo.sql` | So sánh hiệu năng có index và không có index |
| `06_provider_additions.sql` | Thêm cột `Reservations.cancel_reason` (lý do hủy đơn) |
| `07_pricing_promotions_ai.sql` | Giá theo khung giờ, khuyến mãi, `sp_QuotePrice`, `sp_RecommendRooms`, `sp_ForecastDemand` |
| `08_collections_settings_ledger.sql` | Bộ sưu tập ảnh, cấu hình admin, sổ giao dịch `vw_PaymentLedger`, `sp_RefundPayment` |
| `10_room_profile.sql` | Thêm thông gió, âm học, chính sách sử dụng vào bảng Rooms |
| `09_backup_recovery.sql` | Sao lưu FULL / DIFF / LOG, kiểm tra file sao lưu, quy trình khôi phục, lịch tự động |

## 7. Tình trạng hiện thực

| Hạng mục | Trạng thái |
|---|---|
| Cơ sở dữ liệu, stored procedure, trigger, view, sao lưu / khôi phục | ✅ Hoàn thành |
| Khách hàng (web responsive): tìm / lọc / so sánh phòng, xem lịch trống, đặt phòng + thiết bị + gói + mã giảm giá, thanh toán, hủy, đánh giá, khiếu nại, QR check-in, workshop, cộng đồng, hồ sơ | ✅ Có |
| Bộ sưu tập ảnh và phục hồi / nâng chất lượng ảnh (xử lý ảnh cổ điển bằng Pillow) | ✅ Có |
| Chủ studio (PC và mobile): đơn, phòng, thiết bị, gói, đánh giá, khiếu nại, workshop, phân tích lấp đầy, hiệu suất thiết bị, dự báo, chính sách giá, khuyến mãi | ✅ Có |
| Chuyên gia: workshop, bài viết, review thiết bị, trả lời thảo luận | ✅ Có |
| Quản trị: duyệt nhà cung cấp / cơ sở, người dùng, giao dịch + hoàn tiền, khiếu nại, kiểm duyệt, cấu hình AI, báo cáo | ✅ Có |
| AI: gợi ý phòng cá nhân hóa, trợ lý hỏi đáp, tìm kiếm kho kiến thức, dự báo nhu cầu, gợi ý giá, gợi ý thiết bị / gói | 🟡 Thuật toán (SQL + luật + TF-IDF), chưa dùng mô hình học máy / LLM |
| Thanh toán VNPay (sandbox) | ✅ Có `integrations/vnpay.py`, cần `VNPAY_TMN_CODE`/`VNPAY_HASH_SECRET`. MoMo, Stripe: ⛔ chưa |
| Ứng dụng di động Flutter | 🟡 Mã nguồn trong `mobile/`, chưa được biên dịch thử, xem `mobile/README.md` |
| OAuth 2.0 (Google) | ✅ `POST /api/auth/google`, cần `GOOGLE_CLIENT_ID` |
| Tối ưu phân bổ tài nguyên | ✅ `GET /api/provider/ai/schedule-optimize` (quét sự kiện, tô màu khoảng, best-fit) |

## 8. Cấu trúc thư mục

```
HQTCSDL-restructure/
├── backend/              # FastAPI: users, studios, rooms, booking, customer, photos, provider, admin, ai, pricing, community, tests
├── database/             # Các script SQL (01 → 09)
├── frontend/
│   ├── customer/         # Đăng nhập + customer-pc.html (khách hàng, responsive)
│   ├── provider/         # Chủ studio (provider-pc-*.html và provider-*.html cho mobile)
│   ├── expert/           # Chuyên gia
│   ├── admin/            # Quản trị viên
│   └── assets/           # CSS và JavaScript dùng chung
├── docs/
│   ├── API.md            # Tài liệu API chung
│   └── PROVIDER_API.md   # Tài liệu API cho chủ studio
├── CHANGELOG.md
└── README.md
```

## 9. Chạy thử nhanh

Hướng dẫn đầy đủ (cài Python, tạo venv, cấu hình `.env`, lỗi thường gặp) nằm trong [`backend/README.md`](backend/README.md). Tóm tắt:

1. Mở SSMS và chạy lần lượt `database/01` → `02` → `03` → `06_provider_additions` → `07` → `08` → `10` (→ `09` nếu muốn thử sao lưu).
2. Cài đặt và chạy backend:
   ```bash
   cd backend
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   copy .env.example .env      # rồi sửa DB_SERVER, DB_USER, DB_PASSWORD
   uvicorn app_full:app --reload
   ```
3. Mở trình duyệt:
   - API và Swagger: http://localhost:8000/docs
   - Đăng nhập (mọi vai trò): http://localhost:8000/web/customer/auth.html
   - Khách hàng: http://localhost:8000/web/customer/customer-pc.html
   - Chủ studio: http://localhost:8000/web/provider/provider-login.html
   - Chuyên gia: http://localhost:8000/web/expert/expert-pc.html · Quản trị: http://localhost:8000/web/admin/admin-pc.html

> Dữ liệu mẫu trong `02_seed_data.sql` dùng mật khẩu giữ chỗ nên chưa đăng nhập được ngay. Cần đặt hash mật khẩu hợp lệ cho một tài khoản (hoặc đăng ký tài khoản mới qua `/api/users/register`) trước khi thử.

## 10. Tài liệu liên quan

- [`backend/README.md`](backend/README.md): cài đặt, chạy, kiểm thử, lỗi thường gặp
- [`docs/API.md`](docs/API.md): danh sách endpoint chung
- [`docs/PROVIDER_API.md`](docs/PROVIDER_API.md): endpoint dành cho chủ studio
- [`CHANGELOG.md`](CHANGELOG.md): lịch sử thay đổi

## 11. Hướng phát triển

- Thay các thuật toán AI bằng mô hình thật: học máy cho gợi ý và dự báo, mô hình ảnh (Real-ESRGAN…) cho phục hồi ảnh, LLM + embedding cho trợ lý và tìm kiếm ngữ nghĩa.
- Biên dịch và kiểm thử app Flutter trên thiết bị thật; MoMo, Stripe.
- Triển khai trên hạ tầng đám mây (Azure/Firebase) có sao lưu tự động; lưu ảnh trên Blob Storage.
- Mô hình AI thật (LLM, thị giác máy tính) thay cho thuật toán hiện tại.
