/* 10 - Bổ sung hồ sơ phòng theo đề tài: thông gió, âm học, chính sách sử dụng.
   Chạy sau 01..09. Chạy lại nhiều lần vẫn an toàn. */
USE FilmPhotographyPlatform;
GO
IF COL_LENGTH('dbo.Rooms', 'ventilation') IS NULL ALTER TABLE dbo.Rooms ADD ventilation NVARCHAR(200) NULL;
IF COL_LENGTH('dbo.Rooms', 'acoustics')   IS NULL ALTER TABLE dbo.Rooms ADD acoustics   NVARCHAR(200) NULL;
IF COL_LENGTH('dbo.Rooms', 'usage_policy') IS NULL ALTER TABLE dbo.Rooms ADD usage_policy NVARCHAR(1000) NULL;
GO
UPDATE dbo.Rooms SET ventilation = N'Quạt hút + cửa sổ thoáng', acoustics = N'Cách âm cơ bản, phù hợp quay phỏng vấn',
       usage_policy = N'Không ăn uống trong phòng; hủy trước 24 giờ để không bị tính phí'
WHERE room_type = 'STUDIO' AND ventilation IS NULL;
UPDATE dbo.Rooms SET ventilation = N'Hút khí hóa chất liên tục', acoustics = N'Yên tĩnh',
       usage_policy = N'Tự đeo găng và kính; không mang đèn sáng vào khi đang rọi ảnh'
WHERE room_type = 'DARKROOM' AND ventilation IS NULL;
GO
