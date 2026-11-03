USE FilmPhotographyPlatform;
GO

-- 1. STORED PROCEDURE: sp_CreateReservation (Đặt phòng chống trùng lịch)
-- Sử dụng Transaction kết hợp khóa UPDLOCK, HOLDLOCK để đảm bảo an toàn dữ liệu
CREATE OR ALTER PROCEDURE sp_CreateReservation
    @room_id INT,
    @customer_id INT,
    @start_time DATETIME,
    @end_time DATETIME,
    @customer_note NVARCHAR(MAX)
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRANSACTION;

    BEGIN TRY
        -- Bước 1: Kiểm tra thời gian hợp lệ
        IF @start_time >= @end_time
        BEGIN
            RAISERROR(N'Lỗi: Thời gian bắt đầu phải nhỏ hơn thời gian kết thúc.', 16, 1);
            ROLLBACK TRANSACTION;
            RETURN;
        END

        IF @start_time < GETDATE()
        BEGIN
            RAISERROR(N'Lỗi: Không thể đặt phòng trong quá khứ.', 16, 1);
            ROLLBACK TRANSACTION;
            RETURN;
        END

        -- Bước 2: Kiểm tra trùng lịch phòng (Khóa dòng bằng UPDLOCK, HOLDLOCK để chống tranh chấp)
        IF EXISTS (
            SELECT 1 FROM dbo.Reservations WITH (UPDLOCK, HOLDLOCK)
            WHERE room_id = @room_id
              AND status IN ('PENDING', 'CONFIRMED')
              AND (@start_time < end_time AND @end_time > start_time)
        )
        BEGIN
            RAISERROR(N'Lỗi: Phòng này đã có người đặt trong khung giờ bạn chọn.', 16, 1);
            ROLLBACK TRANSACTION;
            RETURN;
        END

        -- Bước 3: Tính toán tổng tiền dựa trên đơn giá giờ của phòng
        DECLARE @price_per_hour DECIMAL(18,2);
        SELECT @price_per_hour = price_per_hour FROM dbo.Rooms WHERE room_id = @room_id;

        IF @price_per_hour IS NULL
        BEGIN
            RAISERROR(N'Lỗi: Không tìm thấy thông tin phòng.', 16, 1);
            ROLLBACK TRANSACTION;
            RETURN;
        END

        DECLARE @hours DECIMAL(18,2) = DATEDIFF(minute, @start_time, @end_time) / 60.0;
        DECLARE @total_amount DECIMAL(18,2) = @hours * @price_per_hour;

