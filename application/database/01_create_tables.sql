CREATE DATABASE FilmPhotographyPlatform;
GO
USE FilmPhotographyPlatform;
GO

-- 1. Bảng Users
CREATE TABLE dbo.Users (
    user_id INT IDENTITY(1,1) PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    phone VARCHAR(20) NULL,
    role VARCHAR(20) NOT NULL CHECK (role IN ('ADMIN', 'EXPERT', 'PROVIDER', 'CUSTOMER')),
    created_at DATETIME DEFAULT GETDATE()
);
GO

-- 2. Bảng Studios
CREATE TABLE dbo.Studios (
    studio_id INT IDENTITY(1,1) PRIMARY KEY,
    provider_id INT NULL FOREIGN KEY REFERENCES dbo.Users(user_id),
    name NVARCHAR(100) NOT NULL,
    address NVARCHAR(255) NOT NULL,
    description NVARCHAR(MAX) NULL,
    phone VARCHAR(20) NULL,
    created_at DATETIME DEFAULT GETDATE()
);
GO

-- 3. Bảng Rooms
CREATE TABLE dbo.Rooms (
    room_id INT IDENTITY(1,1) PRIMARY KEY,
    studio_id INT NULL FOREIGN KEY REFERENCES dbo.Studios(studio_id) ON DELETE CASCADE,
    name NVARCHAR(100) NOT NULL,
    room_type VARCHAR(20) NOT NULL CHECK (room_type IN ('STUDIO', 'DARKROOM')),
    capacity INT NOT NULL,
    price_per_hour DECIMAL(18, 2) NOT NULL,
    description NVARCHAR(MAX) NULL,
    status VARCHAR(20) DEFAULT 'AVAILABLE' CHECK (status IN ('AVAILABLE', 'MAINTENANCE', 'INACTIVE')),
    created_at DATETIME DEFAULT GETDATE()
);
GO

-- 4. Bảng Equipment
CREATE TABLE dbo.Equipment (
    equipment_id INT IDENTITY(1,1) PRIMARY KEY,
    studio_id INT NULL FOREIGN KEY REFERENCES dbo.Studios(studio_id) ON DELETE CASCADE,
    name NVARCHAR(100) NOT NULL,
    equipment_type VARCHAR(20) NOT NULL CHECK (equipment_type IN ('REUSABLE', 'CONSUMABLE')),
    quantity INT NOT NULL,
    price DECIMAL(18, 2) NOT NULL,
    status VARCHAR(20) DEFAULT 'GOOD'
);
GO

-- 5. Bảng ServicePackages
CREATE TABLE dbo.ServicePackages (
    package_id INT IDENTITY(1,1) PRIMARY KEY,
    studio_id INT NULL FOREIGN KEY REFERENCES dbo.Studios(studio_id) ON DELETE CASCADE,
    name NVARCHAR(100) NOT NULL,
    price DECIMAL(18, 2) NOT NULL,
    description NVARCHAR(MAX) NULL,
    created_at DATETIME DEFAULT GETDATE()
);
GO

-- 6. Bảng Reservations
CREATE TABLE dbo.Reservations (
    reservation_id INT IDENTITY(1,1) PRIMARY KEY,
    room_id INT NULL FOREIGN KEY REFERENCES dbo.Rooms(room_id),
    customer_id INT NULL FOREIGN KEY REFERENCES dbo.Users(user_id),
    start_time DATETIME NOT NULL,
    end_time DATETIME NOT NULL,
    total_amount DECIMAL(18, 2) NOT NULL,
    customer_note NVARCHAR(MAX) NULL,
    status VARCHAR(20) DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'CONFIRMED', 'CANCELLED', 'COMPLETED')),
    created_at DATETIME DEFAULT GETDATE()
);
GO

-- 7. Bảng Workshops
CREATE TABLE dbo.Workshops (
    workshop_id INT IDENTITY(1,1) PRIMARY KEY,
    expert_id INT NULL FOREIGN KEY REFERENCES dbo.Users(user_id),
    title NVARCHAR(200) NOT NULL,
    description NVARCHAR(MAX) NULL,
    capacity INT NOT NULL,
    start_time DATETIME NOT NULL,
    end_time DATETIME NOT NULL,
    created_at DATETIME DEFAULT GETDATE()
);
GO

-- 8. Bảng WorkshopRegistrations
CREATE TABLE dbo.WorkshopRegistrations (
    registration_id INT IDENTITY(1,1) PRIMARY KEY,
    workshop_id INT NULL FOREIGN KEY REFERENCES dbo.Workshops(workshop_id) ON DELETE CASCADE,
    customer_id INT NULL FOREIGN KEY REFERENCES dbo.Users(user_id) ON DELETE CASCADE,
    registered_at DATETIME DEFAULT GETDATE(),
    CONSTRAINT UQ_Workshop_Customer UNIQUE (workshop_id, customer_id)
);
GO

-- 9. Bảng StudioImages (Ảnh của Studio)
CREATE TABLE dbo.StudioImages (
    image_id INT IDENTITY(1,1) PRIMARY KEY,
    studio_id INT NULL FOREIGN KEY REFERENCES dbo.Studios(studio_id) ON DELETE CASCADE,
    image_url NVARCHAR(500) NOT NULL,
    is_primary BIT DEFAULT 0,
    created_at DATETIME DEFAULT GETDATE()
);
GO

-- 10. Bảng EquipmentMaintenance (Lịch sử bảo trì thiết bị)
CREATE TABLE dbo.EquipmentMaintenance (
    maintenance_id INT IDENTITY(1,1) PRIMARY KEY,
    equipment_id INT NULL FOREIGN KEY REFERENCES dbo.Equipment(equipment_id) ON DELETE CASCADE,
    maintenance_date DATETIME DEFAULT GETDATE(),
    cost DECIMAL(18, 2) NOT NULL,
    description NVARCHAR(MAX) NULL
);
GO

-- 11. Bảng PackageEquipment (Thiết bị đi kèm gói dịch vụ - Nhiều nhiều)
CREATE TABLE dbo.PackageEquipment (
    package_id INT FOREIGN KEY REFERENCES dbo.ServicePackages(package_id) ON DELETE CASCADE,
    equipment_id INT FOREIGN KEY REFERENCES dbo.Equipment(equipment_id),
    quantity_included INT NOT NULL DEFAULT 1,
    PRIMARY KEY (package_id, equipment_id)
);
GO

-- 12. Bảng ReservationEquipments (Thiết bị thuê thêm trong đơn đặt phòng)
CREATE TABLE dbo.ReservationEquipments (
    reservation_id INT FOREIGN KEY REFERENCES dbo.Reservations(reservation_id) ON DELETE CASCADE,
    equipment_id INT FOREIGN KEY REFERENCES dbo.Equipment(equipment_id),
    quantity INT NOT NULL DEFAULT 1,
    unit_price DECIMAL(18, 2) NOT NULL,
    PRIMARY KEY (reservation_id, equipment_id)
);
GO

-- 13. Bảng ServiceSessions (Gói dịch vụ chọn trong đơn đặt phòng)
CREATE TABLE dbo.ServiceSessions (
    session_id INT IDENTITY(1,1) PRIMARY KEY,
    reservation_id INT NULL FOREIGN KEY REFERENCES dbo.Reservations(reservation_id) ON DELETE CASCADE,
    package_id INT NULL FOREIGN KEY REFERENCES dbo.ServicePackages(package_id),
    notes NVARCHAR(MAX) NULL
);
GO

-- 14. Bảng ReservationStatusHistory (Lịch sử thay đổi trạng thái đơn)
CREATE TABLE dbo.ReservationStatusHistory (
    history_id INT IDENTITY(1,1) PRIMARY KEY,
    reservation_id INT NULL FOREIGN KEY REFERENCES dbo.Reservations(reservation_id) ON DELETE CASCADE,
    changed_by INT NULL FOREIGN KEY REFERENCES dbo.Users(user_id),
    old_status VARCHAR(20) NULL,
    new_status VARCHAR(20) NULL,
    changed_at DATETIME DEFAULT GETDATE()
);
GO

-- 15. Bảng Payments (Thanh toán giao dịch)
CREATE TABLE dbo.Payments (
    payment_id INT IDENTITY(1,1) PRIMARY KEY,
    reservation_id INT NULL FOREIGN KEY REFERENCES dbo.Reservations(reservation_id),
    amount DECIMAL(18, 2) NOT NULL,
    payment_method VARCHAR(50) NOT NULL, -- VNPay, Momo, Cash, BankTransfer
    transaction_code VARCHAR(100) NULL,
    status VARCHAR(20) DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'SUCCESS', 'FAILED', 'REFUNDED')),
    created_at DATETIME DEFAULT GETDATE()
);
GO

-- 16. Bảng Reviews (Đánh giá Studio)
CREATE TABLE dbo.Reviews (
    review_id INT IDENTITY(1,1) PRIMARY KEY,
    studio_id INT NULL FOREIGN KEY REFERENCES dbo.Studios(studio_id) ON DELETE CASCADE,
    customer_id INT NULL FOREIGN KEY REFERENCES dbo.Users(user_id),
    rating INT NOT NULL CHECK (rating BETWEEN 1 AND 5),
    comment NVARCHAR(MAX) NULL,
    created_at DATETIME DEFAULT GETDATE()
);
GO

-- 17. Bảng CommunityPosts (Bài viết chia sẻ cộng đồng)
CREATE TABLE dbo.CommunityPosts (
    post_id INT IDENTITY(1,1) PRIMARY KEY,
    author_id INT NULL FOREIGN KEY REFERENCES dbo.Users(user_id) ON DELETE CASCADE,
    title NVARCHAR(200) NOT NULL,
    content NVARCHAR(MAX) NOT NULL,
    image_url NVARCHAR(500) NULL,
    created_at DATETIME DEFAULT GETDATE()
);
GO

-- 18. Bảng PostComments (Bình luận bài viết cộng đồng - Đã sửa lỗi Cascade)
CREATE TABLE dbo.PostComments (
    comment_id INT IDENTITY(1,1) PRIMARY KEY,
    post_id INT NULL FOREIGN KEY REFERENCES dbo.CommunityPosts(post_id) ON DELETE CASCADE,
    user_id INT NULL FOREIGN KEY REFERENCES dbo.Users(user_id), -- Đã lược bỏ ON DELETE CASCADE ở đây
    content NVARCHAR(MAX) NOT NULL,
    created_at DATETIME DEFAULT GETDATE()
);
GO
