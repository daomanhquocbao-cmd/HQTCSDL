-- Bổ sung cột cho các tính năng đăng nhập và quản lý phòng.
-- Chạy SAU schema.sql. Có thể chạy lại nhiều lần mà không lỗi.
USE FilmPhotographyPlatform;
GO

IF COL_LENGTH('dbo.Users', 'password_hash') IS NULL
    ALTER TABLE Users ADD password_hash VARCHAR(255) NULL;

IF COL_LENGTH('dbo.Rooms', 'description') IS NULL
    ALTER TABLE Rooms ADD description NVARCHAR(500) NULL;

IF COL_LENGTH('dbo.Rooms', 'hourly_price') IS NULL
    ALTER TABLE Rooms ADD hourly_price DECIMAL(10,2) NOT NULL DEFAULT 0;
GO
