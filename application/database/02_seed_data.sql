USE FilmPhotographyPlatform;
GO

SET NOCOUNT ON;

PRINT N'=== BẮT ĐẦU BƠM DỮ LIỆU ĐỒNG BỘ CHO CÁC BẢNG MỞ RỘNG ===';

-- Lấy khoảng giá trị ID hiện có trên hệ thống để đảm bảo khớp tuyệt đối khóa ngoại (FK)
DECLARE @min_u INT = (SELECT MIN(user_id) FROM Users);
DECLARE @max_u INT = (SELECT MAX(user_id) FROM Users);
DECLARE @min_std INT = (SELECT MIN(studio_id) FROM Studios);
DECLARE @max_std INT = (SELECT MAX(studio_id) FROM Studios);
DECLARE @min_res INT = (SELECT MIN(reservation_id) FROM Reservations);
DECLARE @max_res INT = (SELECT MAX(reservation_id) FROM Reservations);
DECLARE @min_eq INT = (SELECT MIN(equipment_id) FROM Equipment);
DECLARE @max_eq INT = (SELECT MAX(equipment_id) FROM Equipment);
DECLARE @min_pkg INT = (SELECT MIN(package_id) FROM ServicePackages);
DECLARE @max_pkg INT = (SELECT MAX(package_id) FROM ServicePackages);

-- 1. BƠM STUDIO IMAGES (Ảnh gallery cho các Studio)
PRINT N'1. Đang bơm StudioImages...';
DECLARE @img INT = 1;
WHILE @img <= 200
BEGIN
    INSERT INTO StudioImages (studio_id, image_url, is_primary)
    VALUES (
        @min_std + (ABS(CHECKSUM(NEWID())) % (@max_std - @min_std + 1)),
        N'https://images.filmplatform.com/studios/gallery_' + CAST(@img AS VARCHAR(5)) + N'.jpg',
        CASE WHEN @img % 5 = 1 THEN 1 ELSE 0 END
    );
    SET @img = @img + 1;
END
GO

-- 2. BƠM PAYMENTS (Thanh toán cho các đơn Reservations)
PRINT N'2. Đang bơm Payments...';
DECLARE @min_res INT = (SELECT MIN(reservation_id) FROM Reservations);
DECLARE @max_res INT = (SELECT MAX(reservation_id) FROM Reservations);

DECLARE @pay INT = 1;
WHILE @pay <= 1000
BEGIN
    INSERT INTO Payments (reservation_id, amount, payment_method, transaction_code, status)
    VALUES (
        @min_res + (ABS(CHECKSUM(NEWID())) % (@max_res - @min_res + 1)),
        250000.00,
        CASE (@pay % 3) WHEN 0 THEN 'VNPAY' WHEN 1 THEN 'MOMO' ELSE 'BANK_TRANSFER' END,
        'TXN_CODE_' + CAST(ABS(CHECKSUM(NEWID())) AS VARCHAR(20)),
        'SUCCESS'
    );
    SET @pay = @pay + 1;
END
GO
