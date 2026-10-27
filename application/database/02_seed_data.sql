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

-- 3. BƠM REVIEWS (Đánh giá Studio từ khách hàng)
PRINT N'3. Đang bơm Reviews...';
DECLARE @min_std INT = (SELECT MIN(studio_id) FROM Studios);
DECLARE @max_std INT = (SELECT MAX(studio_id) FROM Studios);
DECLARE @min_u INT = (SELECT MIN(user_id) FROM Users);
DECLARE @max_u INT = (SELECT MAX(user_id) FROM Users);

DECLARE @rev INT = 1;
WHILE @rev <= 500
BEGIN
    INSERT INTO Reviews (studio_id, customer_id, rating, comment)
    VALUES (
        @min_std + (ABS(CHECKSUM(NEWID())) % (@max_std - @min_std + 1)),
        @min_u + (ABS(CHECKSUM(NEWID())) % (@max_u - @min_u + 1)),
        3 + (ABS(CHECKSUM(NEWID())) % 3), -- Rating từ 3 đến 5 sao
        N'Không gian phòng tối chuyên nghiệp, thiết bị hiện đại, rất đáng trải nghiệm!'
    );
    SET @rev = @rev + 1;
END
GO

-- 4. BƠM COMMUNITY POSTS & COMMENTS (Bài viết & Bình luận cộng đồng)
PRINT N'4. Đang bơm CommunityPosts & PostComments...';
DECLARE @min_u INT = (SELECT MIN(user_id) FROM Users);
DECLARE @max_u INT = (SELECT MAX(user_id) FROM Users);

DECLARE @pst INT = 1;
WHILE @pst <= 100
BEGIN
    INSERT INTO CommunityPosts (author_id, title, content, image_url)
    VALUES (
        @min_u + (ABS(CHECKSUM(NEWID())) % (@max_u - @min_u + 1)),
        N'Chia sẻ công thức pha thuốc tráng phim B&W số #' + CAST(@pst AS VARCHAR(5)),
        N'Bài viết hướng dẫn chi tiết tỉ lệ pha và nhiệt độ chuẩn để kiểm soát hạt phim tốt nhất.',
        N'https://images.filmplatform.com/posts/post_' + CAST(@pst AS VARCHAR(5)) + N'.jpg'
    );
    SET @pst = @pst + 1;
END

DECLARE @cmt INT = 1;
DECLARE @min_p INT = (SELECT MIN(post_id) FROM CommunityPosts);
DECLARE @max_p INT = (SELECT MAX(post_id) FROM CommunityPosts);

WHILE @cmt <= 300
BEGIN
    INSERT INTO PostComments (post_id, user_id, content)
    VALUES (
        @min_p + (ABS(CHECKSUM(NEWID())) % (@max_p - @min_p + 1)),
        @min_u + (ABS(CHECKSUM(NEWID())) % (@max_u - @min_u + 1)),
        N'Bài viết rất hữu ích, cảm ơn tác giả đã chia sẻ kinh nghiệm thực tế!'
    );
    SET @cmt = @cmt + 1;
END
GO
