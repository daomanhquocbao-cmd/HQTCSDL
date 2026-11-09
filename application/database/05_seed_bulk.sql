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

/* ---------------------------------------------------------------
   3. EQUIPMENT, MAINTENANCE, PACKAGES
   --------------------------------------------------------------- */
PRINT N'3. Equipment, EquipmentMaintenance, ServicePackages, PackageEquipment...';
INSERT INTO dbo.Equipment (studio_id, name, equipment_type, category, quantity, rental_price, next_maintenance_date)
SELECT s.studio_id, d.name, d.etype, d.cat, d.qty, d.price,
       CASE WHEN d.etype = 'REUSABLE'
            THEN DATEADD(DAY, 20 + (s.studio_id * 17 + d.slot * 11) % 90, CAST(GETDATE() AS DATE)) END
FROM dbo.Studios s
CROSS JOIN (VALUES
    (1, N'Máy ảnh phim Pentax K1000', 'REUSABLE',   'CAMERA',   8, 120000),
    (2, N'Ống kính 50mm f/1.4',       'REUSABLE',   'LENS',     8,  80000),
    (3, N'Đèn flash Godox',           'REUSABLE',   'LIGHTING', 10, 60000),
    (4, N'Chân máy Manfrotto',        'REUSABLE',   'TRIPOD',   8,  40000),
    (5, N'Máy phóng ảnh (enlarger)',  'REUSABLE',   'ENLARGER', 4, 150000),
    (6, N'Máy scan phim Epson V600',  'REUSABLE',   'SCANNER',  4, 100000),
    (7, N'Hóa chất tráng phim B&W',   'CONSUMABLE', 'CHEMICAL', 500,  50000),
    (8, N'Giấy in ảnh 8x10',          'CONSUMABLE', 'PAPER',    5000,  8000)
) d(slot, name, etype, cat, qty, price)
WHERE s.studio_id > @maxStudio;

UPDATE dbo.Equipment
SET status = 'NEEDS_MAINTENANCE', next_maintenance_date = DATEADD(DAY, -3, CAST(GETDATE() AS DATE))
WHERE studio_id > @maxStudio AND equipment_type = 'REUSABLE' AND equipment_id % 29 = 0;

UPDATE dbo.Equipment SET status = 'BROKEN'
WHERE studio_id > @maxStudio AND equipment_type = 'REUSABLE' AND status = 'GOOD' AND equipment_id % 47 = 0;

INSERT INTO dbo.EquipmentMaintenance (equipment_id, maintenance_date, cost, description, status)
SELECT e.equipment_id, DATEADD(DAY, -k.d, GETDATE()), 100000 + (e.equipment_id % 5) * 50000,
       N'Bảo trì định kỳ, vệ sinh và hiệu chỉnh.', 'DONE'
FROM dbo.Equipment e CROSS JOIN (VALUES (200), (60)) k(d)
WHERE e.studio_id > @maxStudio AND e.equipment_type = 'REUSABLE';

INSERT INTO dbo.EquipmentMaintenance (equipment_id, maintenance_date, cost, description, status)
SELECT equipment_id, DATEADD(DAY, 3, GETDATE()), 300000, N'Thay linh kiện hao mòn, canh chỉnh.', 'SCHEDULED'
FROM dbo.Equipment WHERE studio_id > @maxStudio AND status = 'NEEDS_MAINTENANCE';

INSERT INTO dbo.ServicePackages (studio_id, name, price, duration_hours, room_type, instructor_id, description)
SELECT s.studio_id, d.name, d.price, d.hours, d.room_type,
       (SELECT user_id FROM dbo.Users WHERE username = 'expert' + CAST(s.studio_id % 3 + 1 AS VARCHAR(1))),
       d.descr
FROM dbo.Studios s
CROSS JOIN (VALUES
    (N'Gói Chân dung',           650000, 3.0, 'STUDIO',   N'Chụp chân dung phim kèm máy ảnh, ống kính, đèn.'),
    (N'Gói Sản phẩm',            550000, 2.0, 'STUDIO',   N'Chụp sản phẩm với bộ đèn và chân máy.'),
    (N'Gói Tráng phim & In ảnh', 450000, 3.0, 'DARKROOM', N'Hướng dẫn tráng phim, in ảnh trong phòng tối.')
) d(name, price, hours, room_type, descr)
WHERE s.studio_id > @maxStudio;

INSERT INTO dbo.PackageEquipment (package_id, equipment_id, quantity_included)
SELECT p.package_id, e.equipment_id, m.qty
FROM dbo.ServicePackages p
JOIN (VALUES
    (N'Gói Chân dung', 'CAMERA', 1), (N'Gói Chân dung', 'LENS', 1),
    (N'Gói Chân dung', 'LIGHTING', 2), (N'Gói Chân dung', 'TRIPOD', 1),
    (N'Gói Sản phẩm',  'CAMERA', 1), (N'Gói Sản phẩm',  'LIGHTING', 2), (N'Gói Sản phẩm', 'TRIPOD', 1),
    (N'Gói Tráng phim & In ảnh', 'ENLARGER', 1),
    (N'Gói Tráng phim & In ảnh', 'CHEMICAL', 2),
    (N'Gói Tráng phim & In ảnh', 'PAPER', 10)
) m(pkg, cat, qty) ON m.pkg = p.name
JOIN dbo.Equipment e ON e.studio_id = p.studio_id AND e.category = m.cat
WHERE p.studio_id > @maxStudio;

/* ---------------------------------------------------------------
   4. RESERVATIONS - số lượng lớn, KHÔNG trùng lịch
   Đơn thứ i vào phòng (i mod số phòng), ngày (i div số phòng):
   mỗi phòng chỉ có tối đa 1 đơn / ngày nên không bao giờ chồng giờ.
   Khoảng 85% đơn nằm trong quá khứ, 15% còn lại là tương lai.
   --------------------------------------------------------------- */
PRINT N'4. Reservations (' + CAST(@RES_COUNT AS NVARCHAR(10)) + N' đơn)...';
DECLARE @R INT = (SELECT COUNT(*) FROM dbo.Rooms r JOIN dbo.Studios s ON s.studio_id = r.studio_id
                  WHERE r.room_id > @maxRoom AND r.status = 'AVAILABLE' AND s.status = 'APPROVED');
DECLARE @back INT = (@RES_COUNT / @R + 1) * 85 / 100;

;WITH rm AS (
    SELECT r.room_id, r.price_per_hour,
           CAST(ROW_NUMBER() OVER (ORDER BY r.room_id) - 1 AS INT) AS idx
    FROM dbo.Rooms r JOIN dbo.Studios s ON s.studio_id = r.studio_id
    WHERE r.room_id > @maxRoom AND r.status = 'AVAILABLE' AND s.status = 'APPROVED'
), cu AS (
    SELECT user_id, CAST(ROW_NUMBER() OVER (ORDER BY user_id) - 1 AS INT) AS idx
    FROM dbo.Users WHERE username LIKE 'bcust%'
), x AS (
    SELECT n.i, rm.room_id, rm.price_per_hour, cu.user_id AS customer_id,
           DATEADD(HOUR, 9 + (n.i % 3) * 3, DATEADD(DAY, ((n.i - 1) / @R) - @back, @today)) AS start_time,
           2 + (n.i % 2) AS dur
    FROM #n n
    JOIN rm ON rm.idx = (n.i - 1) % @R
    JOIN cu ON cu.idx = (CAST(n.i AS BIGINT) * 7919) % @CUSTOMERS
    WHERE n.i <= @RES_COUNT
), y AS (
    SELECT x.*, DATEADD(HOUR, x.dur, x.start_time) AS end_time FROM x
)
INSERT INTO dbo.Reservations (room_id, customer_id, start_time, end_time, total_amount, customer_note, status, created_at)
SELECT room_id, customer_id, start_time, end_time,
       CAST(DATEDIFF(MINUTE, start_time, end_time) / 60.0 * price_per_hour AS DECIMAL(18,2)),
       CASE WHEN i % 7 = 0 THEN N'Nhờ chuẩn bị sẵn phông nền và ghế.' END,
       CASE WHEN end_time < GETDATE() THEN (CASE WHEN i % 9 = 4 THEN 'CANCELLED' ELSE 'COMPLETED' END)
            WHEN start_time <= GETDATE()  THEN 'IN_USE'
            WHEN i % 3 = 0                THEN 'PENDING'
            ELSE 'CONFIRMED' END,
       DATEADD(DAY, -3, start_time)
FROM y
ORDER BY i;

UPDATE dbo.Reservations
SET qr_code = 'QR-' + CAST(reservation_id AS VARCHAR(10)) + '-'
              + CAST(ABS(CHECKSUM(reservation_id)) % 1000000 AS VARCHAR(10))
WHERE reservation_id > @maxRes AND status IN ('CONFIRMED', 'IN_USE', 'COMPLETED');

PRINT N'   ... thiết bị thuê thêm, gói dịch vụ, tính lại tổng tiền';
INSERT INTO dbo.ReservationEquipments (reservation_id, equipment_id, quantity, unit_price)
SELECT r.reservation_id, e.equipment_id, 1, e.rental_price
FROM dbo.Reservations r
JOIN dbo.Rooms rm ON rm.room_id = r.room_id
JOIN dbo.Equipment e ON e.studio_id = rm.studio_id AND e.category = 'CAMERA'
WHERE r.reservation_id > @maxRes AND (r.reservation_id - @maxRes) % 4 = 0;

INSERT INTO dbo.ReservationPackages (reservation_id, package_id, price)
SELECT r.reservation_id, p.package_id, p.price
FROM dbo.Reservations r
JOIN dbo.Rooms rm ON rm.room_id = r.room_id
JOIN dbo.ServicePackages p ON p.studio_id = rm.studio_id AND p.room_type = rm.room_type
WHERE r.reservation_id > @maxRes AND (r.reservation_id - @maxRes) % 5 = 1
  AND p.name = CASE WHEN rm.room_type = 'DARKROOM' THEN N'Gói Tráng phim & In ảnh'
                    WHEN r.reservation_id % 2 = 0   THEN N'Gói Chân dung'
                    ELSE N'Gói Sản phẩm' END;

UPDATE r
SET total_amount = CAST(DATEDIFF(MINUTE, r.start_time, r.end_time) / 60.0 * rm.price_per_hour AS DECIMAL(18,2))
    + ISNULL(eq.amount, 0) + ISNULL(pk.amount, 0)
FROM dbo.Reservations r
JOIN dbo.Rooms rm ON rm.room_id = r.room_id
LEFT JOIN (SELECT reservation_id, SUM(quantity * unit_price) AS amount
           FROM dbo.ReservationEquipments WHERE reservation_id > @maxRes GROUP BY reservation_id) eq ON eq.reservation_id = r.reservation_id
LEFT JOIN (SELECT reservation_id, SUM(price) AS amount
           FROM dbo.ReservationPackages WHERE reservation_id > @maxRes GROUP BY reservation_id) pk ON pk.reservation_id = r.reservation_id
WHERE r.reservation_id > @maxRes;

PRINT N'   ... lịch sử trạng thái';
INSERT INTO dbo.ReservationStatusHistory (reservation_id, changed_by, old_status, new_status, changed_at)
SELECT r.reservation_id, r.customer_id, CAST(NULL AS VARCHAR(20)), 'PENDING', r.created_at
FROM dbo.Reservations r WHERE r.reservation_id > @maxRes
UNION ALL
SELECT r.reservation_id, s.provider_id, 'PENDING', 'CONFIRMED', DATEADD(HOUR, 2, r.created_at)
FROM dbo.Reservations r
JOIN dbo.Rooms rm ON rm.room_id = r.room_id
JOIN dbo.Studios s ON s.studio_id = rm.studio_id
WHERE r.reservation_id > @maxRes AND r.status IN ('CONFIRMED', 'IN_USE', 'COMPLETED')
UNION ALL
SELECT r.reservation_id, r.customer_id, 'CONFIRMED', 'IN_USE', DATEADD(MINUTE, -5, r.start_time)
FROM dbo.Reservations r WHERE r.reservation_id > @maxRes AND r.status IN ('IN_USE', 'COMPLETED')
UNION ALL
SELECT r.reservation_id, r.customer_id, 'IN_USE', 'COMPLETED', DATEADD(MINUTE, 10, r.end_time)
FROM dbo.Reservations r WHERE r.reservation_id > @maxRes AND r.status = 'COMPLETED'
UNION ALL
SELECT r.reservation_id, r.customer_id, 'PENDING', 'CANCELLED', DATEADD(DAY, 1, r.created_at)
FROM dbo.Reservations r WHERE r.reservation_id > @maxRes AND r.status = 'CANCELLED';
