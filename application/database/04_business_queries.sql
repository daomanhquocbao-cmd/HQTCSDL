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
