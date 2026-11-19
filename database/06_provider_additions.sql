/* =====================================================================
   06_provider_additions.sql  -  bổ sung cho giao diện Provider
   Chạy SAU 01..03 (an toàn khi chạy lại nhiều lần).
   - Thêm cột Reservations.cancel_reason: lý do chủ studio hủy đơn (khách thấy).
   Nếu chưa chạy file này, backend vẫn chạy bình thường nhưng không lưu được lý do hủy.
   ===================================================================== */
IF COL_LENGTH(N'dbo.Reservations', N'cancel_reason') IS NULL
    ALTER TABLE dbo.Reservations ADD cancel_reason NVARCHAR(500) NULL;
GO
