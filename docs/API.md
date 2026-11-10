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

## Stats
| Method | Path | Mô tả | Quyền |
|---|---|---|---|
| GET | /api/stats/summary | Số đơn, user theo role, studio, phòng, doanh thu | 👑 |

## Mã lỗi
`400` sai trạng thái / dữ liệu · `401` token sai hoặc hết hạn · `403` thiếu token hoặc không đủ quyền ·
`404` không tìm thấy · `409` trùng (username/email, khung giờ) · `422` dữ liệu không hợp lệ.
