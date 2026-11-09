USE FilmPhotographyPlatform;
GO
SET NOCOUNT ON;
SET QUOTED_IDENTIFIER ON;
GO

/* ---------------- THAM SỐ QUY MÔ (chỉnh ở đây) ---------------- */
DECLARE @CUSTOMERS INT = 5000;      -- số khách hàng mới (tối đa 999999)
DECLARE @PROVIDERS INT = 60;        -- số nhà cung cấp = số studio mới (tối đa 99999)
DECLARE @RES_COUNT INT = 200000;    -- số đơn đặt phòng
DECLARE @POSTS     INT = 3000;      -- số bài viết cộng đồng
DECLARE @COMMENTS  INT = 20000;     -- số bình luận
DECLARE @WORKSHOPS INT = 200;       -- số workshop

IF EXISTS (SELECT 1 FROM dbo.Users WHERE username = 'bcust000001')
BEGIN
    PRINT N'Đã nạp dữ liệu bulk trước đó, bỏ qua. (Muốn nạp lại: chạy 00_drop_all.sql rồi 01, 02, 03, 05)';
    RETURN;
END

DECLARE @t0 DATETIME2 = SYSDATETIME();
DECLARE @pwd VARCHAR(255) = '$2b$12$BULK.PLACEHOLDER.HASH.REPLACE.IN.BACKEND';
DECLARE @today DATETIME = CAST(CAST(GETDATE() AS DATE) AS DATETIME);

-- Ghi nhớ mốc ID hiện có để chỉ thao tác trên dữ liệu bulk mới
DECLARE @maxStudio INT = ISNULL((SELECT MAX(studio_id)      FROM dbo.Studios), 0);
DECLARE @maxRoom   INT = ISNULL((SELECT MAX(room_id)        FROM dbo.Rooms), 0);
DECLARE @maxRes    INT = ISNULL((SELECT MAX(reservation_id) FROM dbo.Reservations), 0);
DECLARE @maxWs     INT = ISNULL((SELECT MAX(workshop_id)    FROM dbo.Workshops), 0);
DECLARE @maxPost   INT = ISNULL((SELECT MAX(post_id)        FROM dbo.CommunityPosts), 0);
DECLARE @admin     INT = (SELECT user_id FROM dbo.Users WHERE username = 'admin');

-- Bảng số 1..N dùng chung (thay cho vòng lặp WHILE - nhanh hơn rất nhiều)
DECLARE @maxN INT = (SELECT MAX(v) FROM (VALUES (@CUSTOMERS), (@PROVIDERS), (@RES_COUNT),
                                                (@POSTS), (@COMMENTS), (@WORKSHOPS), (500)) x(v));
CREATE TABLE #n (i INT NOT NULL PRIMARY KEY);
INSERT INTO #n (i)
SELECT TOP (@maxN) CAST(ROW_NUMBER() OVER (ORDER BY (SELECT NULL)) AS INT)
FROM sys.all_objects a CROSS JOIN sys.all_objects b;

-- Tạm tắt trigger để nạp nhanh (lịch sử trạng thái sẽ nạp thủ công bên dưới)
IF OBJECT_ID(N'dbo.trg_Reservations_Audit', 'TR') IS NOT NULL DISABLE TRIGGER dbo.trg_Reservations_Audit ON dbo.Reservations;
IF OBJECT_ID(N'dbo.trg_Reviews_Validate',   'TR') IS NOT NULL DISABLE TRIGGER dbo.trg_Reviews_Validate   ON dbo.Reviews;

BEGIN TRY
