USE FilmPhotographyPlatform;
GO

SET NOCOUNT ON;
SET QUOTED_IDENTIFIER ON;
GO

/* ---------------------------------------------------------------
   1. USERS: 1 admin, 3 chuyên gia, 4 nhà cung cấp, 20 khách hàng
   (password_hash chỉ là chuỗi giữ chỗ - backend thật sẽ băm bcrypt)
   --------------------------------------------------------------- */
PRINT N'1. Users...';
DECLARE @pwd VARCHAR(255) = '$2b$12$SEED.PLACEHOLDER.HASH.REPLACE.IN.BACKEND';

INSERT INTO dbo.Users (username, password_hash, email, phone, full_name, role, status) VALUES
('admin',     @pwd, 'admin@filmplatform.vn',     '0900000001', N'Quản trị viên',      'ADMIN',    'ACTIVE'),
('expert1',   @pwd, 'expert1@filmplatform.vn',   '0900000002', N'Nguyễn Minh Khoa',   'EXPERT',   'ACTIVE'),
('expert2',   @pwd, 'expert2@filmplatform.vn',   '0900000003', N'Trần Thu Hà',        'EXPERT',   'ACTIVE'),
('expert3',   @pwd, 'expert3@filmplatform.vn',   '0900000004', N'Lê Quốc Bảo',        'EXPERT',   'ACTIVE'),
('provider1', @pwd, 'provider1@filmplatform.vn', '0900000005', N'Phạm Gia Huy',       'PROVIDER', 'ACTIVE'),
('provider2', @pwd, 'provider2@filmplatform.vn', '0900000006', N'Võ Ngọc Anh',        'PROVIDER', 'ACTIVE'),
('provider3', @pwd, 'provider3@filmplatform.vn', '0900000007', N'Đặng Thanh Tùng',    'PROVIDER', 'ACTIVE'),
('provider4', @pwd, 'provider4@filmplatform.vn', '0900000008', N'Hoàng Mỹ Linh',      'PROVIDER', 'PENDING');

;WITH n AS (
    SELECT TOP (20) CAST(ROW_NUMBER() OVER (ORDER BY (SELECT NULL)) AS INT) AS i
    FROM sys.all_objects
)
INSERT INTO dbo.Users (username, password_hash, email, phone, full_name, role, status)
SELECT 'customer' + RIGHT('00' + CAST(i AS VARCHAR(3)), 3),
       @pwd,
       'customer' + RIGHT('00' + CAST(i AS VARCHAR(3)), 3) + '@gmail.com',
       '0912' + RIGHT('000000' + CAST(i * 1234 AS VARCHAR(10)), 6),
       N'Khách hàng số ' + CAST(i AS NVARCHAR(3)),
       'CUSTOMER',
       CASE WHEN i = 20 THEN 'SUSPENDED' ELSE 'ACTIVE' END     -- 1 tài khoản bị khóa để demo
FROM n;
GO

/* ---------------------------------------------------------------
   2. STUDIOS (3 đã duyệt + 1 chờ duyệt), STUDIO IMAGES, ROOMS
   --------------------------------------------------------------- */
PRINT N'2. Studios, StudioImages, Rooms...';
INSERT INTO dbo.Studios (provider_id, name, address, city, latitude, longitude, description, phone, open_time, close_time, status) VALUES
((SELECT user_id FROM dbo.Users WHERE username = 'provider1'), N'Silver Grain Studio',  N'12 Nguyễn Huệ, Quận 1',     N'TP.HCM', 10.774000, 106.703000, N'Studio chụp phim phong cách vintage, ánh sáng tự nhiên.', '0281111111', '08:00', '21:00', 'APPROVED'),
((SELECT user_id FROM dbo.Users WHERE username = 'provider2'), N'Darkroom Saigon',      N'45 Lý Tự Trọng, Quận 3',    N'TP.HCM', 10.781000, 106.695000, N'Chuyên phòng tối tráng và in ảnh đen trắng.',            '0282222222', '09:00', '20:00', 'APPROVED'),
((SELECT user_id FROM dbo.Users WHERE username = 'provider3'), N'Hanoi Analog Lab',     N'8 Tràng Tiền, Hoàn Kiếm',   N'Hà Nội', 21.025000, 105.855000, N'Phòng lab analog cho cộng đồng nhiếp ảnh phim Hà Nội.',  '0243333333', '08:30', '21:30', 'APPROVED'),
((SELECT user_id FROM dbo.Users WHERE username = 'provider4'), N'Đà Nẵng Film House',   N'30 Bạch Đằng, Hải Châu',    N'Đà Nẵng',16.071000, 108.224000, N'Cơ sở mới, đang chờ admin duyệt.',                      '0236444444', '08:00', '21:00', 'PENDING');

INSERT INTO dbo.StudioImages (studio_id, image_url, is_primary)
SELECT s.studio_id,
       N'https://images.filmplatform.vn/studios/' + CAST(s.studio_id AS NVARCHAR(10)) + N'_' + CAST(k.n AS NVARCHAR(2)) + N'.jpg',
       CASE WHEN k.n = 1 THEN 1 ELSE 0 END
FROM dbo.Studios s
CROSS JOIN (VALUES (1), (2)) k(n);

-- Mỗi studio có 3 phòng: 2 phòng chụp + 1 phòng tối (giá lệch nhẹ giữa các studio)
INSERT INTO dbo.Rooms (studio_id, name, room_type, capacity, area_sqm, art_style, lighting, amenities, price_per_hour, description)
SELECT s.studio_id, d.name, d.room_type, d.capacity, d.area, d.style, d.lighting, d.amenities,
       d.price + (s.studio_id % 3) * 20000, d.descr
FROM dbo.Studios s
CROSS JOIN (VALUES
    (N'Phòng chụp Vintage', 'STUDIO',   6, 35.0, N'Vintage',      N'Softbox + cửa sổ ánh sáng tự nhiên', N'Phông nền, ghế, bàn trang điểm',        250000, N'Không gian hoài cổ, hợp chụp chân dung phim.'),
    (N'Phòng chụp Minimal', 'STUDIO',   4, 25.0, N'Minimal',      N'Đèn LED liên tục',                    N'Phông trắng, hộp sáng',                  220000, N'Phòng tối giản, phù hợp chụp sản phẩm.'),
    (N'Phòng tối B&W',      'DARKROOM', 3, 15.0, N'Truyền thống', N'Đèn an toàn màu đỏ',                  N'Bồn rửa, kẹp phơi, máy phóng ảnh',       180000, N'Phòng tối tráng phim và in ảnh đen trắng.')
) d(name, room_type, capacity, area, style, lighting, amenities, price, descr);

-- 1 phòng đang bảo trì (để demo: không cho đặt)
UPDATE dbo.Rooms SET status = 'MAINTENANCE'
WHERE name = N'Phòng chụp Minimal'
  AND studio_id = (SELECT studio_id FROM dbo.Studios WHERE name = N'Darkroom Saigon');
GO

/* ---------------------------------------------------------------
   3. EQUIPMENT, MAINTENANCE, PACKAGES, PACKAGE-EQUIPMENT
   --------------------------------------------------------------- */
PRINT N'3. Equipment, EquipmentMaintenance, ServicePackages, PackageEquipment...';

-- Mỗi studio có đủ 8 loại (mỗi category đúng 1 dòng / studio)
INSERT INTO dbo.Equipment (studio_id, name, equipment_type, category, quantity, rental_price, next_maintenance_date)
SELECT s.studio_id, d.name, d.etype, d.cat, d.qty, d.price,
       CASE WHEN d.etype = 'REUSABLE'
            THEN DATEADD(DAY, 20 + (s.studio_id * 17 + d.slot * 11) % 90, CAST(GETDATE() AS DATE)) END
FROM dbo.Studios s
CROSS JOIN (VALUES
    (1, N'Máy ảnh phim Pentax K1000',  'REUSABLE',   'CAMERA',   6, 120000),
    (2, N'Ống kính 50mm f/1.4',        'REUSABLE',   'LENS',     6,  80000),
    (3, N'Đèn flash Godox',            'REUSABLE',   'LIGHTING', 6,  60000),
    (4, N'Chân máy Manfrotto',         'REUSABLE',   'TRIPOD',   6,  40000),
    (5, N'Máy phóng ảnh (enlarger)',   'REUSABLE',   'ENLARGER', 3, 150000),
    (6, N'Máy scan phim Epson V600',   'REUSABLE',   'SCANNER',  3, 100000),
    (7, N'Hóa chất tráng phim B&W',    'CONSUMABLE', 'CHEMICAL', 60,  50000),
    (8, N'Giấy in ảnh 8x10',           'CONSUMABLE', 'PAPER',    200,  8000)
) d(slot, name, etype, cat, qty, price);

-- Một vài thiết bị có tình trạng đặc biệt (cho truy vấn cảnh báo)
UPDATE dbo.Equipment
SET status = 'NEEDS_MAINTENANCE', next_maintenance_date = DATEADD(DAY, -3, CAST(GETDATE() AS DATE))
WHERE category = 'ENLARGER' AND studio_id = (SELECT studio_id FROM dbo.Studios WHERE name = N'Darkroom Saigon');

UPDATE dbo.Equipment SET status = 'BROKEN'
WHERE category = 'SCANNER' AND studio_id = (SELECT studio_id FROM dbo.Studios WHERE name = N'Hanoi Analog Lab');

UPDATE dbo.Equipment SET quantity = 6        -- tồn kho hóa chất thấp
WHERE category = 'CHEMICAL' AND studio_id = (SELECT studio_id FROM dbo.Studios WHERE name = N'Silver Grain Studio');

-- Lịch sử bảo trì: mỗi thiết bị REUSABLE đã bảo trì 1 lần cách đây 60 ngày
INSERT INTO dbo.EquipmentMaintenance (equipment_id, maintenance_date, cost, description, status)
SELECT equipment_id, DATEADD(DAY, -60, GETDATE()), 150000, N'Bảo trì định kỳ, vệ sinh và hiệu chỉnh.', 'DONE'
FROM dbo.Equipment WHERE equipment_type = 'REUSABLE';

-- Thiết bị quá hạn bảo trì -> đã có lịch bảo trì sắp tới
INSERT INTO dbo.EquipmentMaintenance (equipment_id, maintenance_date, cost, description, status)
SELECT equipment_id, DATEADD(DAY, 3, GETDATE()), 300000, N'Thay linh kiện hao mòn, canh chỉnh quang học.', 'SCHEDULED'
FROM dbo.Equipment WHERE status = 'NEEDS_MAINTENANCE';

-- Mỗi studio có 3 gói dịch vụ, mỗi gói do 1 chuyên gia hướng dẫn
INSERT INTO dbo.ServicePackages (studio_id, name, price, duration_hours, room_type, instructor_id, description)
SELECT s.studio_id, d.name, d.price, d.hours, d.room_type,
       (SELECT user_id FROM dbo.Users WHERE username = d.expert), d.descr
FROM dbo.Studios s
CROSS JOIN (VALUES
    (N'Gói Chân dung',             650000, 3.0, 'STUDIO',   'expert1', N'Chụp chân dung phim kèm máy ảnh, ống kính, đèn.'),
    (N'Gói Sản phẩm',              550000, 2.0, 'STUDIO',   'expert2', N'Chụp sản phẩm với bộ đèn và chân máy.'),
    (N'Gói Tráng phim & In ảnh',   450000, 3.0, 'DARKROOM', 'expert3', N'Hướng dẫn tráng phim, in ảnh đen trắng trong phòng tối.')
) d(name, price, hours, room_type, expert, descr);

-- Thiết bị đi kèm từng gói (ghép theo category nên luôn đúng studio)
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
JOIN dbo.Equipment e ON e.studio_id = p.studio_id AND e.category = m.cat;
GO

/* ---------------------------------------------------------------
   4. RESERVATIONS - 72 đơn, trải từ 24 ngày trước đến 8 ngày tới
   Cách tạo để KHÔNG BAO GIỜ trùng lịch: đơn thứ i vào phòng (i mod số phòng),
   ngày (i div số phòng); mỗi phòng chỉ có 1 đơn / ngày.
   --------------------------------------------------------------- */
PRINT N'4. Reservations + chi tiết + lịch sử trạng thái...';
DECLARE @R INT = (SELECT COUNT(*) FROM dbo.Rooms r JOIN dbo.Studios s ON s.studio_id = r.studio_id
                  WHERE r.status = 'AVAILABLE' AND s.status = 'APPROVED');
DECLARE @C INT = (SELECT COUNT(*) FROM dbo.Users WHERE role = 'CUSTOMER' AND status = 'ACTIVE');
DECLARE @today DATETIME = CAST(CAST(GETDATE() AS DATE) AS DATETIME);

;WITH rm AS (
    SELECT r.room_id, r.price_per_hour,
           CAST(ROW_NUMBER() OVER (ORDER BY r.room_id) - 1 AS INT) AS idx
    FROM dbo.Rooms r JOIN dbo.Studios s ON s.studio_id = r.studio_id
    WHERE r.status = 'AVAILABLE' AND s.status = 'APPROVED'
), cu AS (
    SELECT user_id, CAST(ROW_NUMBER() OVER (ORDER BY user_id) - 1 AS INT) AS idx
    FROM dbo.Users WHERE role = 'CUSTOMER' AND status = 'ACTIVE'
), n AS (
    SELECT TOP (72) CAST(ROW_NUMBER() OVER (ORDER BY (SELECT NULL)) - 1 AS INT) AS i
    FROM sys.all_objects
), x AS (
    SELECT n.i, rm.room_id, rm.price_per_hour, cu.user_id AS customer_id,
           DATEADD(HOUR, 9 + (n.i % 3) * 3, DATEADD(DAY, -24 + (n.i / @R) * 4, @today)) AS start_time,
           2 + (n.i % 2) AS dur
    FROM n
    JOIN rm ON rm.idx = n.i % @R
    JOIN cu ON cu.idx = (n.i * 7) % @C
), y AS (
    SELECT x.*, DATEADD(HOUR, x.dur, x.start_time) AS end_time FROM x
)
INSERT INTO dbo.Reservations (room_id, customer_id, start_time, end_time, total_amount, customer_note, status, created_at)
SELECT room_id, customer_id, start_time, end_time,
       CAST(DATEDIFF(MINUTE, start_time, end_time) / 60.0 * price_per_hour AS DECIMAL(18,2)),
       CASE WHEN i % 5 = 0 THEN N'Nhờ chuẩn bị sẵn phông nền và ghế.' END,
       CASE WHEN end_time < GETDATE() THEN (CASE WHEN i % 9 = 4 THEN 'CANCELLED' ELSE 'COMPLETED' END)
            WHEN start_time <= GETDATE()  THEN 'IN_USE'
            WHEN i % 3 = 0                THEN 'PENDING'
            ELSE 'CONFIRMED' END,
       DATEADD(DAY, -3, start_time)
FROM y
ORDER BY i;

-- Mã QR cho các đơn đã xác nhận trở lên
UPDATE dbo.Reservations
SET qr_code = 'QR-' + RIGHT('00000' + CAST(reservation_id AS VARCHAR(10)), 5) + '-'
              + CAST(ABS(CHECKSUM(reservation_id * 7919)) % 1000000 AS VARCHAR(10))
WHERE status IN ('CONFIRMED', 'IN_USE', 'COMPLETED');

-- Thuê thêm 1 máy ảnh cho 1/4 số đơn
INSERT INTO dbo.ReservationEquipments (reservation_id, equipment_id, quantity, unit_price)
SELECT r.reservation_id, e.equipment_id, 1, e.rental_price
FROM dbo.Reservations r
JOIN dbo.Rooms rm ON rm.room_id = r.room_id
JOIN dbo.Equipment e ON e.studio_id = rm.studio_id AND e.category = 'CAMERA'
WHERE r.reservation_id % 4 = 0;

-- Chọn gói dịch vụ cho 1/5 số đơn (gói phải đúng loại phòng và đúng studio)
INSERT INTO dbo.ReservationPackages (reservation_id, package_id, price)
SELECT r.reservation_id, p.package_id, p.price
FROM dbo.Reservations r
JOIN dbo.Rooms rm ON rm.room_id = r.room_id
JOIN dbo.ServicePackages p ON p.studio_id = rm.studio_id AND p.room_type = rm.room_type
WHERE r.reservation_id % 5 = 1
  AND p.name = CASE WHEN rm.room_type = 'DARKROOM' THEN N'Gói Tráng phim & In ảnh'
                    WHEN r.reservation_id % 2 = 0   THEN N'Gói Chân dung'
                    ELSE N'Gói Sản phẩm' END;

-- Tính lại tổng tiền = phòng + thiết bị thuê thêm + gói (cùng công thức với sp_RecalculateReservationTotal)
UPDATE r
SET total_amount = CAST(DATEDIFF(MINUTE, r.start_time, r.end_time) / 60.0 * rm.price_per_hour AS DECIMAL(18,2))
    + ISNULL((SELECT SUM(re.quantity * re.unit_price) FROM dbo.ReservationEquipments re WHERE re.reservation_id = r.reservation_id), 0)
    + ISNULL((SELECT SUM(rp.price) FROM dbo.ReservationPackages rp WHERE rp.reservation_id = r.reservation_id), 0)
FROM dbo.Reservations r
JOIN dbo.Rooms rm ON rm.room_id = r.room_id;

-- Lịch sử trạng thái (seed thủ công, mốc thời gian hợp lý)
INSERT INTO dbo.ReservationStatusHistory (reservation_id, changed_by, old_status, new_status, changed_at)
SELECT r.reservation_id, r.customer_id, CAST(NULL AS VARCHAR(20)), 'PENDING', r.created_at
FROM dbo.Reservations r
UNION ALL
SELECT r.reservation_id, s.provider_id, 'PENDING', 'CONFIRMED', DATEADD(HOUR, 2, r.created_at)
FROM dbo.Reservations r
JOIN dbo.Rooms rm ON rm.room_id = r.room_id
JOIN dbo.Studios s ON s.studio_id = rm.studio_id
WHERE r.status IN ('CONFIRMED', 'IN_USE', 'COMPLETED')
UNION ALL
SELECT r.reservation_id, r.customer_id, 'CONFIRMED', 'IN_USE', DATEADD(MINUTE, -5, r.start_time)
FROM dbo.Reservations r WHERE r.status IN ('IN_USE', 'COMPLETED')
UNION ALL
SELECT r.reservation_id, r.customer_id, 'IN_USE', 'COMPLETED', DATEADD(MINUTE, 10, r.end_time)
FROM dbo.Reservations r WHERE r.status = 'COMPLETED'
UNION ALL
SELECT r.reservation_id, r.customer_id, 'PENDING', 'CANCELLED', DATEADD(DAY, 1, r.created_at)
FROM dbo.Reservations r WHERE r.status = 'CANCELLED';
GO

/* ---------------------------------------------------------------
   5. PAYMENTS, SESSIONS, REVIEWS, DISPUTES
   --------------------------------------------------------------- */
PRINT N'5. Payments, ServiceSessions, Reviews, Disputes...';

-- Đơn COMPLETED / IN_USE: đã trả đủ
INSERT INTO dbo.Payments (reservation_id, amount, payment_method, transaction_code, status, paid_at, created_at)
SELECT r.reservation_id, r.total_amount,
       CHOOSE(r.reservation_id % 4 + 1, 'VNPAY', 'MOMO', 'STRIPE', 'BANK_TRANSFER'),
       'TXN' + RIGHT('00000' + CAST(r.reservation_id AS VARCHAR(10)), 5) + 'A',
       'SUCCESS', DATEADD(HOUR, 3, r.created_at), DATEADD(HOUR, 3, r.created_at)
FROM dbo.Reservations r WHERE r.status IN ('COMPLETED', 'IN_USE');

-- Đơn CONFIRMED: id lẻ trả đủ, id chẵn mới đặt cọc 50%
INSERT INTO dbo.Payments (reservation_id, amount, payment_method, transaction_code, status, paid_at, created_at)
SELECT r.reservation_id,
       CASE WHEN r.reservation_id % 2 = 1 THEN r.total_amount ELSE ROUND(r.total_amount * 0.5, 0) END,
       CHOOSE(r.reservation_id % 4 + 1, 'VNPAY', 'MOMO', 'STRIPE', 'BANK_TRANSFER'),
       'TXN' + RIGHT('00000' + CAST(r.reservation_id AS VARCHAR(10)), 5) + 'B',
       'SUCCESS', DATEADD(HOUR, 3, r.created_at), DATEADD(HOUR, 3, r.created_at)
FROM dbo.Reservations r WHERE r.status = 'CONFIRMED';

-- Đơn CANCELLED: đã hoàn tiền
INSERT INTO dbo.Payments (reservation_id, amount, payment_method, transaction_code, status, paid_at, created_at)
SELECT r.reservation_id, r.total_amount, 'VNPAY',
       'TXN' + RIGHT('00000' + CAST(r.reservation_id AS VARCHAR(10)), 5) + 'C',
       'REFUNDED', DATEADD(HOUR, 3, r.created_at), DATEADD(HOUR, 3, r.created_at)
FROM dbo.Reservations r WHERE r.status = 'CANCELLED';

-- Một số đơn PENDING có giao dịch đang chờ
INSERT INTO dbo.Payments (reservation_id, amount, payment_method, transaction_code, status, paid_at, created_at)
SELECT r.reservation_id, r.total_amount, 'MOMO',
       'TXN' + RIGHT('00000' + CAST(r.reservation_id AS VARCHAR(10)), 5) + 'D',
       'PENDING', NULL, GETDATE()
FROM dbo.Reservations r WHERE r.status = 'PENDING' AND r.reservation_id % 2 = 0;

-- Phiên sử dụng thực tế: đơn COMPLETED đã check-out, đơn IN_USE đang dùng
INSERT INTO dbo.ServiceSessions (reservation_id, checkin_time, checkout_time, status)
SELECT reservation_id,
       DATEADD(MINUTE, -5, start_time),
       CASE WHEN status = 'COMPLETED' THEN DATEADD(MINUTE, 10, end_time) END,
       CASE WHEN status = 'COMPLETED' THEN 'CHECKED_OUT' ELSE 'IN_USE' END
FROM dbo.Reservations WHERE status IN ('COMPLETED', 'IN_USE');

-- Đánh giá: khoảng 2/3 đơn COMPLETED được khách đánh giá (đúng khách, đúng studio)
INSERT INTO dbo.Reviews (reservation_id, studio_id, customer_id, rating, comment, created_at)
SELECT r.reservation_id, rm.studio_id, r.customer_id,
       CASE WHEN r.reservation_id % 7 = 0 THEN 3 ELSE 4 + (r.reservation_id % 2) END,
       CHOOSE(CASE WHEN r.reservation_id % 7 = 0 THEN 1 ELSE 2 + (r.reservation_id % 2) END,
              N'Phòng ổn, thiết bị hơi cũ một chút.',
              N'Không gian đẹp, nhân viên hỗ trợ nhiệt tình.',
              N'Rất tuyệt vời, thiết bị chuyên nghiệp, sẽ quay lại!'),
       DATEADD(DAY, 1, r.end_time)
FROM dbo.Reservations r
JOIN dbo.Rooms rm ON rm.room_id = r.room_id
WHERE r.status = 'COMPLETED' AND r.reservation_id % 3 <> 0;

-- 3 khiếu nại ở 3 trạng thái khác nhau
;WITH c AS (
    SELECT reservation_id, customer_id, end_time,
           ROW_NUMBER() OVER (ORDER BY reservation_id) AS rn
    FROM dbo.Reservations WHERE status = 'COMPLETED'
)
INSERT INTO dbo.Disputes (reservation_id, raised_by, reason, status, resolution, resolved_by, created_at, resolved_at)
SELECT reservation_id, customer_id,
       CHOOSE(rn, N'Thiết bị thuê bị lỗi giữa buổi chụp.',
                  N'Phòng không đúng như mô tả trên hệ thống.',
                  N'Bị tính thêm phí ngoài thỏa thuận.'),
       CHOOSE(rn, 'RESOLVED', 'IN_REVIEW', 'OPEN'),
       CASE WHEN rn = 1 THEN N'Đã hoàn 50% phí thuê thiết bị cho khách.' END,
       CASE WHEN rn = 1 THEN (SELECT user_id FROM dbo.Users WHERE username = 'admin') END,
       DATEADD(DAY, 1, end_time),
       CASE WHEN rn = 1 THEN DATEADD(DAY, 3, end_time) END
FROM c WHERE rn <= 3;
GO

/* ---------------------------------------------------------------
   6. WORKSHOPS + ĐĂNG KÝ, BÀI VIẾT + BÌNH LUẬN
   --------------------------------------------------------------- */
PRINT N'6. Workshops, CommunityPosts, PostComments...';
DECLARE @today DATETIME = CAST(CAST(GETDATE() AS DATE) AS DATETIME);

INSERT INTO dbo.Workshops (expert_id, studio_id, title, description, capacity, fee, start_time, end_time, status) VALUES
((SELECT user_id FROM dbo.Users WHERE username = 'expert1'), (SELECT studio_id FROM dbo.Studios WHERE name = N'Silver Grain Studio'),
    N'Tráng phim đen trắng tại nhà',     N'Học tráng phim B&W với dụng cụ đơn giản.', 5, 200000,
    DATEADD(HOUR, 14, DATEADD(DAY, 10, @today)), DATEADD(HOUR, 17, DATEADD(DAY, 10, @today)), 'CLOSED'),     -- đã đủ 5/5
((SELECT user_id FROM dbo.Users WHERE username = 'expert2'), NULL,
    N'Chụp phim chân dung (online)',      N'Buổi chia sẻ online về bố cục và ánh sáng.', 20, 0,
    DATEADD(HOUR, 19, DATEADD(DAY, 14, @today)), DATEADD(HOUR, 21, DATEADD(DAY, 14, @today)), 'OPEN'),
((SELECT user_id FROM dbo.Users WHERE username = 'expert3'), (SELECT studio_id FROM dbo.Studios WHERE name = N'Darkroom Saigon'),
    N'In ảnh trong phòng tối cơ bản',     N'Thực hành in ảnh với máy phóng.', 12, 300000,
    DATEADD(HOUR, 9, DATEADD(DAY, 21, @today)), DATEADD(HOUR, 12, DATEADD(DAY, 21, @today)), 'OPEN'),
((SELECT user_id FROM dbo.Users WHERE username = 'expert1'), (SELECT studio_id FROM dbo.Studios WHERE name = N'Hanoi Analog Lab'),
    N'Nhập môn nhiếp ảnh phim 35mm',      N'Workshop đã diễn ra.', 10, 150000,
    DATEADD(HOUR, 9, DATEADD(DAY, -15, @today)), DATEADD(HOUR, 12, DATEADD(DAY, -15, @today)), 'COMPLETED');

-- Số người đăng ký: workshop 1: 5 (đủ chỗ), 2: 8, 3: 3, 4: 7
INSERT INTO dbo.WorkshopRegistrations (workshop_id, customer_id, registered_at)
SELECT w.workshop_id, c.user_id,
       CASE WHEN w.start_time < GETDATE() THEN DATEADD(DAY, -7, w.start_time)
            ELSE DATEADD(HOUR, -c.cn * 5, GETDATE()) END
FROM (SELECT workshop_id, start_time, ROW_NUMBER() OVER (ORDER BY workshop_id) AS wn FROM dbo.Workshops) w
JOIN (VALUES (1, 5), (2, 8), (3, 3), (4, 7)) q(wn, cnt) ON q.wn = w.wn
JOIN (SELECT user_id, ROW_NUMBER() OVER (ORDER BY user_id) AS cn
      FROM dbo.Users WHERE role = 'CUSTOMER' AND status = 'ACTIVE') c ON c.cn <= q.cnt;

INSERT INTO dbo.CommunityPosts (author_id, post_type, title, content, image_url, created_at) VALUES
((SELECT user_id FROM dbo.Users WHERE username = 'expert1'),   'TUTORIAL',         N'Công thức pha thuốc tráng phim B&W',        N'Tỉ lệ pha và nhiệt độ chuẩn để kiểm soát hạt phim.', N'https://images.filmplatform.vn/posts/1.jpg', DATEADD(DAY, -20, GETDATE())),
((SELECT user_id FROM dbo.Users WHERE username = 'expert2'),   'ARTICLE',          N'Vì sao nhiếp ảnh phim đang quay trở lại?',    N'Cảm giác chậm rãi và chất màu riêng của phim.',        NULL,                                          DATEADD(DAY, -18, GETDATE())),
((SELECT user_id FROM dbo.Users WHERE username = 'expert3'),   'EQUIPMENT_REVIEW', N'Review Pentax K1000 sau 1 năm sử dụng',     N'Ưu nhược điểm của dòng máy cơ huyền thoại.',           N'https://images.filmplatform.vn/posts/3.jpg', DATEADD(DAY, -16, GETDATE())),
((SELECT user_id FROM dbo.Users WHERE username = 'customer001'),'DISCUSSION',      N'Nên chọn phim Kodak hay Fuji?',               N'Mọi người hay dùng loại nào cho chân dung?',           NULL,                                          DATEADD(DAY, -14, GETDATE())),
((SELECT user_id FROM dbo.Users WHERE username = 'customer002'),'DISCUSSION',      N'Tìm bạn đi chụp phim cuối tuần ở Sài Gòn',    N'Ai đi cùng không, mình có sẵn 2 cuộn.',                NULL,                                          DATEADD(DAY, -12, GETDATE())),
((SELECT user_id FROM dbo.Users WHERE username = 'expert1'),   'WORKSHOP_ANNOUNCEMENT', N'Mở đăng ký workshop tráng phim',        N'Số lượng có hạn, đăng ký sớm nhé.',                    NULL,                                          DATEADD(DAY, -10, GETDATE())),
((SELECT user_id FROM dbo.Users WHERE username = 'customer003'),'DISCUSSION',      N'Kinh nghiệm thuê phòng tối lần đầu',          N'Chia sẻ lại những điều mình rút ra.',                  NULL,                                          DATEADD(DAY, -8, GETDATE())),
((SELECT user_id FROM dbo.Users WHERE username = 'customer004'),'ARTICLE',         N'Hành trình từ digital sang analog',           N'Mình đã đổi thói quen chụp như thế nào.',              N'https://images.filmplatform.vn/posts/8.jpg', DATEADD(DAY, -6, GETDATE())),
((SELECT user_id FROM dbo.Users WHERE username = 'expert2'),   'TUTORIAL',         N'Bố cục ba phần ba với phim 35mm',             N'Một vài mẹo đơn giản cho người mới.',                  NULL,                                          DATEADD(DAY, -4, GETDATE())),
((SELECT user_id FROM dbo.Users WHERE username = 'customer005'),'EQUIPMENT_REVIEW',N'Trải nghiệm máy scan phim Epson V600',        N'Chất lượng scan so với gửi lab.',                      NULL,                                          DATEADD(DAY, -2, GETDATE()));

DECLARE @P INT = (SELECT COUNT(*) FROM dbo.CommunityPosts);
DECLARE @U INT = (SELECT COUNT(*) FROM dbo.Users WHERE status = 'ACTIVE');

;WITH n AS (
    SELECT TOP (30) CAST(ROW_NUMBER() OVER (ORDER BY (SELECT NULL)) - 1 AS INT) AS i FROM sys.all_objects
), p AS (
    SELECT post_id, CAST(ROW_NUMBER() OVER (ORDER BY post_id) - 1 AS INT) AS idx FROM dbo.CommunityPosts
), u AS (
    SELECT user_id, CAST(ROW_NUMBER() OVER (ORDER BY user_id) - 1 AS INT) AS idx FROM dbo.Users WHERE status = 'ACTIVE'
)
INSERT INTO dbo.PostComments (post_id, user_id, content, created_at)
SELECT p.post_id, u.user_id,
       CHOOSE(n.i % 4 + 1, N'Bài viết rất hữu ích, cảm ơn bạn đã chia sẻ!',
                           N'Mình cũng từng gặp trường hợp tương tự.',
                           N'Cho mình hỏi thêm về phần này được không?',
                           N'Hay quá, mong chờ bài tiếp theo.'),
       DATEADD(HOUR, -n.i * 6, GETDATE())
FROM n
JOIN p ON p.idx = n.i % @P
JOIN u ON u.idx = (n.i * 3) % @U;
GO

SET NOEXEC OFF;
GO

PRINT N'=== HOÀN TẤT SEED. Số dòng mỗi bảng: ===';
SELECT 'Users' AS tbl, COUNT(*) AS n FROM dbo.Users UNION ALL
SELECT 'Studios', COUNT(*) FROM dbo.Studios UNION ALL
SELECT 'Rooms', COUNT(*) FROM dbo.Rooms UNION ALL
SELECT 'Equipment', COUNT(*) FROM dbo.Equipment UNION ALL
SELECT 'ServicePackages', COUNT(*) FROM dbo.ServicePackages UNION ALL
SELECT 'Reservations', COUNT(*) FROM dbo.Reservations UNION ALL
SELECT 'Payments', COUNT(*) FROM dbo.Payments UNION ALL
SELECT 'Reviews', COUNT(*) FROM dbo.Reviews UNION ALL
SELECT 'Workshops', COUNT(*) FROM dbo.Workshops UNION ALL
SELECT 'WorkshopRegistrations', COUNT(*) FROM dbo.WorkshopRegistrations UNION ALL
SELECT 'CommunityPosts', COUNT(*) FROM dbo.CommunityPosts UNION ALL
SELECT 'PostComments', COUNT(*) FROM dbo.PostComments;
GO
