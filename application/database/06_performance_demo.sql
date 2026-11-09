USE FilmPhotographyPlatform;
GO
SET NOCOUNT ON;
SET STATISTICS TIME ON;
SET STATISTICS IO ON;
GO

/* =====================================================================
   PHẦN 1 - CÁC TRUY VẤN "NẶNG" TRÊN TOÀN BỘ DỮ LIỆU
   ===================================================================== */

PRINT N'--- 1.1 Tìm phòng trống toàn hệ thống (1 tuần nữa, 10h-12h, TP.HCM) ---';
DECLARE @s DATETIME = DATEADD(HOUR, 10, CAST(CAST(DATEADD(DAY, 7, GETDATE()) AS DATE) AS DATETIME));
DECLARE @e DATETIME = DATEADD(HOUR, 2, @s);
EXEC dbo.sp_SearchAvailableRooms @start_time = @s, @end_time = @e, @city = N'TP.HCM', @room_type = 'STUDIO';
GO

PRINT N'--- 1.2 Doanh thu theo studio ---';
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

PRINT N'--- 1.3 Doanh thu theo tháng + tăng trưởng ---';
WITH m AS (
    SELECT YEAR(p.paid_at) AS y, MONTH(p.paid_at) AS mth, SUM(p.amount) AS revenue
    FROM dbo.Payments p WHERE p.status = 'SUCCESS'
    GROUP BY YEAR(p.paid_at), MONTH(p.paid_at)
)
SELECT y, mth, revenue,
       CAST(100.0 * (revenue - LAG(revenue) OVER (ORDER BY y, mth))
            / NULLIF(LAG(revenue) OVER (ORDER BY y, mth), 0) AS DECIMAL(10,1)) AS growth_pct
FROM m ORDER BY y, mth;
GO

PRINT N'--- 1.4 Top 10 khách chi tiêu nhiều nhất ---';
SELECT TOP (10) u.user_id, u.full_name,
       COUNT(r.reservation_id) AS completed_reservations, SUM(r.total_amount) AS total_spent
FROM dbo.Users u
JOIN dbo.Reservations r ON r.customer_id = u.user_id AND r.status = 'COMPLETED'
GROUP BY u.user_id, u.full_name
ORDER BY total_spent DESC;
GO

PRINT N'--- 1.5 Xếp hạng studio theo điểm đánh giá ---';
SELECT TOP (20) studio_name, city, review_count, avg_rating
FROM dbo.vw_StudioRating
WHERE review_count >= 10
ORDER BY avg_rating DESC, review_count DESC;
GO

PRINT N'--- 1.6 Tỉ lệ lấp đầy từng phòng 30 ngày qua ---';
SELECT TOP (20) rm.room_id, rm.name AS room_name, s.name AS studio_name,
       CAST(100.0 * ISNULL(SUM(DATEDIFF(MINUTE, r.start_time, r.end_time)), 0) / 60.0
            / (30 * DATEDIFF(HOUR, s.open_time, s.close_time)) AS DECIMAL(5,1)) AS occupancy_pct
FROM dbo.Rooms rm
JOIN dbo.Studios s ON s.studio_id = rm.studio_id
LEFT JOIN dbo.Reservations r
       ON r.room_id = rm.room_id AND r.status IN ('COMPLETED', 'IN_USE')
      AND r.start_time >= DATEADD(DAY, -30, GETDATE()) AND r.start_time < GETDATE()
WHERE s.status = 'APPROVED'
GROUP BY rm.room_id, rm.name, s.name, s.open_time, s.close_time
ORDER BY occupancy_pct DESC;
GO

