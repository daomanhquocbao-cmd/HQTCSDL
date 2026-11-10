USE FilmPhotographyPlatform;
GO

/* =====================================================================
   PHẦN A - BÁO CÁO NGHIỆP VỤ
   ===================================================================== */

-- A1. Doanh thu theo từng studio (chỉ tính giao dịch SUCCESS)
--     Điều kiện p.status đặt trong ON (không đặt trong WHERE) để studio chưa có doanh thu vẫn hiện, doanh thu = 0
SELECT s.studio_id, s.name AS studio_name,
       COUNT(DISTINCT r.reservation_id) AS total_reservations,
       ISNULL(SUM(p.amount), 0)         AS revenue
FROM dbo.Studios s
LEFT JOIN dbo.Rooms rm        ON rm.studio_id = s.studio_id
LEFT JOIN dbo.Reservations r  ON r.room_id = rm.room_id
LEFT JOIN dbo.Payments p      ON p.reservation_id = r.reservation_id AND p.status = 'SUCCESS'
GROUP BY s.studio_id, s.name
ORDER BY revenue DESC;
GO

-- A2. Doanh thu theo tháng + tăng trưởng so với tháng trước (hàm cửa sổ LAG)
WITH m AS (
    SELECT YEAR(p.paid_at) AS y, MONTH(p.paid_at) AS mth, SUM(p.amount) AS revenue
    FROM dbo.Payments p
    WHERE p.status = 'SUCCESS'
    GROUP BY YEAR(p.paid_at), MONTH(p.paid_at)
)
SELECT y, mth, revenue,
       LAG(revenue) OVER (ORDER BY y, mth) AS prev_month_revenue,
       CAST(100.0 * (revenue - LAG(revenue) OVER (ORDER BY y, mth))
            / NULLIF(LAG(revenue) OVER (ORDER BY y, mth), 0) AS DECIMAL(10,1)) AS growth_pct
FROM m
ORDER BY y, mth;
GO

-- A3. Tỉ lệ hủy đơn của từng studio
SELECT s.name AS studio_name,
       COUNT(*) AS total_reservations,
       SUM(CASE WHEN r.status = 'CANCELLED' THEN 1 ELSE 0 END) AS cancelled,
       CAST(100.0 * SUM(CASE WHEN r.status = 'CANCELLED' THEN 1 ELSE 0 END) / COUNT(*) AS DECIMAL(5,1)) AS cancel_rate_pct
FROM dbo.Reservations r
JOIN dbo.Rooms rm  ON rm.room_id = r.room_id
JOIN dbo.Studios s ON s.studio_id = rm.studio_id
GROUP BY s.name
ORDER BY cancel_rate_pct DESC;
GO

-- A4. Top 5 khách chi tiêu nhiều nhất (đơn đã hoàn thành)
SELECT TOP (5) u.user_id, u.full_name,
       COUNT(r.reservation_id) AS completed_reservations,
       SUM(r.total_amount)     AS total_spent
FROM dbo.Users u
JOIN dbo.Reservations r ON r.customer_id = u.user_id AND r.status = 'COMPLETED'
GROUP BY u.user_id, u.full_name
ORDER BY total_spent DESC;
GO

-- A5. Tỉ lệ lấp đầy từng phòng trong 30 ngày qua
--     = số giờ đã dùng / (30 ngày x số giờ mở cửa mỗi ngày)
SELECT rm.room_id, rm.name AS room_name, s.name AS studio_name,
       ISNULL(SUM(DATEDIFF(MINUTE, r.start_time, r.end_time)), 0) / 60.0 AS booked_hours,
       CAST(100.0 * ISNULL(SUM(DATEDIFF(MINUTE, r.start_time, r.end_time)), 0) / 60.0
            / (30 * DATEDIFF(HOUR, s.open_time, s.close_time)) AS DECIMAL(5,1)) AS occupancy_pct
FROM dbo.Rooms rm
JOIN dbo.Studios s ON s.studio_id = rm.studio_id
LEFT JOIN dbo.Reservations r
       ON r.room_id = rm.room_id
      AND r.status IN ('COMPLETED', 'IN_USE')
      AND r.start_time >= DATEADD(DAY, -30, GETDATE()) AND r.start_time < GETDATE()
WHERE s.status = 'APPROVED'
GROUP BY rm.room_id, rm.name, s.name, s.open_time, s.close_time
ORDER BY occupancy_pct DESC;
GO

-- A6. Giờ cao điểm: số đơn theo giờ bắt đầu (không tính đơn đã hủy)
SELECT DATEPART(HOUR, start_time) AS start_hour, COUNT(*) AS reservations
FROM dbo.Reservations
WHERE status <> 'CANCELLED'
GROUP BY DATEPART(HOUR, start_time)
ORDER BY reservations DESC;
GO

-- A7. Cảnh báo thiết bị: hỏng / cần bảo trì / quá hạn hoặc sắp tới hạn bảo trì (14 ngày) / vật tư sắp hết
SELECT s.name AS studio_name, e.name AS equipment_name, e.equipment_type, e.quantity, e.status,
       e.next_maintenance_date,
       CASE WHEN e.status IN ('BROKEN', 'NEEDS_MAINTENANCE', 'UNDER_MAINTENANCE') THEN N'Tình trạng: ' + e.status
            WHEN e.next_maintenance_date < CAST(GETDATE() AS DATE)                THEN N'Quá hạn bảo trì'
            WHEN e.next_maintenance_date <= DATEADD(DAY, 14, CAST(GETDATE() AS DATE)) THEN N'Sắp đến hạn bảo trì'
            WHEN e.equipment_type = 'CONSUMABLE' AND e.quantity < 10              THEN N'Vật tư sắp hết'
       END AS warning
FROM dbo.Equipment e
JOIN dbo.Studios s ON s.studio_id = e.studio_id
WHERE e.status IN ('BROKEN', 'NEEDS_MAINTENANCE', 'UNDER_MAINTENANCE')
   OR e.next_maintenance_date <= DATEADD(DAY, 14, CAST(GETDATE() AS DATE))
   OR (e.equipment_type = 'CONSUMABLE' AND e.quantity < 10)
ORDER BY s.name, e.name;
GO

-- A8. Chi phí bảo trì theo studio
SELECT s.name AS studio_name, COUNT(*) AS maintenance_count, SUM(m.cost) AS total_cost
FROM dbo.EquipmentMaintenance m
JOIN dbo.Equipment e ON e.equipment_id = m.equipment_id
JOIN dbo.Studios s   ON s.studio_id = e.studio_id
WHERE m.status = 'DONE'
GROUP BY s.name
ORDER BY total_cost DESC;
GO

-- A9. Xếp hạng studio theo điểm đánh giá (dùng view, chỉ xét studio có từ 2 đánh giá)
SELECT studio_name, city, review_count, avg_rating
FROM dbo.vw_StudioRating
WHERE review_count >= 2
ORDER BY avg_rating DESC, review_count DESC;
GO

-- A10. Thống kê workshop: số đăng ký, còn lại bao nhiêu chỗ, doanh thu phí tham dự
SELECT w.workshop_id, w.title, u.full_name AS expert_name, w.status,
       w.capacity, COUNT(wr.registration_id) AS registered,
       w.capacity - COUNT(wr.registration_id) AS remaining_slots,
       w.fee * COUNT(wr.registration_id) AS expected_fee_revenue
FROM dbo.Workshops w
JOIN dbo.Users u ON u.user_id = w.expert_id
LEFT JOIN dbo.WorkshopRegistrations wr ON wr.workshop_id = w.workshop_id
GROUP BY w.workshop_id, w.title, u.full_name, w.status, w.capacity, w.fee, w.start_time
ORDER BY w.start_time;
GO

-- A11. Đơn còn nợ tiền (đã xác nhận / đang dùng / hoàn thành nhưng chưa trả đủ) - dùng view
SELECT reservation_id, customer, studio_name, status, total_amount, paid_amount, balance_due
FROM dbo.vw_ReservationDetail
WHERE status IN ('CONFIRMED', 'IN_USE', 'COMPLETED') AND balance_due > 0
ORDER BY balance_due DESC;
GO

-- A12. Lịch sử đặt phòng của 1 khách (đổi @cid để tra khách khác)
DECLARE @cid INT = (SELECT user_id FROM dbo.Users WHERE username = 'customer001');
SELECT reservation_id, room_name, studio_name, start_time, end_time, total_amount, paid_amount, status
FROM dbo.vw_ReservationDetail
WHERE customer_id = @cid
ORDER BY start_time DESC;
GO

/* =====================================================================
   PHẦN B - KIỂM TRA TOÀN VẸN DỮ LIỆU (mỗi truy vấn phải trả về 0 dòng)
   ===================================================================== */

-- B1. Hai đơn còn hiệu lực cùng phòng bị chồng giờ
SELECT a.reservation_id AS res_a, b.reservation_id AS res_b, a.room_id
FROM dbo.Reservations a
JOIN dbo.Reservations b ON a.room_id = b.room_id AND a.reservation_id < b.reservation_id
WHERE a.status IN ('PENDING', 'CONFIRMED', 'IN_USE') AND b.status IN ('PENDING', 'CONFIRMED', 'IN_USE')
  AND a.start_time < b.end_time AND a.end_time > b.start_time;
GO

-- B2. Đơn bị thanh toán vượt tổng tiền
SELECT r.reservation_id, r.total_amount, SUM(p.amount) AS paid
FROM dbo.Reservations r
JOIN dbo.Payments p ON p.reservation_id = r.reservation_id AND p.status = 'SUCCESS'
GROUP BY r.reservation_id, r.total_amount
HAVING SUM(p.amount) > r.total_amount;
GO

-- B3. Tổng tiền đơn không khớp công thức (phòng + thiết bị + gói)
SELECT r.reservation_id, r.total_amount,
       CAST(DATEDIFF(MINUTE, r.start_time, r.end_time) / 60.0 * rm.price_per_hour AS DECIMAL(18,2))
       + ISNULL((SELECT SUM(quantity * unit_price) FROM dbo.ReservationEquipments WHERE reservation_id = r.reservation_id), 0)
       + ISNULL((SELECT SUM(price) FROM dbo.ReservationPackages WHERE reservation_id = r.reservation_id), 0) AS expected_total
FROM dbo.Reservations r
JOIN dbo.Rooms rm ON rm.room_id = r.room_id
WHERE ABS(r.total_amount
          - (CAST(DATEDIFF(MINUTE, r.start_time, r.end_time) / 60.0 * rm.price_per_hour AS DECIMAL(18,2))
             + ISNULL((SELECT SUM(quantity * unit_price) FROM dbo.ReservationEquipments WHERE reservation_id = r.reservation_id), 0)
             + ISNULL((SELECT SUM(price) FROM dbo.ReservationPackages WHERE reservation_id = r.reservation_id), 0))) > 0.01;
GO

-- B4. Workshop có số đăng ký vượt sức chứa
SELECT w.workshop_id, w.capacity, COUNT(*) AS registered
FROM dbo.Workshops w
JOIN dbo.WorkshopRegistrations wr ON wr.workshop_id = w.workshop_id
GROUP BY w.workshop_id, w.capacity
HAVING COUNT(*) > w.capacity;
GO

/* =====================================================================
   PHẦN C - KỊCH BẢN DEMO STORED PROCEDURE
   Chạy từng khối (bôi đen + F5) hoặc chạy cả phần C một lượt.
   Đơn demo đặt vào ~60 ngày sau, giờ 10:00-12:00 để không đụng dữ liệu mẫu.
   ===================================================================== */

DECLARE @cust INT = (SELECT user_id FROM dbo.Users WHERE username = 'customer001');
DECLARE @cust2 INT = (SELECT user_id FROM dbo.Users WHERE username = 'customer002');
DECLARE @admin INT = (SELECT user_id FROM dbo.Users WHERE username = 'admin');
DECLARE @room INT, @studio INT, @provider INT;

SELECT TOP (1) @room = rm.room_id, @studio = s.studio_id, @provider = s.provider_id
FROM dbo.Rooms rm JOIN dbo.Studios s ON s.studio_id = rm.studio_id
WHERE rm.room_type = 'STUDIO' AND rm.status = 'AVAILABLE' AND s.status = 'APPROVED'
ORDER BY rm.room_id;

DECLARE @day DATETIME = DATEADD(DAY, 60, CAST(CAST(GETDATE() AS DATE) AS DATETIME));
DECLARE @start DATETIME = DATEADD(HOUR, 10, @day);
DECLARE @end   DATETIME = DATEADD(HOUR, 12, @day);

PRINT N'--- Bước 1: tìm phòng còn trống ---';
EXEC dbo.sp_SearchAvailableRooms @start_time = @start, @end_time = @end, @room_type = 'STUDIO';

PRINT N'--- Bước 2: khách 1 đặt phòng (thành công) ---';
DECLARE @res INT;
EXEC dbo.sp_CreateReservation @room_id = @room, @customer_id = @cust,
     @start_time = @start, @end_time = @end, @customer_note = N'Demo đặt phòng', @reservation_id = @res OUTPUT;

PRINT N'--- Bước 3: khách 2 đặt TRÙNG khung giờ -> phải báo lỗi 50108 ---';
BEGIN TRY
    EXEC dbo.sp_CreateReservation @room_id = @room, @customer_id = @cust2,
         @start_time = @start, @end_time = @end;
END TRY
BEGIN CATCH
    PRINT N'Đã chặn đúng: ' + ERROR_MESSAGE();
END CATCH

PRINT N'--- Bước 4: thuê thêm 1 máy ảnh + chọn gói Chân dung ---';
DECLARE @eq INT = (SELECT equipment_id FROM dbo.Equipment WHERE studio_id = @studio AND category = 'CAMERA');
DECLARE @pkg INT = (SELECT package_id FROM dbo.ServicePackages WHERE studio_id = @studio AND name = N'Gói Chân dung');
EXEC dbo.sp_AddReservationEquipment @reservation_id = @res, @equipment_id = @eq, @quantity = 1, @actor_id = @cust;
EXEC dbo.sp_AddReservationPackage   @reservation_id = @res, @package_id = @pkg, @actor_id = @cust;
SELECT reservation_id, status, total_amount FROM dbo.Reservations WHERE reservation_id = @res;

PRINT N'--- Bước 5: thuê vượt số lượng tồn -> phải báo lỗi 50206 ---';
BEGIN TRY
    EXEC dbo.sp_AddReservationEquipment @reservation_id = @res, @equipment_id = @eq, @quantity = 999, @actor_id = @cust;
END TRY
BEGIN CATCH
    PRINT N'Đã chặn đúng: ' + ERROR_MESSAGE();
END CATCH

PRINT N'--- Bước 6: chủ studio xác nhận đơn -> sinh mã QR ---';
EXEC dbo.sp_ConfirmReservation @reservation_id = @res, @actor_id = @provider;

PRINT N'--- Bước 7: thanh toán cọc 50%, sau đó thử trả vượt tổng tiền -> báo lỗi 50804 ---';
DECLARE @total DECIMAL(18,2) = (SELECT total_amount FROM dbo.Reservations WHERE reservation_id = @res);
DECLARE @tx1 VARCHAR(100) = 'DEMO' + CAST(@res AS VARCHAR(10)) + 'X' + CAST(ABS(CHECKSUM(NEWID())) % 100000 AS VARCHAR(10));
DECLARE @half DECIMAL(18,2) = ROUND(@total * 0.5, 0);
EXEC dbo.sp_ProcessPayment @reservation_id = @res, @amount = @half, @payment_method = 'VNPAY',
     @actor_id = @cust, @transaction_code = @tx1;
BEGIN TRY
    EXEC dbo.sp_ProcessPayment @reservation_id = @res, @amount = @total, @payment_method = 'VNPAY', @actor_id = @cust;
END TRY
BEGIN CATCH
    PRINT N'Đã chặn đúng: ' + ERROR_MESSAGE();
END CATCH

PRINT N'--- Bước 8: check-in sớm (đơn ở 60 ngày sau) -> phải báo lỗi 50604 ---';
DECLARE @qr VARCHAR(100) = (SELECT qr_code FROM dbo.Reservations WHERE reservation_id = @res);
BEGIN TRY
    EXEC dbo.sp_CheckIn @qr_code = @qr, @actor_id = @provider;
END TRY
BEGIN CATCH
    PRINT N'Đã chặn đúng: ' + ERROR_MESSAGE();
END CATCH

PRINT N'--- Bước 9: khách hủy đơn (còn > 24h) -> được hoàn tiền ---';
EXEC dbo.sp_CancelReservation @reservation_id = @res, @actor_id = @cust;

PRINT N'--- Bước 10: lịch sử trạng thái do trigger tự ghi ---';
SELECT history_id, old_status, new_status, changed_by, changed_at
FROM dbo.ReservationStatusHistory WHERE reservation_id = @res ORDER BY history_id;

PRINT N'--- Bước 11: đăng ký workshop (đã đủ chỗ -> lỗi 50903; còn chỗ -> thành công) ---';
DECLARE @wFull INT = (SELECT TOP (1) workshop_id FROM dbo.Workshops WHERE status = 'CLOSED' AND start_time > GETDATE());
DECLARE @wOpen INT = (SELECT TOP (1) workshop_id FROM dbo.Workshops WHERE status = 'OPEN' AND start_time > GETDATE() ORDER BY workshop_id);
DECLARE @cust3 INT = (SELECT user_id FROM dbo.Users WHERE username = 'customer015');
BEGIN TRY
    EXEC dbo.sp_RegisterWorkshop @workshop_id = @wFull, @customer_id = @cust3;
END TRY
BEGIN CATCH
    PRINT N'Đã chặn đúng: ' + ERROR_MESSAGE();
END CATCH
BEGIN TRY
    EXEC dbo.sp_RegisterWorkshop @workshop_id = @wOpen, @customer_id = @cust3;
END TRY
BEGIN CATCH
    PRINT N'Lưu ý (chạy lại lần 2 sẽ báo đã đăng ký): ' + ERROR_MESSAGE();
END CATCH
GO
