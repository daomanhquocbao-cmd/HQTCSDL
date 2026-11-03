USE FilmPhotographyPlatform;
GO

-- =====================================================================
-- 06_extra_reports.sql : các truy vấn báo cáo bổ sung (bổ sung cho 04)
-- =====================================================================

-- 1. Doanh thu theo Studio (chỉ tính thanh toán thành công)
SELECT s.studio_id, s.name AS studio_name,
       COUNT(p.payment_id) AS total_payments,
       SUM(p.amount)       AS total_revenue
FROM dbo.Payments p
JOIN dbo.Reservations res ON res.reservation_id = p.reservation_id
JOIN dbo.Rooms r          ON r.room_id = res.room_id
JOIN dbo.Studios s        ON s.studio_id = r.studio_id
WHERE p.status = 'SUCCESS'
GROUP BY s.studio_id, s.name
ORDER BY total_revenue DESC;
GO

-- 2. Doanh thu theo tháng
SELECT YEAR(p.created_at) AS [year], MONTH(p.created_at) AS [month],
       SUM(p.amount) AS revenue, COUNT(*) AS total_payments
FROM dbo.Payments p
WHERE p.status = 'SUCCESS'
GROUP BY YEAR(p.created_at), MONTH(p.created_at)
ORDER BY [year], [month];
GO

-- 3. Top 10 phòng được đặt nhiều nhất (không tính đơn đã hủy)
SELECT TOP 10 r.room_id, r.name AS room_name, s.name AS studio_name,
       COUNT(*) AS total_bookings
FROM dbo.Reservations res
JOIN dbo.Rooms r ON r.room_id = res.room_id
LEFT JOIN dbo.Studios s ON s.studio_id = r.studio_id
WHERE res.status <> 'CANCELLED'
GROUP BY r.room_id, r.name, s.name
ORDER BY total_bookings DESC;
GO

-- 4. Tỷ lệ hủy đơn theo Studio
SELECT s.studio_id, s.name AS studio_name,
       COUNT(*) AS total_reservations,
       SUM(CASE WHEN res.status = 'CANCELLED' THEN 1 ELSE 0 END) AS cancelled,
       CAST(100.0 * SUM(CASE WHEN res.status = 'CANCELLED' THEN 1 ELSE 0 END) / COUNT(*) AS DECIMAL(5,2)) AS cancel_rate_percent
FROM dbo.Reservations res
JOIN dbo.Rooms r   ON r.room_id = res.room_id
JOIN dbo.Studios s ON s.studio_id = r.studio_id
GROUP BY s.studio_id, s.name
ORDER BY cancel_rate_percent DESC;
GO

-- 5. Studio có điểm đánh giá trung bình cao nhất (tối thiểu 5 đánh giá)
SELECT TOP 10 s.studio_id, s.name AS studio_name,
       CAST(AVG(CAST(rv.rating AS FLOAT)) AS DECIMAL(3,2)) AS avg_rating,
       COUNT(*) AS review_count
FROM dbo.Reviews rv
JOIN dbo.Studios s ON s.studio_id = rv.studio_id
GROUP BY s.studio_id, s.name
HAVING COUNT(*) >= 5
ORDER BY avg_rating DESC, review_count DESC;
GO

-- 6. Top 10 khách hàng đặt phòng nhiều nhất và tổng chi tiêu
SELECT TOP 10 u.user_id, u.username, COUNT(*) AS total_reservations,
       SUM(res.total_amount) AS total_spent
FROM dbo.Reservations res
JOIN dbo.Users u ON u.user_id = res.customer_id
WHERE res.status IN ('CONFIRMED', 'COMPLETED')
GROUP BY u.user_id, u.username
ORDER BY total_spent DESC;
GO

-- 7. Phòng chưa từng được đặt
SELECT r.room_id, r.name, r.room_type, r.price_per_hour
FROM dbo.Rooms r
WHERE NOT EXISTS (SELECT 1 FROM dbo.Reservations res WHERE res.room_id = r.room_id);
GO

-- 8. Phòng còn trống trong một khung giờ (đổi 2 biến ngày giờ để thử)
DECLARE @start_time DATETIME = '2026-12-01 09:00';
DECLARE @end_time   DATETIME = '2026-12-01 12:00';

SELECT r.room_id, r.name, r.room_type, r.capacity, r.price_per_hour
FROM dbo.Rooms r
WHERE r.status = 'AVAILABLE'
  AND NOT EXISTS (
      SELECT 1 FROM dbo.Reservations res
      WHERE res.room_id = r.room_id
        AND res.status IN ('PENDING', 'CONFIRMED')
        AND @start_time < res.end_time AND @end_time > res.start_time
  );
GO

-- 9. Tổng chi phí bảo trì thiết bị theo Studio
SELECT s.studio_id, s.name AS studio_name,
       COUNT(m.maintenance_id) AS maintenance_count,
       SUM(m.cost) AS total_cost
FROM dbo.EquipmentMaintenance m
JOIN dbo.Equipment e ON e.equipment_id = m.equipment_id
JOIN dbo.Studios s   ON s.studio_id = e.studio_id
GROUP BY s.studio_id, s.name
ORDER BY total_cost DESC;
GO

-- 10. Mức độ lấp đầy của Workshop
SELECT w.workshop_id, w.title, w.capacity,
       COUNT(wr.registration_id) AS registered,
       CAST(100.0 * COUNT(wr.registration_id) / w.capacity AS DECIMAL(5,2)) AS fill_rate_percent
FROM dbo.Workshops w
LEFT JOIN dbo.WorkshopRegistrations wr ON wr.workshop_id = w.workshop_id
GROUP BY w.workshop_id, w.title, w.capacity
ORDER BY fill_rate_percent DESC;
GO

-- 11. Thống kê thanh toán theo phương thức
SELECT payment_method, status, COUNT(*) AS total, SUM(amount) AS total_amount
FROM dbo.Payments
GROUP BY payment_method, status
ORDER BY payment_method, status;
GO

-- 12. Khung giờ cao điểm (số đơn theo giờ bắt đầu)
SELECT DATEPART(HOUR, start_time) AS start_hour, COUNT(*) AS total_reservations
FROM dbo.Reservations
WHERE status <> 'CANCELLED'
GROUP BY DATEPART(HOUR, start_time)
ORDER BY total_reservations DESC;
GO

-- 13. Lịch sử đổi trạng thái của một đơn (đổi @reservation_id)
DECLARE @reservation_id INT = 1;
SELECT h.history_id, h.old_status, h.new_status, u.username AS changed_by, h.changed_at
FROM dbo.ReservationStatusHistory h
LEFT JOIN dbo.Users u ON u.user_id = h.changed_by
WHERE h.reservation_id = @reservation_id
ORDER BY h.changed_at;
GO
