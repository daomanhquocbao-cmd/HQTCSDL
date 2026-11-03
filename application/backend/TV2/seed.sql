-- Dữ liệu mẫu để demo. Chạy SAU schema.sql và migrations/002.
USE FilmPhotographyPlatform;
GO

INSERT INTO Rooms (name, description, hourly_price, is_active) VALUES
(N'Studio A', N'Phòng chụp ảnh nền trắng, đèn softbox', 200000, 1),
(N'Studio B', N'Phòng quay phim có green screen', 350000, 1),
(N'Studio C', N'Phòng chụp ngoại cảnh trong nhà, bối cảnh vintage', 250000, 1);
GO
-- Tạo tài khoản admin: đăng ký qua POST /api/users/register rồi chạy:
-- UPDATE Users SET role = 'admin' WHERE email = 'admin@example.com';
