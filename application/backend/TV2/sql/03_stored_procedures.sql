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

        -- Bước 4: Thêm mới đơn đặt phòng
        INSERT INTO dbo.Reservations (
            room_id, customer_id, start_time, end_time, 
            total_amount, customer_note, status, created_at
        )
        VALUES (
            @room_id, @customer_id, @start_time, @end_time, 
            @total_amount, @customer_note, 'PENDING', GETDATE()
        );

        COMMIT TRANSACTION;
        PRINT N'Thành công: Đặt phòng đã được tạo ở trạng thái PENDING.';
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        
        DECLARE @ErrorMessage NVARCHAR(4000) = ERROR_MESSAGE();
        RAISERROR(@ErrorMessage, 16, 1);
    END CATCH
END;
GO

-- 2. STORED PROCEDURE: sp_RegisterWorkshop (Đăng ký Workshop thông minh)
-- Kiểm tra sức chứa (capacity) và chống đăng ký trùng lặp
CREATE OR ALTER PROCEDURE sp_RegisterWorkshop
    @workshop_id INT,
    @customer_id INT
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRANSACTION;

    BEGIN TRY
        -- Bước 1: Kiểm tra Workshop có tồn tại không
        DECLARE @capacity INT;
        SELECT @capacity = capacity FROM dbo.Workshops WHERE workshop_id = @workshop_id;

        IF @capacity IS NULL
        BEGIN
            RAISERROR(N'Lỗi: Workshop không tồn tại trên hệ thống.', 16, 1);
            ROLLBACK TRANSACTION;
            RETURN;
        END

        -- Bước 2: Kiểm tra khách hàng đã đăng ký workshop này trước đó chưa
        IF EXISTS (
            SELECT 1 FROM dbo.WorkshopRegistrations 
            WHERE workshop_id = @workshop_id AND customer_id = @customer_id
        )
        BEGIN
            RAISERROR(N'Lỗi: Bạn đã đăng ký tham gia workshop này từ trước rồi.', 16, 1);
            ROLLBACK TRANSACTION;
            RETURN;
        END

        -- Bước 3: Kiểm tra số lượng chỗ ngồi hiện tại có vượt capacity không
        DECLARE @current_registrations INT;
        SELECT @current_registrations = COUNT(*) 
        FROM dbo.WorkshopRegistrations WITH (UPDLOCK)
        WHERE workshop_id = @workshop_id;

        IF @current_registrations >= @capacity
        BEGIN
            RAISERROR(N'Lỗi: Workshop đã đủ số lượng người tham gia tối đa (Hết chỗ).', 16, 1);
            ROLLBACK TRANSACTION;
            RETURN;
        END

        -- Bước 4: Thực hiện ghi danh
        INSERT INTO dbo.WorkshopRegistrations (workshop_id, customer_id, registered_at)
        VALUES (@workshop_id, @customer_id, GETDATE());

        COMMIT TRANSACTION;
        PRINT N'Thành công: Đăng ký tham gia Workshop hoàn tất!';
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        
        DECLARE @ErrMsg NVARCHAR(4000) = ERROR_MESSAGE();
        RAISERROR(@ErrMsg, 16, 1);
    END CATCH
END;
GO


