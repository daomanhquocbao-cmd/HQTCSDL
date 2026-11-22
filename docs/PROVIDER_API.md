# API dành cho giao diện Provider

Giao diện `frontend/provider/` gọi các endpoint dưới đây. Toàn bộ đường dẫn nằm ở một chỗ duy nhất:
`frontend/assets/js/provider-common.js` → hằng số `EP`. Backend đổi route thì chỉ sửa `EP`.

- Đăng nhập dùng API **đã có sẵn**: `POST /api/users/login` (nhận `{access_token}`) và `GET /api/users/me`.
- Các endpoint `/api/provider/*` đã được cài trong `backend/provider/` (router, service, schemas) và gắn vào `main.py`; chỉ cần có CSDL chạy các script 01-03. Chúng là endpoint **mới**, dành cho vai trò `PROVIDER` (chỉ thấy dữ liệu studio của mình) và `ADMIN` (thấy tất cả).
- Không đăng nhập hoặc không có backend: giao diện chạy **chế độ demo** bằng dữ liệu giả, mô phỏng đúng quy tắc của stored procedure.
- Lỗi: `{ "detail": "<thông báo>" }`. Với lỗi từ SQL (`THROW 50xxx`) nên trả `detail` là chính thông báo tiếng Việt của SQL
  (409 khi sai trạng thái / vi phạm quy tắc, 403 khi sai quyền, 404 khi không tìm thấy) để giao diện hiển thị nguyên văn.

## Luồng đơn đặt ↔ stored procedure

| Giao diện | Endpoint | Gọi trong SQL (`03_stored_procedures.sql`) |
|---|---|---|
| Xác nhận đơn (PENDING → CONFIRMED, sinh `qr_code`) | `POST /api/provider/bookings/{id}/confirm` | `sp_ConfirmReservation @reservation_id, @actor_id` |
| Hủy đơn (hoàn tiền) | `POST /api/provider/bookings/{id}/cancel` | `sp_CancelReservation @reservation_id, @actor_id` |
| Check-in bằng mã QR (CONFIRMED → IN_USE) | `POST /api/provider/bookings/checkin` body `{ "qr_code" }` | `sp_CheckIn @qr_code, @actor_id` |
| Check-out (IN_USE → COMPLETED, trừ kho vật tư tiêu hao) | `POST /api/provider/bookings/{id}/checkout` | `sp_CheckOut @reservation_id, @actor_id` |
| Ghi nhận thanh toán | `POST /api/provider/bookings/{id}/payments` body `{ amount, payment_method, transaction_code? }` | `sp_ProcessPayment @reservation_id, @amount, @payment_method, @actor_id, @transaction_code` |
| Thêm thiết bị vào đơn | `POST /api/provider/bookings/{id}/equipment` body `{ equipment_id, quantity }` | `sp_AddReservationEquipment` |
| Thêm gói dịch vụ vào đơn | `POST /api/provider/bookings/{id}/packages` body `{ package_id, notes? }` | `sp_AddReservationPackage` |

`@actor_id` = `user_id` trong JWT. Mỗi endpoint trên trả về **chi tiết đơn** (xem bên dưới) sau khi thực hiện.
Giao diện không còn đổi trạng thái tùy ý: đơn chỉ đi theo `PENDING → CONFIRMED → IN_USE → COMPLETED`, hủy được từ `PENDING/CONFIRMED`.

### Đọc dữ liệu đơn
- `GET /api/provider/bookings?status=&studio_id=&room_id=&limit=&offset=` → mảng, mỗi phần tử lấy từ **`vw_ReservationDetail`**:
  `reservation_id, status, start_time, end_time, customer_id, customer (username), customer_name?, room_id, room_name, studio_id, studio_name, total_amount, paid_amount, balance_due`
  + `qr_code, customer_note`.
- `GET /api/provider/bookings/{id}` → như trên, thêm:
  - `equipment[]` = `ReservationEquipments` ⨝ `Equipment` → `{equipment_id, name, quantity, unit_price}`
  - `packages[]` = `ReservationPackages` ⨝ `ServicePackages` → `{package_id, name, price, notes}`
  - `payments[]` = `Payments` → `{payment_id, amount, payment_method, transaction_code, status, paid_at, created_at}`
  - `history[]` = `ReservationStatusHistory` (do trigger `trg_Reservations_Audit` ghi) → `{old_status, new_status, changed_at, changed_by_name}`
  - `session` = `ServiceSessions` → `{checkin_time, checkout_time, actual_minutes}` hoặc `null`

## Các endpoint còn lại
| Endpoint | Ghi chú |
|---|---|
| `GET /api/provider/overview` | `studio_count, room_count, equipment_count, total_bookings, pending_bookings, upcoming_bookings, revenue_total, revenue_this_month, avg_rating, review_count, revenue_by_month[{month 'YYYY-MM', revenue, bookings}], top_rooms[{room_id, room_name, studio_name, bookings, revenue}]`. Doanh thu chỉ tính `Payments.status = 'SUCCESS'` (khoản `REFUNDED` không tính). Điểm đánh giá lấy từ `vw_StudioRating`. |
| `GET/POST /api/provider/studios`, `PATCH …/{id}` | Studio tạo mới ở trạng thái `PENDING` (admin tạo thì `APPROVED`). Nhà cung cấp phải được admin duyệt (`Users.status = ACTIVE`) mới tạo được, nếu không `403`. Trường: `name, address, city, phone, description, open_time, close_time`. |
| `DELETE /api/provider/studios/{id}` | `204`. Xóa cơ sở cùng phòng / thiết bị / gói của nó. `409` nếu cơ sở đã có đơn đặt phòng hoặc workshop (khi đó chỉ nên ẩn phòng). `403` nếu không phải chủ cơ sở. |
| `POST /api/provider/bookings/{id}/cancel` | Body tùy chọn `{"reason": "..."}` (≤ 500 ký tự). Lý do lưu vào `Reservations.cancel_reason` (cần chạy `database/06_provider_additions.sql`); chưa có cột thì vẫn hủy được nhưng phản hồi có `reason_saved: false`. Chi tiết đơn trả thêm `cancel_reason`. |
| `GET /api/provider/disputes?status=` | Khiếu nại thuộc các cơ sở của provider (join Disputes → Reservations → Rooms → Studios). |
| `PATCH /api/provider/disputes/{id}` | Body `{"status": "IN_REVIEW"\|"RESOLVED"\|"REJECTED", "resolution": "..."}`. `RESOLVED`/`REJECTED` bắt buộc có `resolution`; `REJECTED` chỉ admin; `409` nếu đã xử lý xong. |
| `GET /api/provider/workshops?status=` | Workshop do chuyên gia tổ chức tại cơ sở của provider (chỉ xem), kèm `registered` / `capacity`. |
| `GET/POST /api/provider/rooms`, `PATCH …/{id}` | Trả **mọi** trạng thái phòng (`AVAILABLE/MAINTENANCE/INACTIVE`). Trường: `studio_id, name, room_type, capacity, area_sqm, art_style, lighting, amenities, price_per_hour, description, status`. Ẩn phòng = `PATCH status=INACTIVE`. |
| `GET/POST /api/provider/equipment`, `PATCH`, `DELETE …/{id}` | `DELETE` = đặt `status = 'RETIRED'`. |
| `POST /api/provider/equipment/{id}/maintenance` | `{cost, description, status: SCHEDULED/DONE, next_maintenance_date}` ghi vào `EquipmentMaintenance`. |
| `GET /api/provider/packages?studio_id=` | `ServicePackages` kèm `equipment[{equipment_id, name, quantity_included}]` từ `PackageEquipment`. |
| `GET /api/provider/reviews?studio_id=` | `Reviews` của studio mình. |
| `PATCH /api/users/me`, `POST /api/users/change-password` | Tùy chọn. Chưa có thì trang Hồ sơ hiển thị "Backend chưa có endpoint". |

## Phân tích, AI, giá, khuyến mãi (cần chạy `database/07_pricing_promotions_ai.sql`)
Chưa chạy file 07 thì các endpoint dưới đây trả `503` kèm hướng dẫn; các endpoint cũ vẫn chạy bình thường.

| Endpoint | Ghi chú |
|---|---|
| `GET /api/provider/analytics/occupancy?days=30&studio_id=` | Tỉ lệ lấp đầy mỗi phòng = giờ đã đặt / giờ mở cửa trong `days` ngày (đơn CONFIRMED/IN_USE/COMPLETED đã bắt đầu). Trả `rooms[{room_id, room_name, studio_name, bookings, booked_hours, available_hours, occupancy_pct}]` và `summary`. |
| `GET /api/provider/analytics/heatmap?days=56&studio_id=` | `cells[{weekday_index 0=Thứ Hai, weekday, hour, booked_hours, available_hours, occupancy_pct}]`: mức lấp đầy theo thứ × giờ (đã nhân số phòng). |
| `GET /api/provider/analytics/equipment?days=30&studio_id=` | Hiệu suất thiết bị `REUSABLE` = giờ-thiết bị được thuê / (số lượng × giờ mở cửa). Kèm `rentals, unit_hours, rental_revenue, maintenance_count, maintenance_cost, alerts[]` (hỏng, quá hạn/sắp bảo trì, vật tư sắp hết, quá tải ≥85%, ít thuê <10%). |
| `GET /api/provider/ai/forecast?studio_id=&horizon_days=7&lookback_days=84` | Gọi `sp_ForecastDemand`: dự báo số đơn từng ngày tới = trung bình cùng thứ trong lịch sử. `level` HIGH/NORMAL/LOW, `reliable=false` nếu ít hơn 4 tuần dữ liệu. |
| `GET /api/provider/ai/pricing-suggestions?studio_id=&days=56` | Gợi ý hệ số giá theo khung (Sáng/Chiều/Tối × ngày thường/cuối tuần): lấp đầy ≥75% → ×1.15, ≥60% → ×1.08, ≤20% → ×0.90. `insufficient_data=true` nếu < 5 giờ đặt. |
| `GET/POST /api/provider/pricing-rules`, `PATCH/DELETE …/{id}` | Quy tắc giá `{studio_id, room_id?, name, day_type ALL/WEEKDAY/WEEKEND, start_hour 0-23, end_hour 1-24, multiplier 0.5-3, status}`. Giá đơn tính theo từng khung 30 phút; quy tắc của phòng thắng quy tắc cả cơ sở; nhiều quy tắc cùng cấp thì lấy hệ số lớn nhất. |
| `GET/POST /api/provider/promotions`, `PATCH/DELETE …/{id}` | Khuyến mãi `{studio_id, code, title, discount_type PERCENT/FIXED, discount_value, max_discount?, min_order_amount, start_date, end_date, max_uses?, status}`; trả thêm `used_count` và `state` (RUNNING/UPCOMING/EXPIRED/USED_UP/INACTIVE). Mã trùng trong cơ sở `409`; mã đã có người dùng không xóa được (`409`, hãy tạm ngưng). |

Phía khách (cùng nghiệp vụ giá): `GET /api/pricing/quote?room_id&start_time&end_time&promo_code` (công khai), `POST /api/pricing/bookings/{id}/promotion {code}` (gọi `sp_ApplyPromotion`, khóa dòng chống dùng quá lượt), `POST /api/bookings` nhận thêm `promo_code` tùy chọn.

## Quản trị, cộng đồng, AI cho khách
| Endpoint | Ghi chú |
|---|---|
| `GET /api/admin/overview` | Chỉ ADMIN. Số nhà cung cấp/cơ sở chờ duyệt, khiếu nại đang mở... |
| `GET /api/admin/providers?status=PENDING\|ACTIVE\|SUSPENDED` | Danh sách nhà cung cấp kèm số cơ sở. |
| `PATCH /api/admin/providers/{id}` `{"status":"ACTIVE"\|"SUSPENDED"}` | Duyệt / mở khóa / từ chối / khóa. Khóa thì các cơ sở đang `APPROVED` chuyển `SUSPENDED` (ngừng nhận đặt). |
| `GET /api/admin/studios?status=`, `PATCH /api/admin/studios/{id}` `{"status":"APPROVED"\|"REJECTED"\|"SUSPENDED"}` | Duyệt cơ sở; chỉ duyệt được khi nhà cung cấp đã `ACTIVE`. |
| `GET /api/community/posts?post_type=&q=&limit=&offset=`, `GET …/{id}` | Công khai. Chi tiết kèm `comments[]`. |
| `POST /api/community/posts`, `POST …/{id}/comments`, `DELETE …/posts/{id}`, `DELETE …/comments/{id}` | Cần đăng nhập. Loại `ARTICLE/TUTORIAL/WORKSHOP_ANNOUNCEMENT` chỉ EXPERT/PROVIDER/ADMIN được đăng; chỉ tác giả hoặc ADMIN xóa. |
| `GET /api/ai/recommendations?top=5` | Gọi `sp_RecommendRooms`: điểm = 35% đánh giá + 25% độ phổ biến 90 ngày + 20% hợp loại phòng + 10% hợp thành phố + 10% hợp mức giá của khách. Có token thì cá nhân hóa. |
| `GET /api/ai/ask?q=phòng tối dưới 300k ở Hà Nội cho 4 người` | Tìm phòng bằng câu hỏi tự nhiên (tách loại phòng, ngân sách, sức chứa, thành phố theo luật từ khóa). |

Nhà cung cấp đăng ký mới (`role=PROVIDER`) có `status = PENDING`: đăng nhập được nhưng chưa tạo được cơ sở cho tới khi admin duyệt.

## Quy tắc nghiệp vụ nằm ở SQL (giao diện chỉ hiển thị lại)
- Đơn chỉ đặt trong **1 ngày**, trong giờ mở/đóng cửa của studio, không trùng đơn `PENDING/CONFIRMED/IN_USE` của cùng phòng.
- Check-in: sớm nhất **30 phút** trước giờ bắt đầu, không quá giờ kết thúc.
- Hủy: chủ studio / admin hủy → hoàn tiền; khách hủy khi còn < 24h → không hoàn.
- Thiết bị `BROKEN/RETIRED/UNDER_MAINTENANCE` không cho thuê; vật tư `CONSUMABLE` bị trừ kho lúc check-out.
- Thanh toán không được vượt tổng tiền; đơn đã hủy/hoàn tất không nhận thanh toán.
