USE FilmPhotographyPlatform;
GO

-- 1. BÁO CÁO: Thống kê tổng doanh thu theo từng Studio
SELECT 
    s.studio_id,
    s.name AS StudioName,
    COUNT(r.reservation_id) AS TotalReservations,
    SUM(p.amount) AS TotalRevenue
FROM dbo.Studios s
JOIN dbo.Rooms rm ON s.studio_id = rm.studio_id
JOIN dbo.Reservations r ON rm.room_id = r.room_id
LEFT JOIN dbo.Payments p ON r.reservation_id = p.reservation_id
WHERE p.status = 'SUCCESS'
GROUP BY s.studio_id, s.name
ORDER BY TotalRevenue DESC;
GO
