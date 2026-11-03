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

-- 2. BÁO CÁO: Kiểm tra danh sách thiết bị cần bảo trì hoặc sắp hết hạn
SELECT 
    eq.equipment_id,
    s.name AS StudioName,
    eq.name AS EquipmentName,
    eq.equipment_type,
    eq.quantity,
    eq.status
FROM dbo.Equipment eq
JOIN dbo.Studios s ON eq.studio_id = s.studio_id
WHERE eq.status <> 'GOOD' OR eq.quantity < 3;
GO

-- 3. BÁO CÁO: Lịch sử đặt phòng chi tiết của một Khách hàng cụ thể
SELECT 
    r.reservation_id,
    u.username AS CustomerName,
    rm.name AS RoomName,
    s.name AS StudioName,
    r.start_time,
    r.end_time,
    r.total_amount,
    r.status
FROM dbo.Reservations r
JOIN dbo.Users u ON r.customer_id = u.user_id
JOIN dbo.Rooms rm ON r.room_id = rm.room_id
JOIN dbo.Studios s ON rm.studio_id = s.studio_id
WHERE u.user_id = 3 -- Thay ID khách hàng cần tra cứu vào đây
ORDER BY r.start_time DESC;
GO
