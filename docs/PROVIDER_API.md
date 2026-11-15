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
| `GET/POST /api/provider/studios`, `PATCH …/{id}` | Studio tạo mới ở trạng thái `PENDING` (admin tạo thì `APPROVED`). Trường: `name, address, city, phone, description, open_time, close_time`. |
| `GET/POST /api/provider/rooms`, `PATCH …/{id}` | Trả **mọi** trạng thái phòng (`AVAILABLE/MAINTENANCE/INACTIVE`). Trường: `studio_id, name, room_type, capacity, area_sqm, art_style, lighting, amenities, price_per_hour, description, status`. Ẩn phòng = `PATCH status=INACTIVE`. |
| `GET/POST /api/provider/equipment`, `PATCH`, `DELETE …/{id}` | `DELETE` = đặt `status = 'RETIRED'`. |
| `POST /api/provider/equipment/{id}/maintenance` | `{cost, description, status: SCHEDULED/DONE, next_maintenance_date}` ghi vào `EquipmentMaintenance`. |
| `GET /api/provider/packages?studio_id=` | `ServicePackages` kèm `equipment[{equipment_id, name, quantity_included}]` từ `PackageEquipment`. |
| `GET /api/provider/reviews?studio_id=` | `Reviews` của studio mình. |
| `PATCH /api/users/me`, `POST /api/users/change-password` | Tùy chọn. Chưa có thì trang Hồ sơ hiển thị "Backend chưa có endpoint". |

## Quy tắc nghiệp vụ nằm ở SQL (giao diện chỉ hiển thị lại)
- Đơn chỉ đặt trong **1 ngày**, trong giờ mở/đóng cửa của studio, không trùng đơn `PENDING/CONFIRMED/IN_USE` của cùng phòng.
- Check-in: sớm nhất **30 phút** trước giờ bắt đầu, không quá giờ kết thúc.
- Hủy: chủ studio / admin hủy → hoàn tiền; khách hủy khi còn < 24h → không hoàn.
- Thiết bị `BROKEN/RETIRED/UNDER_MAINTENANCE` không cho thuê; vật tư `CONSUMABLE` bị trừ kho lúc check-out.
- Thanh toán không được vượt tổng tiền; đơn đã hủy/hoàn tất không nhận thanh toán.
