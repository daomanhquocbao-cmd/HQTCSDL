IF DB_ID(N'FilmPhotographyPlatform') IS NULL
    CREATE DATABASE FilmPhotographyPlatform;
GO
USE FilmPhotographyPlatform;
GO
SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
GO

/* ---------- 1. Users (4 vai trò: ADMIN / EXPERT / PROVIDER / CUSTOMER) ---------- */
CREATE TABLE dbo.Users (
    user_id       INT IDENTITY(1,1) NOT NULL,
    username      VARCHAR(50)   NOT NULL,
    password_hash VARCHAR(255)  NOT NULL,
    email         VARCHAR(100)  NOT NULL,
    phone         VARCHAR(20)   NULL,
    full_name     NVARCHAR(100) NOT NULL,
    role          VARCHAR(20)   NOT NULL,
    status        VARCHAR(20)   NOT NULL CONSTRAINT DF_Users_status DEFAULT 'ACTIVE',  -- PENDING: chờ duyệt, SUSPENDED: bị khóa
    created_at    DATETIME      NOT NULL CONSTRAINT DF_Users_created DEFAULT GETDATE(),
    CONSTRAINT PK_Users PRIMARY KEY (user_id),
    CONSTRAINT UQ_Users_username UNIQUE (username),
    CONSTRAINT UQ_Users_email UNIQUE (email),
    CONSTRAINT CK_Users_role CHECK (role IN ('ADMIN','EXPERT','PROVIDER','CUSTOMER')),
    CONSTRAINT CK_Users_status CHECK (status IN ('ACTIVE','PENDING','SUSPENDED'))
);
GO

/* ---------- 2. Studios (cơ sở của nhà cung cấp) ---------- */
CREATE TABLE dbo.Studios (
    studio_id   INT IDENTITY(1,1) NOT NULL,
    provider_id INT           NOT NULL,
    name        NVARCHAR(100) NOT NULL,
    address     NVARCHAR(255) NOT NULL,
    city        NVARCHAR(100) NOT NULL,
    latitude    DECIMAL(9,6)  NULL,      -- phục vụ Google Maps
    longitude   DECIMAL(9,6)  NULL,
    description NVARCHAR(MAX) NULL,
    phone       VARCHAR(20)   NULL,
    open_time   TIME(0)       NOT NULL CONSTRAINT DF_Studios_open  DEFAULT '08:00',
    close_time  TIME(0)       NOT NULL CONSTRAINT DF_Studios_close DEFAULT '21:00',
    status      VARCHAR(20)   NOT NULL CONSTRAINT DF_Studios_status DEFAULT 'PENDING',  -- Admin duyệt
    created_at  DATETIME      NOT NULL CONSTRAINT DF_Studios_created DEFAULT GETDATE(),
    CONSTRAINT PK_Studios PRIMARY KEY (studio_id),
    CONSTRAINT FK_Studios_Provider FOREIGN KEY (provider_id) REFERENCES dbo.Users(user_id),
    CONSTRAINT CK_Studios_status CHECK (status IN ('PENDING','APPROVED','REJECTED','SUSPENDED')),
    CONSTRAINT CK_Studios_hours CHECK (close_time > open_time)
);
GO

/* ---------- 3. StudioImages ---------- */
CREATE TABLE dbo.StudioImages (
    image_id   INT IDENTITY(1,1) NOT NULL,
    studio_id  INT           NOT NULL,
    image_url  NVARCHAR(500) NOT NULL,
    is_primary BIT           NOT NULL CONSTRAINT DF_StudioImages_primary DEFAULT 0,
    created_at DATETIME      NOT NULL CONSTRAINT DF_StudioImages_created DEFAULT GETDATE(),
    CONSTRAINT PK_StudioImages PRIMARY KEY (image_id),
    CONSTRAINT FK_StudioImages_Studio FOREIGN KEY (studio_id)
        REFERENCES dbo.Studios(studio_id) ON DELETE CASCADE
);
GO

/* ---------- 4. Rooms (phòng chụp / phòng tối) ---------- */
CREATE TABLE dbo.Rooms (
    room_id        INT IDENTITY(1,1) NOT NULL,
    studio_id      INT           NOT NULL,
    name           NVARCHAR(100) NOT NULL,
    room_type      VARCHAR(20)   NOT NULL,
    capacity       INT           NOT NULL,
    area_sqm       DECIMAL(8,2)  NULL,            -- diện tích
    art_style      NVARCHAR(100) NULL,            -- phong cách
    lighting       NVARCHAR(200) NULL,            -- ánh sáng
    amenities      NVARCHAR(500) NULL,            -- tiện ích đi kèm
    price_per_hour DECIMAL(18,2) NOT NULL,
    description    NVARCHAR(MAX) NULL,
    status         VARCHAR(20)   NOT NULL CONSTRAINT DF_Rooms_status DEFAULT 'AVAILABLE',
    created_at     DATETIME      NOT NULL CONSTRAINT DF_Rooms_created DEFAULT GETDATE(),
    CONSTRAINT PK_Rooms PRIMARY KEY (room_id),
    CONSTRAINT FK_Rooms_Studio FOREIGN KEY (studio_id) REFERENCES dbo.Studios(studio_id),
    CONSTRAINT CK_Rooms_type CHECK (room_type IN ('STUDIO','DARKROOM')),
    CONSTRAINT CK_Rooms_capacity CHECK (capacity > 0),
    CONSTRAINT CK_Rooms_price CHECK (price_per_hour >= 0),
    CONSTRAINT CK_Rooms_status CHECK (status IN ('AVAILABLE','MAINTENANCE','INACTIVE'))
);
GO

/* ---------- 5. Equipment (thiết bị cho thuê + vật tư tiêu hao) ---------- */
CREATE TABLE dbo.Equipment (
    equipment_id          INT IDENTITY(1,1) NOT NULL,
    studio_id             INT           NOT NULL,
    name                  NVARCHAR(100) NOT NULL,
    equipment_type        VARCHAR(20)   NOT NULL,   -- REUSABLE: cho thuê lại nhiều lần | CONSUMABLE: dùng hết (hóa chất, giấy)
    category              VARCHAR(30)   NOT NULL CONSTRAINT DF_Equipment_cat DEFAULT 'OTHER',
    quantity              INT           NOT NULL,   -- số lượng đang sở hữu / tồn kho
    rental_price          DECIMAL(18,2) NOT NULL,   -- giá thuê (hoặc giá bán nếu CONSUMABLE) cho 1 đơn vị / 1 lượt
    next_maintenance_date DATE          NULL,       -- lịch bảo trì kế tiếp
    status                VARCHAR(20)   NOT NULL CONSTRAINT DF_Equipment_status DEFAULT 'GOOD',
    CONSTRAINT PK_Equipment PRIMARY KEY (equipment_id),
    CONSTRAINT FK_Equipment_Studio FOREIGN KEY (studio_id) REFERENCES dbo.Studios(studio_id),
    CONSTRAINT CK_Equipment_type CHECK (equipment_type IN ('REUSABLE','CONSUMABLE')),
    CONSTRAINT CK_Equipment_cat CHECK (category IN
        ('CAMERA','LENS','LIGHTING','TRIPOD','ENLARGER','SCANNER','CHEMICAL','PAPER','OTHER')),
    CONSTRAINT CK_Equipment_qty CHECK (quantity >= 0),
    CONSTRAINT CK_Equipment_price CHECK (rental_price >= 0),
    CONSTRAINT CK_Equipment_status CHECK (status IN ('GOOD','NEEDS_MAINTENANCE','UNDER_MAINTENANCE','BROKEN','RETIRED'))
);
GO

/* ---------- 6. EquipmentMaintenance (lịch sử + lịch bảo trì) ---------- */
CREATE TABLE dbo.EquipmentMaintenance (
    maintenance_id   INT IDENTITY(1,1) NOT NULL,
    equipment_id     INT           NOT NULL,
    maintenance_date DATETIME      NOT NULL CONSTRAINT DF_EqMaint_date DEFAULT GETDATE(),
    cost             DECIMAL(18,2) NOT NULL,
    description      NVARCHAR(MAX) NULL,
    status           VARCHAR(20)   NOT NULL CONSTRAINT DF_EqMaint_status DEFAULT 'DONE',
    CONSTRAINT PK_EquipmentMaintenance PRIMARY KEY (maintenance_id),
    CONSTRAINT FK_EqMaint_Equipment FOREIGN KEY (equipment_id)
        REFERENCES dbo.Equipment(equipment_id) ON DELETE CASCADE,
    CONSTRAINT CK_EqMaint_cost CHECK (cost >= 0),
    CONSTRAINT CK_EqMaint_status CHECK (status IN ('SCHEDULED','DONE','CANCELLED'))
);
GO

/* ---------- 7. ServicePackages ---------- */
CREATE TABLE dbo.ServicePackages (
    package_id     INT IDENTITY(1,1) NOT NULL,
    studio_id      INT           NOT NULL,
    name           NVARCHAR(100) NOT NULL,
    price          DECIMAL(18,2) NOT NULL,
    duration_hours DECIMAL(4,1)  NULL,
    room_type      VARCHAR(20)   NULL,        -- gói dành cho STUDIO hay DARKROOM (NULL = dùng được cho cả hai)
    instructor_id  INT           NULL,        -- chuyên gia hướng dẫn (role EXPERT), có thể không có
    description    NVARCHAR(MAX) NULL,
    is_active      BIT           NOT NULL CONSTRAINT DF_Pkg_active DEFAULT 1,
    created_at     DATETIME      NOT NULL CONSTRAINT DF_Pkg_created DEFAULT GETDATE(),
    CONSTRAINT PK_ServicePackages PRIMARY KEY (package_id),
    CONSTRAINT FK_Pkg_Studio FOREIGN KEY (studio_id) REFERENCES dbo.Studios(studio_id),
    CONSTRAINT FK_Pkg_Instructor FOREIGN KEY (instructor_id) REFERENCES dbo.Users(user_id),
    CONSTRAINT CK_Pkg_price CHECK (price >= 0),
    CONSTRAINT CK_Pkg_roomtype CHECK (room_type IS NULL OR room_type IN ('STUDIO','DARKROOM'))
);
GO

/* ---------- 8. PackageEquipment (N-N: gói <-> thiết bị) ---------- */
CREATE TABLE dbo.PackageEquipment (
    package_id        INT NOT NULL,
    equipment_id      INT NOT NULL,
    quantity_included INT NOT NULL CONSTRAINT DF_PkgEq_qty DEFAULT 1,
    CONSTRAINT PK_PackageEquipment PRIMARY KEY (package_id, equipment_id),
    CONSTRAINT FK_PkgEq_Package FOREIGN KEY (package_id)
        REFERENCES dbo.ServicePackages(package_id) ON DELETE CASCADE,
    CONSTRAINT FK_PkgEq_Equipment FOREIGN KEY (equipment_id) REFERENCES dbo.Equipment(equipment_id),
    CONSTRAINT CK_PkgEq_qty CHECK (quantity_included > 0)
);
GO

/* ---------- 9. Reservations (đơn đặt phòng) ---------- */
CREATE TABLE dbo.Reservations (
    reservation_id INT IDENTITY(1,1) NOT NULL,
    room_id        INT           NOT NULL,
    customer_id    INT           NOT NULL,
    start_time     DATETIME      NOT NULL,
    end_time       DATETIME      NOT NULL,
    total_amount   DECIMAL(18,2) NOT NULL,   -- = tiền phòng + thiết bị thuê thêm + gói (sp_RecalculateReservationTotal)
    customer_note  NVARCHAR(MAX) NULL,
    qr_code        VARCHAR(100)  NULL,       -- mã QR check-in, tạo khi đơn được CONFIRMED
    status         VARCHAR(20)   NOT NULL CONSTRAINT DF_Res_status DEFAULT 'PENDING',
    created_at     DATETIME      NOT NULL CONSTRAINT DF_Res_created DEFAULT GETDATE(),
    CONSTRAINT PK_Reservations PRIMARY KEY (reservation_id),
    CONSTRAINT FK_Res_Room FOREIGN KEY (room_id) REFERENCES dbo.Rooms(room_id),
    CONSTRAINT FK_Res_Customer FOREIGN KEY (customer_id) REFERENCES dbo.Users(user_id),
    CONSTRAINT CK_Res_time CHECK (end_time > start_time),
    CONSTRAINT CK_Res_amount CHECK (total_amount >= 0),
    CONSTRAINT CK_Res_status CHECK (status IN ('PENDING','CONFIRMED','IN_USE','COMPLETED','CANCELLED'))
);
GO

/* ---------- 10. ReservationEquipments (thiết bị thuê thêm trong đơn) ---------- */
CREATE TABLE dbo.ReservationEquipments (
    reservation_id INT           NOT NULL,
    equipment_id   INT           NOT NULL,
    quantity       INT           NOT NULL CONSTRAINT DF_ResEq_qty DEFAULT 1,
    unit_price     DECIMAL(18,2) NOT NULL,   -- lưu lại giá tại thời điểm đặt (giá sau này đổi cũng không ảnh hưởng đơn cũ)
    CONSTRAINT PK_ReservationEquipments PRIMARY KEY (reservation_id, equipment_id),
    CONSTRAINT FK_ResEq_Reservation FOREIGN KEY (reservation_id)
        REFERENCES dbo.Reservations(reservation_id) ON DELETE CASCADE,
    CONSTRAINT FK_ResEq_Equipment FOREIGN KEY (equipment_id) REFERENCES dbo.Equipment(equipment_id),
    CONSTRAINT CK_ResEq_qty CHECK (quantity > 0),
    CONSTRAINT CK_ResEq_price CHECK (unit_price >= 0)
);
GO

/* ---------- 11. ReservationPackages (gói dịch vụ chọn trong đơn) ---------- */
CREATE TABLE dbo.ReservationPackages (
    reservation_id INT           NOT NULL,
    package_id     INT           NOT NULL,
    price          DECIMAL(18,2) NOT NULL,   -- lưu lại giá gói tại thời điểm đặt
    notes          NVARCHAR(MAX) NULL,
    CONSTRAINT PK_ReservationPackages PRIMARY KEY (reservation_id, package_id),
    CONSTRAINT FK_ResPkg_Reservation FOREIGN KEY (reservation_id)
        REFERENCES dbo.Reservations(reservation_id) ON DELETE CASCADE,
    CONSTRAINT FK_ResPkg_Package FOREIGN KEY (package_id) REFERENCES dbo.ServicePackages(package_id),
    CONSTRAINT CK_ResPkg_price CHECK (price >= 0)
);
GO

/* ---------- 12. ServiceSessions (phiên sử dụng thực tế: check-in / check-out) ---------- */
CREATE TABLE dbo.ServiceSessions (
    session_id     INT IDENTITY(1,1) NOT NULL,
    reservation_id INT           NOT NULL,
    checkin_time   DATETIME      NOT NULL,
    checkout_time  DATETIME      NULL,
    actual_minutes AS DATEDIFF(MINUTE, checkin_time, checkout_time) PERSISTED,   -- cột tính toán
    status         VARCHAR(20)   NOT NULL CONSTRAINT DF_Sess_status DEFAULT 'IN_USE',
    notes          NVARCHAR(MAX) NULL,
    CONSTRAINT PK_ServiceSessions PRIMARY KEY (session_id),
    CONSTRAINT UQ_Sess_Reservation UNIQUE (reservation_id),    -- 1 đơn = 1 phiên
    CONSTRAINT FK_Sess_Reservation FOREIGN KEY (reservation_id)
        REFERENCES dbo.Reservations(reservation_id) ON DELETE CASCADE,
    CONSTRAINT CK_Sess_status CHECK (status IN ('IN_USE','CHECKED_OUT')),
    CONSTRAINT CK_Sess_time CHECK (checkout_time IS NULL OR checkout_time >= checkin_time)
);
GO

/* ---------- 13. ReservationStatusHistory (trigger tự ghi) ---------- */
CREATE TABLE dbo.ReservationStatusHistory (
    history_id     INT IDENTITY(1,1) NOT NULL,
    reservation_id INT         NOT NULL,
    changed_by     INT         NULL,          -- NULL = hệ thống
    old_status     VARCHAR(20) NULL,
    new_status     VARCHAR(20) NOT NULL,
    changed_at     DATETIME    NOT NULL CONSTRAINT DF_ResHist_at DEFAULT GETDATE(),
    CONSTRAINT PK_ResStatusHistory PRIMARY KEY (history_id),
    CONSTRAINT FK_ResHist_Reservation FOREIGN KEY (reservation_id)
        REFERENCES dbo.Reservations(reservation_id) ON DELETE CASCADE,
    CONSTRAINT FK_ResHist_User FOREIGN KEY (changed_by) REFERENCES dbo.Users(user_id)
);
GO

/* ---------- 14. Payments ---------- */
CREATE TABLE dbo.Payments (
    payment_id       INT IDENTITY(1,1) NOT NULL,
    reservation_id   INT           NOT NULL,
    amount           DECIMAL(18,2) NOT NULL,
    payment_method   VARCHAR(20)   NOT NULL,
    transaction_code VARCHAR(100)  NULL,
    status           VARCHAR(20)   NOT NULL CONSTRAINT DF_Pay_status DEFAULT 'PENDING',
    paid_at          DATETIME      NULL,
    created_at       DATETIME      NOT NULL CONSTRAINT DF_Pay_created DEFAULT GETDATE(),
    CONSTRAINT PK_Payments PRIMARY KEY (payment_id),
    CONSTRAINT FK_Pay_Reservation FOREIGN KEY (reservation_id) REFERENCES dbo.Reservations(reservation_id),
    CONSTRAINT CK_Pay_amount CHECK (amount > 0),
    CONSTRAINT CK_Pay_method CHECK (payment_method IN ('VNPAY','MOMO','STRIPE','CASH','BANK_TRANSFER')),
    CONSTRAINT CK_Pay_status CHECK (status IN ('PENDING','SUCCESS','FAILED','REFUNDED'))
);
GO

/* ---------- 15. Reviews (mỗi đơn COMPLETED được đánh giá 1 lần) ---------- */
CREATE TABLE dbo.Reviews (
    review_id      INT IDENTITY(1,1) NOT NULL,
    reservation_id INT           NOT NULL,
    studio_id      INT           NOT NULL,   -- phi chuẩn hóa có chủ đích để tính điểm studio nhanh (trigger kiểm tra khớp)
    customer_id    INT           NOT NULL,
    rating         INT           NOT NULL,
    comment        NVARCHAR(MAX) NULL,
    created_at     DATETIME      NOT NULL CONSTRAINT DF_Rev_created DEFAULT GETDATE(),
    CONSTRAINT PK_Reviews PRIMARY KEY (review_id),
    CONSTRAINT UQ_Reviews_Reservation UNIQUE (reservation_id),
    CONSTRAINT FK_Rev_Reservation FOREIGN KEY (reservation_id) REFERENCES dbo.Reservations(reservation_id),
    CONSTRAINT FK_Rev_Studio FOREIGN KEY (studio_id) REFERENCES dbo.Studios(studio_id),
    CONSTRAINT FK_Rev_Customer FOREIGN KEY (customer_id) REFERENCES dbo.Users(user_id),
    CONSTRAINT CK_Rev_rating CHECK (rating BETWEEN 1 AND 5)
);
GO

/* ---------- 16. Workshops ---------- */
CREATE TABLE dbo.Workshops (
    workshop_id INT IDENTITY(1,1) NOT NULL,
    expert_id   INT           NOT NULL,
    studio_id   INT           NULL,         -- địa điểm tổ chức (NULL = online)
    title       NVARCHAR(200) NOT NULL,
    description NVARCHAR(MAX) NULL,
    capacity    INT           NOT NULL,
    fee         DECIMAL(18,2) NOT NULL CONSTRAINT DF_Ws_fee DEFAULT 0,
    start_time  DATETIME      NOT NULL,
    end_time    DATETIME      NOT NULL,
    status      VARCHAR(20)   NOT NULL CONSTRAINT DF_Ws_status DEFAULT 'OPEN',
    created_at  DATETIME      NOT NULL CONSTRAINT DF_Ws_created DEFAULT GETDATE(),
    CONSTRAINT PK_Workshops PRIMARY KEY (workshop_id),
    CONSTRAINT FK_Ws_Expert FOREIGN KEY (expert_id) REFERENCES dbo.Users(user_id),
    CONSTRAINT FK_Ws_Studio FOREIGN KEY (studio_id) REFERENCES dbo.Studios(studio_id),
    CONSTRAINT CK_Ws_capacity CHECK (capacity > 0),
    CONSTRAINT CK_Ws_fee CHECK (fee >= 0),
    CONSTRAINT CK_Ws_time CHECK (end_time > start_time),
    CONSTRAINT CK_Ws_status CHECK (status IN ('OPEN','CLOSED','CANCELLED','COMPLETED'))
);
GO

/* ---------- 17. WorkshopRegistrations ---------- */
CREATE TABLE dbo.WorkshopRegistrations (
    registration_id INT IDENTITY(1,1) NOT NULL,
    workshop_id     INT      NOT NULL,
    customer_id     INT      NOT NULL,
    registered_at   DATETIME NOT NULL CONSTRAINT DF_WsReg_at DEFAULT GETDATE(),
    CONSTRAINT PK_WorkshopRegistrations PRIMARY KEY (registration_id),
    CONSTRAINT UQ_Workshop_Customer UNIQUE (workshop_id, customer_id),   -- 1 khách đăng ký 1 workshop tối đa 1 lần
    CONSTRAINT FK_WsReg_Workshop FOREIGN KEY (workshop_id)
        REFERENCES dbo.Workshops(workshop_id) ON DELETE CASCADE,
    CONSTRAINT FK_WsReg_Customer FOREIGN KEY (customer_id) REFERENCES dbo.Users(user_id)
);
GO

/* ---------- 18. CommunityPosts ---------- */
CREATE TABLE dbo.CommunityPosts (
    post_id    INT IDENTITY(1,1) NOT NULL,
    author_id  INT           NOT NULL,
    post_type  VARCHAR(30)   NOT NULL CONSTRAINT DF_Post_type DEFAULT 'DISCUSSION',
    title      NVARCHAR(200) NOT NULL,
    content    NVARCHAR(MAX) NOT NULL,
    image_url  NVARCHAR(500) NULL,
    created_at DATETIME      NOT NULL CONSTRAINT DF_Post_created DEFAULT GETDATE(),
    CONSTRAINT PK_CommunityPosts PRIMARY KEY (post_id),
    CONSTRAINT FK_Post_Author FOREIGN KEY (author_id) REFERENCES dbo.Users(user_id),
    CONSTRAINT CK_Post_type CHECK (post_type IN
        ('ARTICLE','TUTORIAL','EQUIPMENT_REVIEW','DISCUSSION','WORKSHOP_ANNOUNCEMENT'))
);
GO

/* ---------- 19. PostComments ---------- */
CREATE TABLE dbo.PostComments (
    comment_id INT IDENTITY(1,1) NOT NULL,
    post_id    INT           NOT NULL,
    user_id    INT           NOT NULL,
    content    NVARCHAR(MAX) NOT NULL,
    created_at DATETIME      NOT NULL CONSTRAINT DF_Cmt_created DEFAULT GETDATE(),
    CONSTRAINT PK_PostComments PRIMARY KEY (comment_id),
    CONSTRAINT FK_Cmt_Post FOREIGN KEY (post_id)
        REFERENCES dbo.CommunityPosts(post_id) ON DELETE CASCADE,
    CONSTRAINT FK_Cmt_User FOREIGN KEY (user_id) REFERENCES dbo.Users(user_id)
);
GO

/* ---------- 20. Disputes (khiếu nại - Admin xử lý) ---------- */
CREATE TABLE dbo.Disputes (
    dispute_id     INT IDENTITY(1,1) NOT NULL,
    reservation_id INT           NOT NULL,
    raised_by      INT           NOT NULL,
    reason         NVARCHAR(MAX) NOT NULL,
    status         VARCHAR(20)   NOT NULL CONSTRAINT DF_Disp_status DEFAULT 'OPEN',
    resolution     NVARCHAR(MAX) NULL,
    resolved_by    INT           NULL,
    created_at     DATETIME      NOT NULL CONSTRAINT DF_Disp_created DEFAULT GETDATE(),
    resolved_at    DATETIME      NULL,
    CONSTRAINT PK_Disputes PRIMARY KEY (dispute_id),
    CONSTRAINT FK_Disp_Reservation FOREIGN KEY (reservation_id) REFERENCES dbo.Reservations(reservation_id),
    CONSTRAINT FK_Disp_RaisedBy FOREIGN KEY (raised_by) REFERENCES dbo.Users(user_id),
    CONSTRAINT FK_Disp_ResolvedBy FOREIGN KEY (resolved_by) REFERENCES dbo.Users(user_id),
    CONSTRAINT CK_Disp_status CHECK (status IN ('OPEN','IN_REVIEW','RESOLVED','REJECTED'))
);
GO

/* =====================================================================
   INDEXES - phục vụ tìm phòng, chống trùng lịch, báo cáo
   ===================================================================== */
CREATE INDEX IX_Res_Room_Time   ON dbo.Reservations(room_id, start_time, end_time) INCLUDE (status);  -- kiểm tra trùng lịch
CREATE INDEX IX_Res_Customer    ON dbo.Reservations(customer_id, start_time DESC);                     -- lịch sử khách
CREATE UNIQUE INDEX UX_Res_QR   ON dbo.Reservations(qr_code) WHERE qr_code IS NOT NULL;               -- mã QR không trùng
CREATE INDEX IX_Pay_Reservation ON dbo.Payments(reservation_id, status) INCLUDE (amount);
CREATE UNIQUE INDEX UX_Pay_Txn  ON dbo.Payments(transaction_code) WHERE transaction_code IS NOT NULL; -- chống trùng giao dịch
CREATE INDEX IX_Rooms_Search    ON dbo.Rooms(room_type, status) INCLUDE (price_per_hour, capacity);
CREATE INDEX IX_Studios_Search  ON dbo.Studios(status, city);
CREATE INDEX IX_Equipment_Studio ON dbo.Equipment(studio_id, status);
CREATE INDEX IX_Reviews_Studio  ON dbo.Reviews(studio_id) INCLUDE (rating);
GO
PRINT N'=== Đã tạo xong 20 bảng + index ===';
GO
