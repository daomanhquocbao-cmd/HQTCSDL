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

/* =====================================================================
   PHẦN C - TRIGGER
   ===================================================================== */

-- C1. Tự ghi lịch sử mỗi khi đơn được tạo hoặc đổi trạng thái.
--     Procedure truyền "ai đang thao tác" qua SESSION_CONTEXT (key 'user_id').
CREATE OR ALTER TRIGGER dbo.trg_Reservations_Audit
ON dbo.Reservations
AFTER INSERT, UPDATE
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @uid INT = TRY_CAST(SESSION_CONTEXT(N'user_id') AS INT);

    INSERT INTO dbo.ReservationStatusHistory (reservation_id, changed_by, old_status, new_status)
    SELECT i.reservation_id,
           ISNULL(@uid, CASE WHEN d.reservation_id IS NULL THEN i.customer_id END),
           d.status, i.status
    FROM inserted i
    LEFT JOIN deleted d ON d.reservation_id = i.reservation_id
    WHERE d.reservation_id IS NULL          -- vừa tạo mới
       OR d.status <> i.status;             -- hoặc đổi trạng thái
END;
GO

-- C2. Chỉ cho đánh giá khi đơn đã COMPLETED, đúng khách, đúng studio.
CREATE OR ALTER TRIGGER dbo.trg_Reviews_Validate
ON dbo.Reviews
AFTER INSERT, UPDATE
AS
BEGIN
    SET NOCOUNT ON;
    IF EXISTS (
        SELECT 1
        FROM inserted i
        JOIN dbo.Reservations r ON r.reservation_id = i.reservation_id
        JOIN dbo.Rooms rm ON rm.room_id = r.room_id
        WHERE r.status <> 'COMPLETED'
           OR r.customer_id <> i.customer_id
           OR rm.studio_id <> i.studio_id)
    BEGIN
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW 50900, N'Chỉ được đánh giá đơn đã hoàn thành của chính mình, và đúng studio.', 1;
    END
END;
GO

/* =====================================================================
   PHẦN D - STORED PROCEDURE
   ===================================================================== */

-- D1. Tính lại tổng tiền đơn = tiền phòng + thiết bị thuê thêm + gói dịch vụ
CREATE OR ALTER PROCEDURE dbo.sp_RecalculateReservationTotal
    @reservation_id INT
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @room_amount DECIMAL(18,2), @eq_amount DECIMAL(18,2), @pkg_amount DECIMAL(18,2);

    SELECT @room_amount = DATEDIFF(MINUTE, r.start_time, r.end_time) / 60.0 * rm.price_per_hour
    FROM dbo.Reservations r
    JOIN dbo.Rooms rm ON rm.room_id = r.room_id
    WHERE r.reservation_id = @reservation_id;

    IF @room_amount IS NULL THROW 50001, N'Không tìm thấy đơn đặt phòng.', 1;

    SELECT @eq_amount  = ISNULL(SUM(quantity * unit_price), 0) FROM dbo.ReservationEquipments WHERE reservation_id = @reservation_id;
    SELECT @pkg_amount = ISNULL(SUM(price), 0)                  FROM dbo.ReservationPackages   WHERE reservation_id = @reservation_id;

    UPDATE dbo.Reservations
    SET total_amount = @room_amount + @eq_amount + @pkg_amount
    WHERE reservation_id = @reservation_id;
END;
GO

-- D2. Tìm phòng còn trống theo thành phố / loại phòng / sức chứa / giá / khung giờ
CREATE OR ALTER PROCEDURE dbo.sp_SearchAvailableRooms
    @start_time   DATETIME,
    @end_time     DATETIME,
    @city         NVARCHAR(100) = NULL,
    @room_type    VARCHAR(20)   = NULL,
    @min_capacity INT           = NULL,
    @max_price    DECIMAL(18,2) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    IF @start_time >= @end_time THROW 50010, N'Giờ bắt đầu phải nhỏ hơn giờ kết thúc.', 1;

    SELECT rm.room_id, rm.name AS room_name, rm.room_type, rm.capacity, rm.price_per_hour,
           s.studio_id, s.name AS studio_name, s.city, s.address,
           ISNULL(sr.avg_rating, 0) AS avg_rating
    FROM dbo.Rooms rm
    JOIN dbo.Studios s ON s.studio_id = rm.studio_id
    LEFT JOIN dbo.vw_StudioRating sr ON sr.studio_id = s.studio_id
    WHERE rm.status = 'AVAILABLE'
      AND s.status = 'APPROVED'
      AND (@city IS NULL OR s.city = @city)
      AND (@room_type IS NULL OR rm.room_type = @room_type)
      AND (@min_capacity IS NULL OR rm.capacity >= @min_capacity)
      AND (@max_price IS NULL OR rm.price_per_hour <= @max_price)
      AND CAST(@start_time AS DATE) = CAST(@end_time AS DATE)          -- trong cùng 1 ngày
      AND CAST(@start_time AS TIME) >= s.open_time                      -- nằm trong giờ mở cửa
      AND CAST(@end_time   AS TIME) <= s.close_time
      AND NOT EXISTS (                                                  -- không đụng đơn nào khác
            SELECT 1 FROM dbo.Reservations r
            WHERE r.room_id = rm.room_id
              AND r.status IN ('PENDING', 'CONFIRMED', 'IN_USE')
              AND r.start_time < @end_time AND r.end_time > @start_time)
    ORDER BY avg_rating DESC, rm.price_per_hour;
END;
GO

-- D3. Đặt phòng - CHỐNG TRÙNG LỊCH khi nhiều người đặt cùng lúc.
--     Cách làm: khóa dòng phòng (UPDLOCK, HOLDLOCK) -> các giao dịch đặt CÙNG PHÒNG
--     phải xếp hàng, người sau sẽ thấy đơn của người trước rồi mới kiểm tra trùng.
CREATE OR ALTER PROCEDURE dbo.sp_CreateReservation
    @room_id        INT,
    @customer_id    INT,
    @start_time     DATETIME,
    @end_time       DATETIME,
    @customer_note  NVARCHAR(MAX) = NULL,
    @reservation_id INT = NULL OUTPUT
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        IF @start_time >= @end_time           THROW 50101, N'Giờ bắt đầu phải nhỏ hơn giờ kết thúc.', 1;
        IF @start_time < GETDATE()            THROW 50102, N'Không thể đặt phòng trong quá khứ.', 1;
        IF CAST(@start_time AS DATE) <> CAST(@end_time AS DATE)
                                              THROW 50103, N'Mỗi đơn chỉ đặt trong 1 ngày.', 1;
        IF NOT EXISTS (SELECT 1 FROM dbo.Users WHERE user_id = @customer_id AND role = 'CUSTOMER' AND status = 'ACTIVE')
                                              THROW 50104, N'Khách hàng không tồn tại hoặc tài khoản không hoạt động.', 1;

        BEGIN TRANSACTION;

        DECLARE @room_status VARCHAR(20), @studio_status VARCHAR(20),
                @price DECIMAL(18,2), @open TIME(0), @close TIME(0);

        SELECT @room_status = rm.status, @price = rm.price_per_hour,
               @studio_status = s.status, @open = s.open_time, @close = s.close_time
        FROM dbo.Rooms rm WITH (UPDLOCK, HOLDLOCK)        -- khóa dòng phòng
        JOIN dbo.Studios s ON s.studio_id = rm.studio_id
        WHERE rm.room_id = @room_id;

        IF @room_status IS NULL                THROW 50105, N'Không tìm thấy phòng.', 1;
        IF @room_status <> 'AVAILABLE' OR @studio_status <> 'APPROVED'
                                               THROW 50106, N'Phòng hiện không nhận đặt.', 1;
        IF CAST(@start_time AS TIME) < @open OR CAST(@end_time AS TIME) > @close
                                               THROW 50107, N'Khung giờ nằm ngoài giờ mở cửa của studio.', 1;

        IF EXISTS (SELECT 1 FROM dbo.Reservations
                   WHERE room_id = @room_id
                     AND status IN ('PENDING', 'CONFIRMED', 'IN_USE')
                     AND start_time < @end_time AND end_time > @start_time)
                                               THROW 50108, N'Phòng đã có người đặt trong khung giờ này.', 1;

        EXEC sys.sp_set_session_context @key = N'user_id', @value = @customer_id;   -- để trigger biết ai thao tác

        INSERT INTO dbo.Reservations (room_id, customer_id, start_time, end_time, total_amount, customer_note, status)
        VALUES (@room_id, @customer_id, @start_time, @end_time,
                DATEDIFF(MINUTE, @start_time, @end_time) / 60.0 * @price, @customer_note, 'PENDING');

        SET @reservation_id = SCOPE_IDENTITY();

        EXEC sys.sp_set_session_context @key = N'user_id', @value = NULL;
        COMMIT TRANSACTION;

        SELECT @reservation_id AS reservation_id, N'Đặt phòng thành công (PENDING)' AS result;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        EXEC sys.sp_set_session_context @key = N'user_id', @value = NULL;
        THROW;
    END CATCH
END;
GO

-- D4. Thuê thêm thiết bị cho đơn (kiểm tra tồn kho theo khung giờ)
CREATE OR ALTER PROCEDURE dbo.sp_AddReservationEquipment
    @reservation_id INT,
    @equipment_id   INT,
    @quantity       INT,
    @actor_id       INT
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        IF @quantity <= 0 THROW 50201, N'Số lượng phải lớn hơn 0.', 1;
        IF dbo.fn_CanManageReservation(@reservation_id, @actor_id) = 0
                          THROW 50202, N'Bạn không có quyền thao tác đơn này.', 1;

        BEGIN TRANSACTION;

        DECLARE @status VARCHAR(20), @start DATETIME, @end DATETIME, @studio_id INT;
        SELECT @status = r.status, @start = r.start_time, @end = r.end_time, @studio_id = rm.studio_id
        FROM dbo.Reservations r JOIN dbo.Rooms rm ON rm.room_id = r.room_id
        WHERE r.reservation_id = @reservation_id;

        IF @status NOT IN ('PENDING', 'CONFIRMED')
                          THROW 50203, N'Chỉ thêm thiết bị khi đơn đang PENDING hoặc CONFIRMED.', 1;

        DECLARE @eq_studio INT, @price DECIMAL(18,2);
        SELECT @eq_studio = studio_id, @price = rental_price
        FROM dbo.Equipment WITH (UPDLOCK, HOLDLOCK)          -- khóa dòng thiết bị: tránh 2 người cùng giành món cuối
        WHERE equipment_id = @equipment_id;

        IF @eq_studio IS NULL     THROW 50204, N'Không tìm thấy thiết bị.', 1;
        IF @eq_studio <> @studio_id THROW 50205, N'Thiết bị không thuộc studio của phòng đã đặt.', 1;

        IF @quantity + dbo.fn_ReservationEquipmentDemand(@reservation_id, @equipment_id)
               > dbo.fn_EquipmentAvailable(@equipment_id, @start, @end, @reservation_id)
                          THROW 50206, N'Thiết bị không đủ số lượng trong khung giờ này.', 1;

        IF EXISTS (SELECT 1 FROM dbo.ReservationEquipments WHERE reservation_id = @reservation_id AND equipment_id = @equipment_id)
            UPDATE dbo.ReservationEquipments SET quantity = quantity + @quantity
            WHERE reservation_id = @reservation_id AND equipment_id = @equipment_id;
        ELSE
            INSERT INTO dbo.ReservationEquipments (reservation_id, equipment_id, quantity, unit_price)
            VALUES (@reservation_id, @equipment_id, @quantity, @price);      -- lưu giá tại thời điểm đặt

        EXEC dbo.sp_RecalculateReservationTotal @reservation_id;
        COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;
GO

-- D5. Chọn gói dịch vụ cho đơn (kiểm tra gói + toàn bộ thiết bị đi kèm đủ hàng)
CREATE OR ALTER PROCEDURE dbo.sp_AddReservationPackage
    @reservation_id INT,
    @package_id     INT,
    @actor_id       INT,
    @notes          NVARCHAR(MAX) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        IF dbo.fn_CanManageReservation(@reservation_id, @actor_id) = 0
                          THROW 50301, N'Bạn không có quyền thao tác đơn này.', 1;

        BEGIN TRANSACTION;

        DECLARE @status VARCHAR(20), @start DATETIME, @end DATETIME, @studio_id INT, @room_type VARCHAR(20);
        SELECT @status = r.status, @start = r.start_time, @end = r.end_time,
               @studio_id = rm.studio_id, @room_type = rm.room_type
        FROM dbo.Reservations r JOIN dbo.Rooms rm ON rm.room_id = r.room_id
        WHERE r.reservation_id = @reservation_id;

        IF @status NOT IN ('PENDING', 'CONFIRMED')
                          THROW 50302, N'Chỉ thêm gói khi đơn đang PENDING hoặc CONFIRMED.', 1;

        DECLARE @pkg_studio INT, @pkg_type VARCHAR(20), @pkg_active BIT, @price DECIMAL(18,2);
        SELECT @pkg_studio = studio_id, @pkg_type = room_type, @pkg_active = is_active, @price = price
        FROM dbo.ServicePackages WHERE package_id = @package_id;

        IF @pkg_studio IS NULL     THROW 50303, N'Không tìm thấy gói dịch vụ.', 1;
        IF @pkg_active = 0         THROW 50304, N'Gói dịch vụ đã ngừng cung cấp.', 1;
        IF @pkg_studio <> @studio_id THROW 50305, N'Gói không thuộc studio của phòng đã đặt.', 1;
        IF @pkg_type IS NOT NULL AND @pkg_type <> @room_type
                          THROW 50306, N'Gói không phù hợp loại phòng đã đặt.', 1;
        IF EXISTS (SELECT 1 FROM dbo.ReservationPackages WHERE reservation_id = @reservation_id AND package_id = @package_id)
                          THROW 50307, N'Đơn đã chọn gói này rồi.', 1;

        -- khóa các dòng thiết bị của gói rồi mới kiểm tra tồn kho
        DECLARE @lock INT;
        SELECT @lock = COUNT(*) FROM dbo.Equipment WITH (UPDLOCK, HOLDLOCK)
        WHERE equipment_id IN (SELECT equipment_id FROM dbo.PackageEquipment WHERE package_id = @package_id);

        IF EXISTS (
            SELECT 1 FROM dbo.PackageEquipment pe
            WHERE pe.package_id = @package_id
              AND pe.quantity_included + dbo.fn_ReservationEquipmentDemand(@reservation_id, pe.equipment_id)
                  > dbo.fn_EquipmentAvailable(pe.equipment_id, @start, @end, @reservation_id))
                          THROW 50308, N'Thiết bị đi kèm gói không đủ số lượng trong khung giờ này.', 1;

        INSERT INTO dbo.ReservationPackages (reservation_id, package_id, price, notes)
        VALUES (@reservation_id, @package_id, @price, @notes);               -- lưu giá gói tại thời điểm đặt

        EXEC dbo.sp_RecalculateReservationTotal @reservation_id;
        COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;
GO

-- D6. Nhà cung cấp (hoặc admin) xác nhận đơn -> sinh mã QR để check-in
CREATE OR ALTER PROCEDURE dbo.sp_ConfirmReservation
    @reservation_id INT,
    @actor_id       INT
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRANSACTION;

        DECLARE @status VARCHAR(20), @provider_id INT;
        SELECT @status = r.status, @provider_id = s.provider_id
        FROM dbo.Reservations r WITH (UPDLOCK)
        JOIN dbo.Rooms rm ON rm.room_id = r.room_id
        JOIN dbo.Studios s ON s.studio_id = rm.studio_id
        WHERE r.reservation_id = @reservation_id;

        IF @status IS NULL THROW 50401, N'Không tìm thấy đơn.', 1;
        IF @actor_id <> @provider_id AND NOT EXISTS (SELECT 1 FROM dbo.Users WHERE user_id = @actor_id AND role = 'ADMIN')
                           THROW 50402, N'Chỉ chủ studio hoặc admin mới được xác nhận đơn.', 1;
        IF @status <> 'PENDING' THROW 50403, N'Chỉ xác nhận được đơn đang PENDING.', 1;

        EXEC sys.sp_set_session_context @key = N'user_id', @value = @actor_id;

        UPDATE dbo.Reservations
        SET status = 'CONFIRMED',
            qr_code = 'QR-' + RIGHT('00000' + CAST(@reservation_id AS VARCHAR(10)), 5) + '-'
                      + CAST(ABS(CHECKSUM(NEWID())) % 1000000 AS VARCHAR(10))
        WHERE reservation_id = @reservation_id;

        EXEC sys.sp_set_session_context @key = N'user_id', @value = NULL;
        COMMIT TRANSACTION;

        SELECT reservation_id, status, qr_code FROM dbo.Reservations WHERE reservation_id = @reservation_id;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        EXEC sys.sp_set_session_context @key = N'user_id', @value = NULL;
        THROW;
    END CATCH
END;
GO






