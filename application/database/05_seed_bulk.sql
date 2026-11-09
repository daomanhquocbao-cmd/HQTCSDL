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

/* ---------------------------------------------------------------
   1. USERS: nhà cung cấp + khách hàng
   --------------------------------------------------------------- */
PRINT N'1. Users...';
INSERT INTO dbo.Users (username, password_hash, email, phone, full_name, role, status)
SELECT 'bprov' + RIGHT('00000' + CAST(i AS VARCHAR(5)), 5), @pwd,
       'bprov' + RIGHT('00000' + CAST(i AS VARCHAR(5)), 5) + '@filmplatform.vn',
       '08' + RIGHT('00000000' + CAST(CAST(i AS BIGINT) * 7919 AS VARCHAR(12)), 8),
       N'Chủ studio số ' + CAST(i AS NVARCHAR(6)), 'PROVIDER', 'ACTIVE'
FROM #n WHERE i <= @PROVIDERS ORDER BY i;

INSERT INTO dbo.Users (username, password_hash, email, phone, full_name, role, status)
SELECT 'bcust' + RIGHT('000000' + CAST(i AS VARCHAR(6)), 6), @pwd,
       'bcust' + RIGHT('000000' + CAST(i AS VARCHAR(6)), 6) + '@gmail.com',
       '09' + RIGHT('00000000' + CAST(CAST(i AS BIGINT) * 7919 AS VARCHAR(12)), 8),
       CHOOSE(i % 8 + 1, N'Nguyễn', N'Trần', N'Lê', N'Phạm', N'Hoàng', N'Võ', N'Đặng', N'Bùi') + N' '
       + CHOOSE((i / 8) % 4 + 1, N'Văn', N'Thị', N'Minh', N'Ngọc') + N' '
       + CHOOSE((i / 32) % 10 + 1, N'An', N'Bình', N'Chi', N'Dũng', N'Hà', N'Khoa', N'Lan', N'Nam', N'Phúc', N'Quang'),
       'CUSTOMER', 'ACTIVE'
FROM #n WHERE i <= @CUSTOMERS ORDER BY i;

/* ---------------------------------------------------------------
   2. STUDIOS, ROOMS
   --------------------------------------------------------------- */
PRINT N'2. Studios, StudioImages, Rooms...';
INSERT INTO dbo.Studios (provider_id, name, address, city, description, phone, status)
SELECT u.user_id,
       N'Studio Analog ' + CAST(n.i AS NVARCHAR(6)),
       N'Số ' + CAST(n.i AS NVARCHAR(6)) + N' Đường số ' + CAST(n.i % 40 + 1 AS NVARCHAR(3)),
       CHOOSE(n.i % 10 + 1, N'TP.HCM', N'Hà Nội', N'Đà Nẵng', N'Cần Thơ', N'Hải Phòng',
                            N'Huế', N'Nha Trang', N'Đà Lạt', N'Biên Hòa', N'Vũng Tàu'),
       N'Studio nhiếp ảnh phim phục vụ cộng đồng địa phương.',
       '028' + RIGHT('0000000' + CAST(n.i AS VARCHAR(7)), 7),
       CASE WHEN n.i % 15 = 0 THEN 'PENDING' ELSE 'APPROVED' END      -- 1/15 studio còn chờ duyệt
FROM #n n
JOIN dbo.Users u ON u.username = 'bprov' + RIGHT('00000' + CAST(n.i AS VARCHAR(5)), 5)
WHERE n.i <= @PROVIDERS
ORDER BY n.i;

INSERT INTO dbo.StudioImages (studio_id, image_url, is_primary)
SELECT s.studio_id,
       N'https://images.filmplatform.vn/studios/' + CAST(s.studio_id AS NVARCHAR(10)) + N'_' + CAST(k.n AS NVARCHAR(2)) + N'.jpg',
       CASE WHEN k.n = 1 THEN 1 ELSE 0 END
FROM dbo.Studios s CROSS JOIN (VALUES (1), (2)) k(n)
WHERE s.studio_id > @maxStudio;

-- Mỗi studio 4 phòng: 3 phòng chụp + 1 phòng tối
INSERT INTO dbo.Rooms (studio_id, name, room_type, capacity, area_sqm, art_style, lighting, amenities, price_per_hour, description)
SELECT s.studio_id, d.name, d.room_type, d.capacity, d.area, d.style, d.lighting, d.amenities,
       d.price + (s.studio_id % 7) * 10000, d.descr
FROM dbo.Studios s
CROSS JOIN (VALUES
    (N'Phòng chụp Vintage',  'STUDIO',   6, 35.0, N'Vintage',      N'Softbox + ánh sáng tự nhiên', N'Phông nền, ghế, bàn trang điểm', 250000, N'Không gian hoài cổ.'),
    (N'Phòng chụp Minimal',  'STUDIO',   4, 25.0, N'Minimal',      N'Đèn LED liên tục',            N'Phông trắng, hộp sáng',          220000, N'Phòng tối giản.'),
    (N'Phòng chụp Cinematic','STUDIO',   8, 45.0, N'Cinematic',    N'Đèn tungsten + gel màu',      N'Phông vải, khói lạnh',           320000, N'Phong cách điện ảnh.'),
    (N'Phòng tối B&W',       'DARKROOM', 3, 15.0, N'Truyền thống', N'Đèn an toàn màu đỏ',          N'Bồn rửa, máy phóng ảnh',         180000, N'Tráng và in ảnh đen trắng.')
) d(name, room_type, capacity, area, style, lighting, amenities, price, descr)
WHERE s.studio_id > @maxStudio;

UPDATE dbo.Rooms SET status = 'MAINTENANCE' WHERE room_id > @maxRoom AND room_id % 23 = 0;
