# Changelog

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
