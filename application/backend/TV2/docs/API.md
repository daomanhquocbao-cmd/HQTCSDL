# Tài liệu API

Base URL: `http://localhost:8000` · Swagger: `/docs`

Các endpoint có 🔒 cần header `Authorization: Bearer <token>`; 👑 chỉ admin.

## Users
| Method | Path | Mô tả | Quyền |
|---|---|---|---|
| POST | /api/users/register | Đăng ký (mật khẩu ≥ 8 ký tự) | public |
| POST | /api/users/login | Đăng nhập, nhận JWT | public |
| GET | /api/users/me | Thông tin tài khoản hiện tại | 🔒 |

## Rooms
| Method | Path | Mô tả | Quyền |
|---|---|---|---|
| GET | /api/rooms | Danh sách phòng đang hoạt động | public |
| GET | /api/rooms/{id} | Chi tiết phòng | public |
| POST | /api/rooms | Tạo phòng | 👑 |
| PATCH | /api/rooms/{id} | Cập nhật phòng | 👑 |
| DELETE | /api/rooms/{id} | Xóa mềm (is_active = 0) | 👑 |

## Bookings
| Method | Path | Mô tả | Quyền |
|---|---|---|---|
| POST | /api/bookings | Tạo booking | 🔒 |
| GET | /api/bookings?status= | Booking của tôi | 🔒 |
| GET | /api/bookings/{id} | Chi tiết | 🔒 |
| PATCH | /api/bookings/{id}/cancel | Hủy booking | 🔒 |

## Stats
| Method | Path | Mô tả | Quyền |
|---|---|---|---|
| GET | /api/stats/summary | Thống kê tổng quan | 👑 |

## Mã lỗi
`400` sai trạng thái · `401` token sai/hết hạn · `403` thiếu token hoặc không đủ quyền ·
`404` không tìm thấy · `409` trùng (email, khung giờ) · `422` dữ liệu không hợp lệ.
