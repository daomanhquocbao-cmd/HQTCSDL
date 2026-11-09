USE FilmPhotographyPlatform;
GO
SET QUOTED_IDENTIFIER ON;
SET ANSI_NULLS ON;
GO

/* =====================================================================
   PHẦN A - HÀM (FUNCTION)
   ===================================================================== */

-- A1. Số lượng thiết bị mà 1 đơn đang cần (gồm thuê lẻ + thiết bị đi kèm gói)
CREATE OR ALTER FUNCTION dbo.fn_ReservationEquipmentDemand (@reservation_id INT, @equipment_id INT)
RETURNS INT
AS
BEGIN
    RETURN ISNULL((
        SELECT SUM(d.q) FROM (
            SELECT re.quantity AS q
            FROM dbo.ReservationEquipments re
            WHERE re.reservation_id = @reservation_id AND re.equipment_id = @equipment_id
            UNION ALL
            SELECT pe.quantity_included
            FROM dbo.ReservationPackages rp
            JOIN dbo.PackageEquipment pe ON pe.package_id = rp.package_id
            WHERE rp.reservation_id = @reservation_id AND pe.equipment_id = @equipment_id
        ) d), 0);
END;
GO

-- A2. Số lượng thiết bị CÒN TRỐNG trong khung giờ [@start, @end)
--     REUSABLE  : chỉ trừ những đơn trùng khung giờ (dùng xong trả lại kho)
--     CONSUMABLE: trừ mọi đơn chưa hoàn tất (vì dùng là hết)
--     @exclude_reservation_id: bỏ qua chính đơn đang xét
CREATE OR ALTER FUNCTION dbo.fn_EquipmentAvailable
    (@equipment_id INT, @start DATETIME, @end DATETIME, @exclude_reservation_id INT)
RETURNS INT
AS
BEGIN
    DECLARE @total INT, @type VARCHAR(20), @status VARCHAR(20), @used INT;

    SELECT @total = quantity, @type = equipment_type, @status = status
    FROM dbo.Equipment WHERE equipment_id = @equipment_id;

    IF @total IS NULL OR @status IN ('BROKEN', 'RETIRED', 'UNDER_MAINTENANCE')
        RETURN 0;

    SELECT @used = ISNULL(SUM(d.q), 0) FROM (
        SELECT re.quantity AS q
        FROM dbo.ReservationEquipments re
        JOIN dbo.Reservations r ON r.reservation_id = re.reservation_id
        WHERE re.equipment_id = @equipment_id
          AND r.reservation_id <> ISNULL(@exclude_reservation_id, 0)
          AND r.status IN ('PENDING', 'CONFIRMED', 'IN_USE')
          AND (@type = 'CONSUMABLE' OR (r.start_time < @end AND r.end_time > @start))
        UNION ALL
        SELECT pe.quantity_included
        FROM dbo.ReservationPackages rp
        JOIN dbo.PackageEquipment pe ON pe.package_id = rp.package_id
        JOIN dbo.Reservations r ON r.reservation_id = rp.reservation_id
        WHERE pe.equipment_id = @equipment_id
          AND r.reservation_id <> ISNULL(@exclude_reservation_id, 0)
          AND r.status IN ('PENDING', 'CONFIRMED', 'IN_USE')
          AND (@type = 'CONSUMABLE' OR (r.start_time < @end AND r.end_time > @start))
    ) d;

    RETURN CASE WHEN @total - @used < 0 THEN 0 ELSE @total - @used END;
END;
GO

-- A3. Phân quyền: người này có quyền thao tác đơn không? (khách chủ đơn / chủ studio / admin)
CREATE OR ALTER FUNCTION dbo.fn_CanManageReservation (@reservation_id INT, @actor_id INT)
RETURNS BIT
AS
BEGIN
    RETURN CAST(CASE
        WHEN EXISTS (
            SELECT 1
            FROM dbo.Reservations r
            JOIN dbo.Rooms rm ON rm.room_id = r.room_id
            JOIN dbo.Studios s ON s.studio_id = rm.studio_id
            WHERE r.reservation_id = @reservation_id
              AND (r.customer_id = @actor_id OR s.provider_id = @actor_id))
          OR EXISTS (SELECT 1 FROM dbo.Users WHERE user_id = @actor_id AND role = 'ADMIN' AND status = 'ACTIVE')
        THEN 1 ELSE 0 END AS BIT);
END;
GO

/* =====================================================================
   PHẦN B - VIEW
   ===================================================================== */

-- B1. Điểm đánh giá trung bình của từng studio đã duyệt
CREATE OR ALTER VIEW dbo.vw_StudioRating
AS
SELECT s.studio_id, s.name AS studio_name, s.city,
       COUNT(rv.review_id) AS review_count,
       CAST(AVG(CAST(rv.rating AS DECIMAL(4,2))) AS DECIMAL(3,2)) AS avg_rating
FROM dbo.Studios s
LEFT JOIN dbo.Reviews rv ON rv.studio_id = s.studio_id
WHERE s.status = 'APPROVED'
GROUP BY s.studio_id, s.name, s.city;
GO

-- B2. Chi tiết đơn đặt phòng kèm số tiền đã thanh toán và còn nợ
CREATE OR ALTER VIEW dbo.vw_ReservationDetail
AS
SELECT r.reservation_id, r.status, r.start_time, r.end_time,
       u.user_id AS customer_id, u.username AS customer,
       rm.room_id, rm.name AS room_name,
       s.studio_id, s.name AS studio_name, s.provider_id,
       r.total_amount,
       ISNULL(p.paid, 0) AS paid_amount,
       r.total_amount - ISNULL(p.paid, 0) AS balance_due
FROM dbo.Reservations r
JOIN dbo.Users u   ON u.user_id = r.customer_id
JOIN dbo.Rooms rm  ON rm.room_id = r.room_id
JOIN dbo.Studios s ON s.studio_id = rm.studio_id
LEFT JOIN (SELECT reservation_id, SUM(amount) AS paid
           FROM dbo.Payments WHERE status = 'SUCCESS'
           GROUP BY reservation_id) p ON p.reservation_id = r.reservation_id;
GO






