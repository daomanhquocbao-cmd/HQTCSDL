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
