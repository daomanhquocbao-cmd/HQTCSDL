/* =====================================================================
   09_backup_recovery.sql  -  Sao lưu tự động và khôi phục sau sự cố
   ---------------------------------------------------------------------
   Đáp ứng yêu cầu phi chức năng: "automatic backup, and disaster recovery".
   - Chuyển CSDL sang mô hình FULL để sao lưu được log giao dịch (khôi phục tới 1 thời điểm).
   - sp_BackupDatabase: sao lưu FULL (toàn bộ) / DIFF (phần thay đổi từ lần FULL gần nhất) / LOG (nhật ký).
   - Cách chạy tự động: SQL Server Agent (bản Standard trở lên) hoặc Windows Task Scheduler + sqlcmd (bản Express,
     vì Express không có SQL Agent) - xem phần cuối file.
   - Quy trình khôi phục mẫu: phần 3 (đã để trong chú thích, chỉ chạy khi thật sự cần).
   Chạy SAU 01..08. Có thể chạy lại nhiều lần.
   LƯU Ý: thư mục sao lưu (mặc định C:\SQLBackups) phải tồn tại và tài khoản chạy SQL Server phải có quyền ghi.
   ===================================================================== */
USE FilmPhotographyPlatform;
GO

/* ---------- 1. Mô hình khôi phục FULL ---------- */
IF (SELECT recovery_model_desc FROM sys.databases WHERE name = DB_NAME()) <> 'FULL'
    ALTER DATABASE FilmPhotographyPlatform SET RECOVERY FULL;
GO

/* ---------- 2. Thủ tục sao lưu ---------- */
CREATE OR ALTER PROCEDURE dbo.sp_BackupDatabase
    @kind VARCHAR(4)       = 'FULL',               -- FULL | DIFF | LOG
    @dir  NVARCHAR(260)    = N'C:\SQLBackups\'
AS
BEGIN
    SET NOCOUNT ON;
    IF @kind NOT IN ('FULL', 'DIFF', 'LOG')
        THROW 53001, N'@kind phải là FULL, DIFF hoặc LOG.', 1;
    IF RIGHT(@dir, 1) NOT IN ('\', '/') SET @dir = @dir + N'\';

    DECLARE @stamp VARCHAR(20) =
        REPLACE(REPLACE(REPLACE(CONVERT(VARCHAR(19), GETDATE(), 120), '-', ''), ':', ''), ' ', '_');
    DECLARE @file NVARCHAR(400) = @dir + N'FilmPhotographyPlatform_' + @kind + N'_' + @stamp
                                  + CASE WHEN @kind = 'LOG' THEN N'.trn' ELSE N'.bak' END;
    DECLARE @sql NVARCHAR(MAX);

    IF @kind = 'FULL'
        SET @sql = N'BACKUP DATABASE FilmPhotographyPlatform TO DISK = @f WITH INIT, CHECKSUM, STATS = 10, '
                 + N'NAME = N''FilmPhotographyPlatform full backup'';';
    ELSE IF @kind = 'DIFF'
        SET @sql = N'BACKUP DATABASE FilmPhotographyPlatform TO DISK = @f WITH DIFFERENTIAL, INIT, CHECKSUM, STATS = 10;';
    ELSE
        SET @sql = N'BACKUP LOG FilmPhotographyPlatform TO DISK = @f WITH INIT, CHECKSUM, STATS = 10;';

    EXEC sp_executesql @sql, N'@f NVARCHAR(400)', @f = @file;

    -- kiểm tra file vừa tạo đọc được và không hỏng (CHECKSUM)
    RESTORE VERIFYONLY FROM DISK = @file WITH CHECKSUM;
    SELECT @kind AS backup_kind, @file AS backup_file, GETDATE() AS finished_at;
END;
GO

/* Lịch sử sao lưu gần đây (đọc từ msdb) */
CREATE OR ALTER VIEW dbo.vw_BackupHistory
AS
SELECT TOP 100 bs.backup_finish_date, 
       CASE bs.type WHEN 'D' THEN 'FULL' WHEN 'I' THEN 'DIFF' WHEN 'L' THEN 'LOG' ELSE bs.type END AS backup_kind,
       CAST(bs.backup_size / 1048576.0 AS DECIMAL(12,2)) AS size_mb,
       bmf.physical_device_name
FROM msdb.dbo.backupset bs
JOIN msdb.dbo.backupmediafamily bmf ON bmf.media_set_id = bs.media_set_id
WHERE bs.database_name = DB_NAME()
ORDER BY bs.backup_finish_date DESC;
GO

/* ---------- Thử ngay một bản FULL (bỏ chú thích khi đã tạo thư mục C:\SQLBackups) ----------
-- EXEC dbo.sp_BackupDatabase @kind = 'FULL';
-- SELECT * FROM dbo.vw_BackupHistory;
*/

/* ---------- 3. KHÔI PHỤC SAU SỰ CỐ (thay tên file cho đúng, chạy từng bước) ----------
USE master;
-- 3a. Sao lưu phần log cuối cùng còn lại (nếu CSDL hỏng nhưng file log còn):
-- BACKUP LOG FilmPhotographyPlatform TO DISK = N'C:\SQLBackups\tail.trn' WITH NO_TRUNCATE;

-- 3b. Khôi phục bản FULL gần nhất, giữ trạng thái "đang khôi phục" để nối thêm DIFF / LOG:
-- RESTORE DATABASE FilmPhotographyPlatform FROM DISK = N'C:\SQLBackups\FilmPhotographyPlatform_FULL_YYYYMMDD_HHMMSS.bak'
--     WITH NORECOVERY, REPLACE;

-- 3c. Nối bản DIFF gần nhất (nếu có):
-- RESTORE DATABASE FilmPhotographyPlatform FROM DISK = N'C:\SQLBackups\FilmPhotographyPlatform_DIFF_YYYYMMDD_HHMMSS.bak'
--     WITH NORECOVERY;

-- 3d. Nối các bản LOG theo thứ tự thời gian; bản cuối dùng STOPAT để về đúng thời điểm trước sự cố:
-- RESTORE LOG FilmPhotographyPlatform FROM DISK = N'C:\SQLBackups\tail.trn'
--     WITH STOPAT = '2026-11-24 09:30:00', RECOVERY;

-- 3e. Kiểm tra toàn vẹn sau khôi phục:
-- DBCC CHECKDB (FilmPhotographyPlatform) WITH NO_INFOMSGS;
*/

/* ---------- 4. Lên lịch tự động ----------
 A) SQL Server Agent (Standard / Enterprise / Developer):
    - FULL mỗi đêm 02:00, DIFF mỗi 6 giờ, LOG mỗi 15 phút: tạo 3 Job, mỗi Job có 1 bước T-SQL
        EXEC FilmPhotographyPlatform.dbo.sp_BackupDatabase @kind = 'FULL';   -- (DIFF / LOG tương ứng)

 B) SQL Server Express (không có Agent): dùng Windows Task Scheduler chạy lệnh
        sqlcmd -S .\SQLEXPRESS -E -d FilmPhotographyPlatform -Q "EXEC dbo.sp_BackupDatabase @kind='FULL'"
    (Task Scheduler -> Create Basic Task -> Daily 02:00 -> Start a program: sqlcmd, thêm tham số như trên.)
   ----------------------------------------------------------------------- */
PRINT N'09_backup_recovery.sql: xong (CSDL đã ở mô hình FULL, có sp_BackupDatabase và vw_BackupHistory).';
GO
