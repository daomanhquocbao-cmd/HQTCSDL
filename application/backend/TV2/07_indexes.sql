USE FilmPhotographyPlatform;
GO

-- =====================================================================
-- 07_indexes.sql : index cho các truy vấn của API.
-- Bảng Reservations có ~10 triệu dòng (xem 02_seed_data.sql) nên thiếu index
-- thì mỗi lần lọc theo customer_id / room_id đều phải quét toàn bảng.
-- Chạy file này SAU 02. Tạo index trên 10 triệu dòng có thể mất vài phút.
-- =====================================================================

-- Danh sách đơn của một khách (GET /api/bookings)
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_Reservations_Customer_Start' AND object_id = OBJECT_ID('dbo.Reservations'))
    CREATE NONCLUSTERED INDEX IX_Reservations_Customer_Start
    ON dbo.Reservations (customer_id, start_time DESC) INCLUDE (status);
GO

-- Kiểm tra trùng lịch trong sp_CreateReservation và tìm phòng trống
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_Reservations_Room_Time' AND object_id = OBJECT_ID('dbo.Reservations'))
    CREATE NONCLUSTERED INDEX IX_Reservations_Room_Time
    ON dbo.Reservations (room_id, start_time, end_time) INCLUDE (status);
GO

-- Thống kê theo trạng thái (GET /api/stats/summary)
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_Reservations_Status' AND object_id = OBJECT_ID('dbo.Reservations'))
    CREATE NONCLUSTERED INDEX IX_Reservations_Status ON dbo.Reservations (status);
GO

-- Doanh thu: nối Payments với Reservations
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_Payments_Reservation' AND object_id = OBJECT_ID('dbo.Payments'))
    CREATE NONCLUSTERED INDEX IX_Payments_Reservation
    ON dbo.Payments (reservation_id) INCLUDE (amount, status);
GO

-- Điểm đánh giá trung bình của studio
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_Reviews_Studio' AND object_id = OBJECT_ID('dbo.Reviews'))
    CREATE NONCLUSTERED INDEX IX_Reviews_Studio ON dbo.Reviews (studio_id) INCLUDE (rating);
GO

-- Lọc phòng theo studio
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_Rooms_Studio' AND object_id = OBJECT_ID('dbo.Rooms'))
    CREATE NONCLUSTERED INDEX IX_Rooms_Studio ON dbo.Rooms (studio_id);
GO
