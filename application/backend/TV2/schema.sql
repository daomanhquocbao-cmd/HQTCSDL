-- SQL Server schema cho FilmPhotographyPlatform
IF DB_ID('FilmPhotographyPlatform') IS NULL CREATE DATABASE FilmPhotographyPlatform;
GO
USE FilmPhotographyPlatform;
GO

IF OBJECT_ID('dbo.Users') IS NULL
CREATE TABLE Users (
    user_id   INT IDENTITY(1,1) PRIMARY KEY,
    full_name NVARCHAR(100) NOT NULL,
    email     NVARCHAR(150) NOT NULL UNIQUE,
    role      VARCHAR(20)   NOT NULL DEFAULT 'customer'
);

IF OBJECT_ID('dbo.Rooms') IS NULL
CREATE TABLE Rooms (
    room_id   INT IDENTITY(1,1) PRIMARY KEY,
    name      NVARCHAR(100) NOT NULL,
    is_active BIT NOT NULL DEFAULT 1
);

IF OBJECT_ID('dbo.Bookings') IS NULL
CREATE TABLE Bookings (
    booking_id INT IDENTITY(1,1) PRIMARY KEY,
    user_id    INT NOT NULL REFERENCES Users(user_id),
    room_id    INT NOT NULL REFERENCES Rooms(room_id),
    start_time DATETIME2 NOT NULL,
    end_time   DATETIME2 NOT NULL,
    status     VARCHAR(20) NOT NULL DEFAULT 'pending'
               CHECK (status IN ('pending','confirmed','cancelled')),
    note       NVARCHAR(500) NULL,
    CHECK (end_time > start_time)
);
GO
