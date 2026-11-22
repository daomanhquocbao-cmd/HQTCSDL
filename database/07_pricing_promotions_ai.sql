/* =====================================================================
   07_pricing_promotions_ai.sql
   Bổ sung: quy tắc giá, khuyến mãi, hàm tính giá, gợi ý phòng, dự báo nhu cầu.
   Chạy SAU 01..03 và 06_provider_additions.sql. An toàn khi chạy lại nhiều lần.

   LƯU Ý: file này CREATE OR ALTER lại dbo.sp_RecalculateReservationTotal (đã có ở 03)
   để tiền phòng tính theo quy tắc giá và trừ khuyến mãi. Nếu chạy lại 03 sau file này,
   hãy chạy lại 07 để giữ hành vi mới.
   Truy vấn kiểm tra B3 trong 04_business_queries.sql dùng công thức giá phẳng, nên có
   thể báo các đơn đã áp quy tắc giá hoặc khuyến mãi là "lệch" - đó là chủ ý.
   ===================================================================== */
USE FilmPhotographyPlatform;
GO
SET QUOTED_IDENTIFIER ON;
SET ANSI_NULLS ON;
GO

/* ---------------------------------------------------------------
   1. BẢNG
   --------------------------------------------------------------- */
-- Khuyến mãi của từng studio (mã giảm giá)
IF OBJECT_ID(N'dbo.Promotions', N'U') IS NULL
CREATE TABLE dbo.Promotions (
    promo_id         INT IDENTITY(1,1) NOT NULL,
    studio_id        INT           NOT NULL,
    code             VARCHAR(30)   NOT NULL,
    title            NVARCHAR(150) NOT NULL,
    discount_type    VARCHAR(10)   NOT NULL,                 -- PERCENT: giảm theo %, FIXED: giảm số tiền cố định
    discount_value   DECIMAL(18,2) NOT NULL,
    max_discount     DECIMAL(18,2) NULL,                     -- trần giảm khi dùng PERCENT
    min_order_amount DECIMAL(18,2) NOT NULL CONSTRAINT DF_Promo_minamt DEFAULT 0,
    start_date       DATE          NOT NULL,
    end_date         DATE          NOT NULL,
    max_uses         INT           NULL,                     -- NULL = không giới hạn lượt
    used_count       INT           NOT NULL CONSTRAINT DF_Promo_used DEFAULT 0,
    status           VARCHAR(10)   NOT NULL CONSTRAINT DF_Promo_status DEFAULT 'ACTIVE',
    created_at       DATETIME      NOT NULL CONSTRAINT DF_Promo_created DEFAULT GETDATE(),
    CONSTRAINT PK_Promotions PRIMARY KEY (promo_id),
    CONSTRAINT FK_Promo_Studio FOREIGN KEY (studio_id) REFERENCES dbo.Studios(studio_id),
    CONSTRAINT UQ_Promo_Code UNIQUE (studio_id, code),
    CONSTRAINT CK_Promo_type   CHECK (discount_type IN ('PERCENT', 'FIXED')),
    CONSTRAINT CK_Promo_value  CHECK (discount_value > 0 AND (discount_type <> 'PERCENT' OR discount_value <= 100)),
    CONSTRAINT CK_Promo_maxdis CHECK (max_discount IS NULL OR max_discount > 0),
    CONSTRAINT CK_Promo_min    CHECK (min_order_amount >= 0),
    CONSTRAINT CK_Promo_dates  CHECK (end_date >= start_date),
    CONSTRAINT CK_Promo_uses   CHECK (max_uses IS NULL OR max_uses > 0),
    CONSTRAINT CK_Promo_status CHECK (status IN ('ACTIVE', 'INACTIVE'))
);
GO

-- Quy tắc giá theo khung giờ / loại ngày (giờ cao điểm, cuối tuần, giờ thấp điểm...)
-- room_id NULL = áp dụng cho mọi phòng của studio; quy tắc riêng của phòng được ưu tiên hơn.
IF OBJECT_ID(N'dbo.PricingRules', N'U') IS NULL
CREATE TABLE dbo.PricingRules (
    rule_id    INT IDENTITY(1,1) NOT NULL,
    studio_id  INT           NOT NULL,
    room_id    INT           NULL,
    name       NVARCHAR(100) NOT NULL,
    day_type   VARCHAR(10)   NOT NULL CONSTRAINT DF_PRule_day DEFAULT 'ALL',   -- ALL / WEEKDAY / WEEKEND
    start_hour TINYINT       NOT NULL,                                          -- giờ bắt đầu (0-23)
    end_hour   TINYINT       NOT NULL,                                          -- giờ kết thúc (1-24, không tính)
    multiplier DECIMAL(4,2)  NOT NULL,                                          -- 1.20 = tăng 20%, 0.90 = giảm 10%
    status     VARCHAR(10)   NOT NULL CONSTRAINT DF_PRule_status DEFAULT 'ACTIVE',
    created_at DATETIME      NOT NULL CONSTRAINT DF_PRule_created DEFAULT GETDATE(),
    CONSTRAINT PK_PricingRules PRIMARY KEY (rule_id),
    CONSTRAINT FK_PRule_Studio FOREIGN KEY (studio_id) REFERENCES dbo.Studios(studio_id),
    CONSTRAINT FK_PRule_Room   FOREIGN KEY (room_id)   REFERENCES dbo.Rooms(room_id),
    CONSTRAINT CK_PRule_day    CHECK (day_type IN ('ALL', 'WEEKDAY', 'WEEKEND')),
    CONSTRAINT CK_PRule_hours  CHECK (start_hour BETWEEN 0 AND 23 AND end_hour BETWEEN 1 AND 24 AND end_hour > start_hour),
    CONSTRAINT CK_PRule_mult   CHECK (multiplier BETWEEN 0.50 AND 3.00),
    CONSTRAINT CK_PRule_status CHECK (status IN ('ACTIVE', 'INACTIVE'))
);
GO

-- Mỗi đơn áp tối đa 1 mã khuyến mãi
IF OBJECT_ID(N'dbo.ReservationPromotions', N'U') IS NULL
CREATE TABLE dbo.ReservationPromotions (
    reservation_id  INT           NOT NULL,
    promo_id        INT           NOT NULL,
    discount_amount DECIMAL(18,2) NOT NULL CONSTRAINT DF_ResPromo_amt DEFAULT 0,
    applied_at      DATETIME      NOT NULL CONSTRAINT DF_ResPromo_at DEFAULT GETDATE(),
    CONSTRAINT PK_ReservationPromotions PRIMARY KEY (reservation_id),
    CONSTRAINT FK_ResPromo_Reservation FOREIGN KEY (reservation_id)
        REFERENCES dbo.Reservations(reservation_id) ON DELETE CASCADE,
    CONSTRAINT FK_ResPromo_Promo FOREIGN KEY (promo_id) REFERENCES dbo.Promotions(promo_id)
);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_Promo_Studio' AND object_id = OBJECT_ID(N'dbo.Promotions'))
    CREATE INDEX IX_Promo_Studio ON dbo.Promotions(studio_id, status, start_date, end_date);
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_PRule_Studio' AND object_id = OBJECT_ID(N'dbo.PricingRules'))
    CREATE INDEX IX_PRule_Studio ON dbo.PricingRules(studio_id, status) INCLUDE (room_id, day_type, start_hour, end_hour, multiplier);
GO

/* ---------------------------------------------------------------
   2. HÀM TÍNH TIỀN PHÒNG THEO QUY TẮC GIÁ
   Chia khoảng thuê thành các lát 30 phút, mỗi lát nhân hệ số của quy tắc khớp
   (quy tắc riêng của phòng thắng quy tắc chung của studio; cùng cấp lấy hệ số cao nhất).
   Không có quy tắc nào khớp thì hệ số = 1 (bằng giá phẳng giờ x đơn giá).
   Thứ trong tuần tính bằng DATEDIFF(DAY, 0, ngày) % 7: 0 = Thứ Hai ... 5, 6 = cuối tuần
   (không phụ thuộc cấu hình SET DATEFIRST).
   --------------------------------------------------------------- */
CREATE OR ALTER FUNCTION dbo.fn_RoomAmount (@room_id INT, @start DATETIME, @end DATETIME)
RETURNS DECIMAL(18,2)
AS
BEGIN
    DECLARE @price DECIMAL(18,2), @studio INT;
    SELECT @price = price_per_hour, @studio = studio_id FROM dbo.Rooms WHERE room_id = @room_id;
    IF @price IS NULL RETURN NULL;

    DECLARE @total DECIMAL(18,4) = 0, @t DATETIME = @start, @next DATETIME,
            @mult DECIMAL(4,2), @mins INT, @weekend BIT, @hour INT;

    WHILE @t < @end
    BEGIN
        SET @next = DATEADD(MINUTE, 30 - (DATEPART(MINUTE, @t) % 30), @t);   -- ranh giới :00 / :30 kế tiếp
        IF @next > @end SET @next = @end;
        SET @mins    = DATEDIFF(MINUTE, @t, @next);
        SET @weekend = CASE WHEN DATEDIFF(DAY, 0, @t) % 7 >= 5 THEN 1 ELSE 0 END;
        SET @hour    = DATEPART(HOUR, @t);

        SET @mult = NULL;
        SELECT @mult = MAX(multiplier) FROM dbo.PricingRules
        WHERE status = 'ACTIVE' AND room_id = @room_id
          AND (day_type = 'ALL' OR (day_type = 'WEEKEND' AND @weekend = 1) OR (day_type = 'WEEKDAY' AND @weekend = 0))
          AND @hour >= start_hour AND @hour < end_hour;

        IF @mult IS NULL
            SELECT @mult = MAX(multiplier) FROM dbo.PricingRules
            WHERE status = 'ACTIVE' AND studio_id = @studio AND room_id IS NULL
              AND (day_type = 'ALL' OR (day_type = 'WEEKEND' AND @weekend = 1) OR (day_type = 'WEEKDAY' AND @weekend = 0))
              AND @hour >= start_hour AND @hour < end_hour;

        SET @total = @total + (@mins / 60.0) * @price * ISNULL(@mult, 1.0);
        SET @t = @next;
    END;

    RETURN CAST(@total AS DECIMAL(18,2));
END;
GO

/* ---------------------------------------------------------------
   3. TÍNH LẠI TỔNG TIỀN ĐƠN (thay bản ở 03):
      tổng = tiền phòng theo quy tắc giá + thiết bị thuê thêm + gói - khuyến mãi
   --------------------------------------------------------------- */
CREATE OR ALTER PROCEDURE dbo.sp_RecalculateReservationTotal
    @reservation_id INT
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @room_amount DECIMAL(18,2), @eq_amount DECIMAL(18,2), @pkg_amount DECIMAL(18,2),
            @subtotal DECIMAL(18,2), @discount DECIMAL(18,2);

    SELECT @room_amount = dbo.fn_RoomAmount(r.room_id, r.start_time, r.end_time)
    FROM dbo.Reservations r
    WHERE r.reservation_id = @reservation_id;

    IF @room_amount IS NULL THROW 50001, N'Không tìm thấy đơn đặt phòng.', 1;

    SELECT @eq_amount  = ISNULL(SUM(quantity * unit_price), 0) FROM dbo.ReservationEquipments WHERE reservation_id = @reservation_id;
    SELECT @pkg_amount = ISNULL(SUM(price), 0)                  FROM dbo.ReservationPackages   WHERE reservation_id = @reservation_id;
    SET @subtotal = @room_amount + @eq_amount + @pkg_amount;

    SELECT @discount = CASE WHEN p.discount_type = 'PERCENT'
                            THEN CASE WHEN p.max_discount IS NOT NULL AND @subtotal * p.discount_value / 100.0 > p.max_discount
                                      THEN p.max_discount
                                      ELSE @subtotal * p.discount_value / 100.0 END
                            ELSE p.discount_value END
    FROM dbo.ReservationPromotions rp
    JOIN dbo.Promotions p ON p.promo_id = rp.promo_id
    WHERE rp.reservation_id = @reservation_id;

    SET @discount = ISNULL(@discount, 0);
    IF @discount > @subtotal SET @discount = @subtotal;
    SET @discount = CAST(@discount AS DECIMAL(18,2));

    UPDATE dbo.ReservationPromotions SET discount_amount = @discount WHERE reservation_id = @reservation_id;
    UPDATE dbo.Reservations SET total_amount = @subtotal - @discount WHERE reservation_id = @reservation_id;
END;
GO

/* ---------------------------------------------------------------
   4. ÁP MÃ KHUYẾN MÃI VÀO ĐƠN
   Khóa dòng mã (UPDLOCK, HOLDLOCK) để 2 người dùng mã cuối cùng cùng lúc
   thì chỉ một người thành công.
   --------------------------------------------------------------- */
CREATE OR ALTER PROCEDURE dbo.sp_ApplyPromotion
    @reservation_id INT,
    @code           VARCHAR(30),
    @actor_id       INT
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        IF dbo.fn_CanManageReservation(@reservation_id, @actor_id) = 0
                           THROW 51001, N'Bạn không có quyền thao tác đơn này.', 1;

        BEGIN TRANSACTION;

        DECLARE @status VARCHAR(20), @studio INT;
        SELECT @status = r.status, @studio = rm.studio_id
        FROM dbo.Reservations r WITH (UPDLOCK)
        JOIN dbo.Rooms rm ON rm.room_id = r.room_id
        WHERE r.reservation_id = @reservation_id;

        IF @status IS NULL THROW 51002, N'Không tìm thấy đơn đặt phòng.', 1;
        IF @status NOT IN ('PENDING', 'CONFIRMED')
                           THROW 51003, N'Chỉ áp mã khuyến mãi khi đơn đang PENDING hoặc CONFIRMED.', 1;
        IF EXISTS (SELECT 1 FROM dbo.ReservationPromotions WHERE reservation_id = @reservation_id)
                           THROW 51004, N'Đơn này đã áp một mã khuyến mãi rồi.', 1;

        DECLARE @promo INT, @pstatus VARCHAR(10), @sd DATE, @ed DATE, @max INT, @used INT, @min DECIMAL(18,2);
        SELECT @promo = promo_id, @pstatus = status, @sd = start_date, @ed = end_date,
               @max = max_uses, @used = used_count, @min = min_order_amount
        FROM dbo.Promotions WITH (UPDLOCK, HOLDLOCK)
        WHERE studio_id = @studio AND code = @code;

        IF @promo IS NULL  THROW 51005, N'Không tìm thấy mã khuyến mãi ở studio này.', 1;
        IF @pstatus <> 'ACTIVE'
                           THROW 51006, N'Mã khuyến mãi đang tạm ngưng.', 1;
        IF CAST(GETDATE() AS DATE) < @sd OR CAST(GETDATE() AS DATE) > @ed
                           THROW 51007, N'Mã khuyến mãi chưa đến hạn hoặc đã hết hạn.', 1;
        IF @max IS NOT NULL AND @used >= @max
                           THROW 51008, N'Mã khuyến mãi đã hết lượt sử dụng.', 1;

        EXEC dbo.sp_RecalculateReservationTotal @reservation_id;     -- tổng chưa giảm
        DECLARE @subtotal DECIMAL(18,2) = (SELECT total_amount FROM dbo.Reservations WHERE reservation_id = @reservation_id);
        IF @subtotal < @min
                           THROW 51009, N'Đơn chưa đạt giá trị tối thiểu để dùng mã này.', 1;

        INSERT INTO dbo.ReservationPromotions (reservation_id, promo_id) VALUES (@reservation_id, @promo);
        UPDATE dbo.Promotions SET used_count = used_count + 1 WHERE promo_id = @promo;
        EXEC dbo.sp_RecalculateReservationTotal @reservation_id;     -- tổng đã giảm

        COMMIT TRANSACTION;

        SELECT r.reservation_id, r.total_amount, rp.discount_amount, @code AS promo_code
        FROM dbo.Reservations r
        JOIN dbo.ReservationPromotions rp ON rp.reservation_id = r.reservation_id
        WHERE r.reservation_id = @reservation_id;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;
GO

/* ---------------------------------------------------------------
   5. BÁO GIÁ (chưa tạo đơn): giá phẳng, giá theo quy tắc, giảm giá, thành tiền
   --------------------------------------------------------------- */
CREATE OR ALTER PROCEDURE dbo.sp_QuotePrice
    @room_id    INT,
    @start_time DATETIME,
    @end_time   DATETIME,
    @promo_code VARCHAR(30) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    IF @start_time >= @end_time THROW 51101, N'Giờ bắt đầu phải nhỏ hơn giờ kết thúc.', 1;

    DECLARE @studio INT, @base DECIMAL(18,2), @rules DECIMAL(18,2),
            @discount DECIMAL(18,2) = NULL, @msg NVARCHAR(200) = NULL;

    SELECT @studio = rm.studio_id,
           @base = CAST(DATEDIFF(MINUTE, @start_time, @end_time) / 60.0 * rm.price_per_hour AS DECIMAL(18,2))
    FROM dbo.Rooms rm WHERE rm.room_id = @room_id;

    IF @studio IS NULL THROW 51102, N'Không tìm thấy phòng.', 1;
    SET @rules = dbo.fn_RoomAmount(@room_id, @start_time, @end_time);

    IF @promo_code IS NOT NULL
    BEGIN
        SELECT @discount = CASE WHEN p.discount_type = 'PERCENT'
                                THEN CASE WHEN p.max_discount IS NOT NULL AND @rules * p.discount_value / 100.0 > p.max_discount
                                          THEN p.max_discount ELSE @rules * p.discount_value / 100.0 END
                                ELSE p.discount_value END
        FROM dbo.Promotions p
        WHERE p.studio_id = @studio AND p.code = @promo_code AND p.status = 'ACTIVE'
          AND CAST(GETDATE() AS DATE) BETWEEN p.start_date AND p.end_date
          AND (p.max_uses IS NULL OR p.used_count < p.max_uses)
          AND @rules >= p.min_order_amount;

        IF @discount IS NULL
        BEGIN
            SET @msg = N'Mã không hợp lệ hoặc chưa đủ điều kiện áp dụng.';
        END
        ELSE IF @discount > @rules
        BEGIN
            SET @discount = @rules;
        END
    END;

    SELECT @base AS base_amount,
           @rules AS room_amount,
           @rules - @base AS price_rule_adjustment,
           CAST(ISNULL(@discount, 0) AS DECIMAL(18,2)) AS discount_amount,
           @rules - CAST(ISNULL(@discount, 0) AS DECIMAL(18,2)) AS final_amount,
           @msg AS promo_message;
END;
GO

/* ---------------------------------------------------------------
   6. AI (không dùng dịch vụ ngoài): GỢI Ý PHÒNG
   Điểm = 0.35 x điểm đánh giá + 0.25 x độ phổ biến 90 ngày + 0.20 x mức khách hay thuê loại phòng này
          + 0.10 x mức khách hay thuê ở thành phố này + 0.10 x độ gần mức giá khách thường trả.
   Khách mới (chưa có lịch sử) chỉ dựa vào đánh giá và độ phổ biến.
   --------------------------------------------------------------- */
CREATE OR ALTER PROCEDURE dbo.sp_RecommendRooms
    @customer_id INT = NULL,
    @top         INT = 5
AS
BEGIN
    SET NOCOUNT ON;
    IF @top < 1 OR @top > 50 SET @top = 5;

    DECLARE @avg_price DECIMAL(18,2) =
        (SELECT AVG(rm.price_per_hour)
         FROM dbo.Reservations r JOIN dbo.Rooms rm ON rm.room_id = r.room_id
         WHERE r.customer_id = @customer_id AND r.status <> 'CANCELLED');

    ;WITH pop AS (
        SELECT r.room_id, COUNT(*) AS n
        FROM dbo.Reservations r
        WHERE r.status <> 'CANCELLED' AND r.start_time >= DATEADD(DAY, -90, GETDATE())
        GROUP BY r.room_id
    ), maxpop AS (
        SELECT ISNULL(MAX(n), 1) AS m FROM pop
    ), mytype AS (
        SELECT rm.room_type, COUNT(*) * 1.0 / SUM(COUNT(*)) OVER () AS share
        FROM dbo.Reservations r JOIN dbo.Rooms rm ON rm.room_id = r.room_id
        WHERE r.customer_id = @customer_id AND r.status <> 'CANCELLED'
        GROUP BY rm.room_type
    ), mycity AS (
        SELECT s.city, COUNT(*) * 1.0 / SUM(COUNT(*)) OVER () AS share
        FROM dbo.Reservations r
        JOIN dbo.Rooms rm ON rm.room_id = r.room_id
        JOIN dbo.Studios s ON s.studio_id = rm.studio_id
        WHERE r.customer_id = @customer_id AND r.status <> 'CANCELLED'
        GROUP BY s.city
    )
    SELECT TOP (@top)
           rm.room_id, rm.name AS room_name, rm.room_type, rm.capacity, rm.price_per_hour,
           s.studio_id, s.name AS studio_name, s.city,
           ISNULL(sr.avg_rating, 0)   AS avg_rating,
           ISNULL(sr.review_count, 0) AS review_count,
           ISNULL(pop.n, 0)           AS recent_bookings,
           CAST(ISNULL(mt.share, 0) AS DECIMAL(5,2)) AS type_preference,
           CAST(ISNULL(mc.share, 0) AS DECIMAL(5,2)) AS city_preference,
           CAST(
               0.35 * (ISNULL(sr.avg_rating, 0) / 5.0)
             + 0.25 * (ISNULL(pop.n, 0) * 1.0 / mp.m)
             + 0.20 * ISNULL(mt.share, 0)
             + 0.10 * ISNULL(mc.share, 0)
             + 0.10 * (CASE WHEN @avg_price IS NULL OR @avg_price = 0 THEN 0.5
                            ELSE 1.0 - (CASE WHEN ABS(rm.price_per_hour - @avg_price) / @avg_price > 1
                                             THEN 1.0 ELSE ABS(rm.price_per_hour - @avg_price) / @avg_price END)
                       END)
           AS DECIMAL(6,4)) AS score
    FROM dbo.Rooms rm
    JOIN dbo.Studios s ON s.studio_id = rm.studio_id
    LEFT JOIN dbo.vw_StudioRating sr ON sr.studio_id = s.studio_id
    LEFT JOIN pop ON pop.room_id = rm.room_id
    CROSS JOIN maxpop mp
    LEFT JOIN mytype mt ON mt.room_type = rm.room_type
    LEFT JOIN mycity mc ON mc.city = s.city
    WHERE rm.status = 'AVAILABLE' AND s.status = 'APPROVED'
    ORDER BY score DESC, rm.room_id;
END;
GO

/* ---------------------------------------------------------------
   7. AI: DỰ BÁO NHU CẦU ĐẶT PHÒNG (mô hình nền theo thứ trong tuần)
   Số đơn dự kiến của một ngày tương lai = số đơn trung bình của cùng thứ trong
   @lookback_days ngày gần nhất (đơn CONFIRMED / IN_USE / COMPLETED).
   Kèm số đơn đã đặt trước (PENDING / CONFIRMED) cho ngày đó để so sánh.
   --------------------------------------------------------------- */
CREATE OR ALTER PROCEDURE dbo.sp_ForecastDemand
    @studio_id     INT,
    @horizon_days  INT = 7,
    @lookback_days INT = 84
AS
BEGIN
    SET NOCOUNT ON;
    IF @horizon_days < 1 OR @horizon_days > 30 THROW 51201, N'Số ngày dự báo phải từ 1 đến 30.', 1;
    IF @lookback_days < 14 OR @lookback_days > 365 THROW 51202, N'Số ngày lịch sử phải từ 14 đến 365.', 1;
    IF NOT EXISTS (SELECT 1 FROM dbo.Studios WHERE studio_id = @studio_id) THROW 51203, N'Không tìm thấy studio.', 1;

    DECLARE @today DATE = CAST(GETDATE() AS DATE);
    DECLARE @from  DATE = DATEADD(DAY, -@lookback_days, @today);

    ;WITH n AS (
        SELECT TOP (@lookback_days) CAST(ROW_NUMBER() OVER (ORDER BY (SELECT NULL)) - 1 AS INT) AS i
        FROM sys.all_objects a CROSS JOIN sys.all_objects b
    ), wk AS (
        SELECT DATEDIFF(DAY, 0, DATEADD(DAY, i, @from)) % 7 AS wd, COUNT(*) AS days_count
        FROM n
        GROUP BY DATEDIFF(DAY, 0, DATEADD(DAY, i, @from)) % 7
    ), b AS (
        SELECT DATEDIFF(DAY, 0, r.start_time) % 7 AS wd,
               COUNT(*) AS bookings,
               SUM(DATEDIFF(MINUTE, r.start_time, r.end_time)) / 60.0 AS hours
        FROM dbo.Reservations r
        JOIN dbo.Rooms rm ON rm.room_id = r.room_id
        WHERE rm.studio_id = @studio_id
          AND r.status IN ('CONFIRMED', 'IN_USE', 'COMPLETED')
          AND CAST(r.start_time AS DATE) >= @from AND CAST(r.start_time AS DATE) < @today
        GROUP BY DATEDIFF(DAY, 0, r.start_time) % 7
    ), fut AS (
        SELECT TOP (@horizon_days) DATEADD(DAY, CAST(ROW_NUMBER() OVER (ORDER BY (SELECT NULL)) AS INT), @today) AS d
        FROM sys.all_objects
    )
    SELECT f.d AS forecast_date,
           DATEDIFF(DAY, 0, f.d) % 7 AS weekday_index,
           CAST(ISNULL(b.bookings, 0) * 1.0 / NULLIF(wk.days_count, 0) AS DECIMAL(8,2)) AS expected_bookings,
           CAST(ISNULL(b.hours, 0) / NULLIF(wk.days_count, 0) AS DECIMAL(8,2))           AS expected_hours,
           ISNULL(wk.days_count, 0) AS sample_days,
           (SELECT COUNT(*) FROM dbo.Reservations r2
              JOIN dbo.Rooms rm2 ON rm2.room_id = r2.room_id
             WHERE rm2.studio_id = @studio_id AND CAST(r2.start_time AS DATE) = f.d
               AND r2.status IN ('PENDING', 'CONFIRMED')) AS already_booked
    FROM fut f
    LEFT JOIN wk ON wk.wd = DATEDIFF(DAY, 0, f.d) % 7
    LEFT JOIN b  ON b.wd  = DATEDIFF(DAY, 0, f.d) % 7
    ORDER BY f.d;
END;
GO

/* ---------------------------------------------------------------
   8. DỮ LIỆU MẪU (chỉ chèn nếu chưa có): để demo ngay sau khi chạy file này
   --------------------------------------------------------------- */
DECLARE @sg INT = (SELECT TOP (1) studio_id FROM dbo.Studios WHERE name = N'Silver Grain Studio');
IF @sg IS NOT NULL
BEGIN
    IF NOT EXISTS (SELECT 1 FROM dbo.PricingRules WHERE studio_id = @sg AND name = N'Cuối tuần')
        INSERT INTO dbo.PricingRules (studio_id, room_id, name, day_type, start_hour, end_hour, multiplier)
        VALUES (@sg, NULL, N'Cuối tuần', 'WEEKEND', 8, 21, 1.15);
    IF NOT EXISTS (SELECT 1 FROM dbo.PricingRules WHERE studio_id = @sg AND name = N'Giờ vàng buổi tối')
        INSERT INTO dbo.PricingRules (studio_id, room_id, name, day_type, start_hour, end_hour, multiplier)
        VALUES (@sg, NULL, N'Giờ vàng buổi tối', 'ALL', 17, 21, 1.10);
    IF NOT EXISTS (SELECT 1 FROM dbo.PricingRules WHERE studio_id = @sg AND name = N'Giờ thấp điểm sáng ngày thường')
        INSERT INTO dbo.PricingRules (studio_id, room_id, name, day_type, start_hour, end_hour, multiplier)
        VALUES (@sg, NULL, N'Giờ thấp điểm sáng ngày thường', 'WEEKDAY', 8, 11, 0.90);

    IF NOT EXISTS (SELECT 1 FROM dbo.Promotions WHERE studio_id = @sg AND code = 'WELCOME10')
        INSERT INTO dbo.Promotions (studio_id, code, title, discount_type, discount_value, max_discount, min_order_amount, start_date, end_date, max_uses)
        VALUES (@sg, 'WELCOME10', N'Giảm 10% cho khách mới', 'PERCENT', 10, 100000, 200000,
                DATEADD(DAY, -30, CAST(GETDATE() AS DATE)), DATEADD(DAY, 365, CAST(GETDATE() AS DATE)), 100);
    IF NOT EXISTS (SELECT 1 FROM dbo.Promotions WHERE studio_id = @sg AND code = 'GIAM50K')
        INSERT INTO dbo.Promotions (studio_id, code, title, discount_type, discount_value, max_discount, min_order_amount, start_date, end_date, max_uses)
        VALUES (@sg, 'GIAM50K', N'Giảm 50.000đ cho đơn từ 400.000đ', 'FIXED', 50000, NULL, 400000,
                DATEADD(DAY, -7, CAST(GETDATE() AS DATE)), DATEADD(DAY, 90, CAST(GETDATE() AS DATE)), NULL);
END;
GO

PRINT N'=== 07: đã tạo 3 bảng, 1 hàm, 5 procedure (1 procedure được thay thế) ===';
GO
