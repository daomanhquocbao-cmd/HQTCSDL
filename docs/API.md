# Tài liệu API

Base URL: `http://localhost:8000` · Swagger: `/docs`
🔒 cần header `Authorization: Bearer <token>` · 👑 ADMIN · 🏢 ADMIN hoặc PROVIDER (chủ studio)

## Users
| Method | Path | Mô tả | Quyền |
|---|---|---|---|
| POST | /api/users/register | Đăng ký (role mặc định CUSTOMER, mật khẩu ≥ 8 ký tự) | public |
| POST | /api/users/login | Đăng nhập bằng username, nhận JWT | public |
| GET | /api/users/me | Thông tin tài khoản hiện tại | 🔒 |

## Studios & Reviews
| Method | Path | Mô tả | Quyền |
|---|---|---|---|
| GET | /api/studios?keyword=&limit=&offset= | Danh sách studio kèm điểm đánh giá TB | public |
| GET | /api/studios/{id} | Chi tiết studio | public |
| POST | /api/studios | Tạo studio | 🏢 |
| GET | /api/studios/{id}/reviews | Danh sách đánh giá | public |
| POST | /api/studios/{id}/reviews | Gửi đánh giá 1–5 sao | 🔒 |

## Rooms
| Method | Path | Mô tả | Quyền |
|---|---|---|---|
| GET | /api/rooms?studio_id=&room_type= | Phòng đang AVAILABLE | public |
| GET | /api/rooms/available?start_time=&end_time= | Phòng còn trống trong khung giờ | public |
| GET | /api/rooms/{id} | Chi tiết phòng | public |
| POST | /api/rooms | Tạo phòng | 🏢 |
| PATCH | /api/rooms/{id} | Cập nhật phòng | 🏢 |
| DELETE | /api/rooms/{id} | Xóa mềm (status = INACTIVE) | 🏢 |

## Bookings (bảng Reservations)
| Method | Path | Mô tả | Quyền |
|---|---|---|---|
| POST | /api/bookings | Đặt phòng (gọi `sp_CreateReservation`, chống trùng lịch) | 🔒 |
| GET | /api/bookings?status= | Đơn của tôi | 🔒 |
| GET | /api/bookings/{id} | Chi tiết đơn (chủ đơn hoặc admin) | 🔒 |
| PATCH | /api/bookings/{id}/cancel | Hủy đơn (gọi `sp_UpdateReservationStatus`) | 🔒 |
| PATCH | /api/bookings/{id}/status | Xác nhận / hoàn thành / hủy đơn | 👑 |

## Workshops
| Method | Path | Mô tả | Quyền |
|---|---|---|---|
| GET | /api/workshops?upcoming_only= | Danh sách workshop, số chỗ còn lại | public |
| GET | /api/workshops/{id} | Chi tiết workshop | public |
| POST | /api/workshops | Tạo workshop | EXPERT / ADMIN |
| POST | /api/workshops/{id}/register | Đăng ký (gọi `sp_RegisterWorkshop`, chống trùng + kiểm tra sức chứa) | 🔒 |
| DELETE | /api/workshops/{id}/register | Hủy đăng ký | 🔒 |
| GET | /api/workshops/me/registrations | Workshop tôi đã đăng ký | 🔒 |

## Pricing / AI / Community / Admin (database/07)
| Method | Path | Mô tả | Quyền |
|---|---|---|---|
| GET | /api/pricing/quote | Báo giá (giờ cao/thấp điểm + mã giảm giá) | public |
| POST | /api/pricing/bookings/{id}/promotion | Áp mã khuyến mãi (`sp_ApplyPromotion`) | 🔒 |
| GET | /api/ai/recommendations | Gợi ý phòng (`sp_RecommendRooms`) | public / 🔒 cá nhân hóa |
| GET | /api/ai/ask?q= | Tìm phòng bằng câu hỏi tự nhiên | public |
| GET/POST | /api/community/posts | Xem / đăng bài cộng đồng | public / 🔒 |
| POST | /api/community/posts/{id}/comments | Bình luận | 🔒 |
| GET | /api/admin/overview, /providers, /studios | Danh sách chờ duyệt | 👑 |
| PATCH | /api/admin/providers/{id}, /studios/{id} | Duyệt / khóa | 👑 |

Chi tiết các endpoint của provider (phân tích, quy tắc giá, khuyến mãi): xem `PROVIDER_API.md`.

## Khách hàng `/api/customer` (database/01-03, 07)
| Method | Path | Mô tả | Quyền |
|---|---|---|---|
| GET | /api/customer/rooms | Tìm / lọc / sắp xếp phòng (`q, room_type, city, min_price, max_price, capacity, sort, start_time+end_time` để chỉ lấy phòng còn trống); chỉ phòng của studio đã duyệt | public |
| GET | /api/customer/cities | Danh sách thành phố có studio | public |
| GET | /api/customer/rooms/{id} | Chi tiết phòng + thiết bị cho thuê + gói dịch vụ + đánh giá | public |
| GET | /api/customer/rooms/{id}/busy?date= | Khung giờ đã có người đặt trong ngày | public |
| GET | /api/customer/overview | Số liệu trang chủ: đơn sắp tới, chi tiêu 6 tháng, đơn chưa đánh giá | 🔒 |
| GET | /api/customer/bookings, /bookings/{id} | Đơn của tôi / chi tiết (thiết bị, gói, thanh toán, mã QR, khiếu nại) | 🔒 |
| POST | /api/customer/bookings/{id}/equipment, /packages | Thuê thêm thiết bị / chọn gói (`sp_AddReservationEquipment`, `sp_AddReservationPackage`) | 🔒 |
| POST | /api/customer/bookings/{id}/payments | Thanh toán (`sp_ProcessPayment`) | 🔒 |
| POST | /api/customer/bookings/{id}/cancel | Hủy đơn (`sp_CancelReservation`) | 🔒 |
| POST | /api/customer/bookings/{id}/review | Đánh giá sau buổi thuê (trigger `trg_Reviews_Validate`) | 🔒 |
| POST | /api/customer/bookings/{id}/disputes | Gửi khiếu nại | 🔒 |

## Bộ sưu tập ảnh `/api/collections` (database/08, cần `pip install Pillow`)
| Method | Path | Mô tả | Quyền |
|---|---|---|---|
| GET/POST | /api/collections | Danh sách / tạo bộ sưu tập | 🔒 |
| PATCH/DELETE | /api/collections/{id} | Đổi tên / xóa (kèm ảnh) | 🔒 chủ sở hữu |
| GET/POST | /api/collections/{id}/photos | Xem ảnh / tải ảnh lên (JSON `{data: base64, caption}`, JPEG/PNG/WEBP ≤ 6 MB) | 🔒 |
| DELETE | /api/collections/photos/{id} | Xóa ảnh | 🔒 |
| POST/DELETE | /api/collections/{id}/share | Bật (sinh token) / tắt chia sẻ | 🔒 chủ sở hữu (file 13) |
| GET | /api/collections/shared/{token} | Xem bộ sưu tập được chia sẻ, chỉ đọc | công khai |
| POST | /api/collections/photos/{id}/restore | Phục hồi ảnh `{mode: restore | enhance | negative}`, kết quả là ảnh mới | 🔒 |
Ảnh được phục vụ tại `/uploads/<user_id>/<tên file>`.

## AI bổ sung
| Method | Path | Mô tả | Quyền |
|---|---|---|---|
| GET | /api/ai/suggest-room-extras?room_id= | Thiết bị / gói nên thêm khi đặt phòng (theo lịch sử thuê) | public |
| GET | /api/community/search?q= | Tìm kho kiến thức (bài viết + workshop) bằng đồng nghĩa + TF-IDF | public |
`/api/ai/ask` trả thêm `knowledge` (bài viết liên quan) để trả lời câu hỏi kỹ thuật nhiếp ảnh.

## Quản trị mở rộng (database/08)
| Method | Path | Mô tả | Quyền |
|---|---|---|---|
| GET | /api/admin/users | Danh sách người dùng (lọc role, status, q) | 👑 |
| PATCH | /api/admin/users/{id} | Khóa / mở khóa khách, chuyên gia | 👑 |
| GET | /api/admin/payments | Sổ giao dịch toàn hệ thống + tổng theo trạng thái | 👑 |
| POST | /api/admin/payments/{id}/refund | Hoàn tiền (`sp_RefundPayment`) | 👑 |
| GET/PUT | /api/admin/settings, /settings/{key} | Cấu hình AI / giá / đặt phòng / bảo trì; có hiệu lực ngay | 👑 |
| GET | /api/admin/reports?months= | Báo cáo: doanh thu theo tháng, top cơ sở, top phòng, đơn theo trạng thái, người dùng, phương thức thanh toán, khiếu nại | 👑 |
Khiếu nại: admin dùng chung `GET/PATCH /api/provider/disputes` (admin thấy toàn bộ).

## Stats
| Method | Path | Mô tả | Quyền |
|---|---|---|---|
| GET | /api/stats/summary | Số đơn, user theo role, studio, phòng, doanh thu | 👑 |

## Mã lỗi
`400` sai trạng thái / dữ liệu · `401` token sai hoặc hết hạn · `403` thiếu token hoặc không đủ quyền ·
`404` không tìm thấy · `409` trùng (username/email, khung giờ) · `422` dữ liệu không hợp lệ.

## Tích hợp (v1.5)
| Method | Path | Mô tả | Quyền |
|---|---|---|---|
| GET | /api/auth/google/config | Cho client biết có bật đăng nhập Google không | public |
| POST | /api/auth/google | Đổi `id_token` của Google lấy JWT hệ thống (tự tạo tài khoản CUSTOMER lần đầu) | public |
| POST | /api/payments/vnpay/create | Tạo link thanh toán VNPay cho phần còn nợ của đơn `{reservation_id}` | 🔒 khách |
| GET | /api/payments/vnpay/return | VNPay chuyển trình duyệt về; ghi nhận thanh toán rồi chuyển về web | public (xác thực bằng chữ ký) |
| GET | /api/payments/vnpay/ipn | VNPay gọi máy chủ-máy chủ; trả `RspCode` | public (xác thực bằng chữ ký) |
| GET | /api/provider/ai/schedule-optimize?studio_id=&day= | Tối ưu phân bổ phòng/thiết bị trong ngày | 🏢 |
