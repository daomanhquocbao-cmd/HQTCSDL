USE FilmPhotographyPlatform;
GO

-- sp_UpdateReservationStatus: đổi trạng thái đơn đặt phòng và ghi lịch sử
-- (bảng ReservationStatusHistory). Dùng cho chức năng hủy / xác nhận / hoàn thành.
CREATE OR ALTER PROCEDURE sp_UpdateReservationStatus
    @reservation_id INT,
    @new_status VARCHAR(20),
    @changed_by INT
AS
BEGIN
    SET NOCOUNT ON;

    BEGIN TRY
        BEGIN TRANSACTION;

        IF @new_status NOT IN ('PENDING', 'CONFIRMED', 'CANCELLED', 'COMPLETED')
            RAISERROR(N'Lỗi: Trạng thái mới không hợp lệ.', 16, 1);

        DECLARE @old_status VARCHAR(20);
        SELECT @old_status = status
        FROM dbo.Reservations WITH (UPDLOCK, HOLDLOCK)
        WHERE reservation_id = @reservation_id;

        IF @old_status IS NULL
            RAISERROR(N'Lỗi: Không tìm thấy đơn đặt phòng.', 16, 1);

        IF @old_status = @new_status
            RAISERROR(N'Lỗi: Đơn đã ở trạng thái này rồi.', 16, 1);

        IF @old_status IN ('CANCELLED', 'COMPLETED')
            RAISERROR(N'Lỗi: Đơn đã kết thúc, không thể đổi trạng thái.', 16, 1);

        UPDATE dbo.Reservations
        SET status = @new_status
        WHERE reservation_id = @reservation_id;

        INSERT INTO dbo.ReservationStatusHistory (reservation_id, changed_by, old_status, new_status)
        VALUES (@reservation_id, @changed_by, @old_status, @new_status);

        COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        DECLARE @ErrorMessage NVARCHAR(4000) = ERROR_MESSAGE();
        RAISERROR(@ErrorMessage, 16, 1);
    END CATCH
END;
GO
