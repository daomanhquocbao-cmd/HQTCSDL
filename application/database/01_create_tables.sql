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
