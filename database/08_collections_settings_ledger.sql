/* =====================================================================
   08_collections_settings_ledger.sql  -  Bổ sung cho vai trò KHÁCH HÀNG và ADMIN
   ---------------------------------------------------------------------
   - Bộ sưu tập ảnh số của khách (PhotoCollections, Photos)       -> "Manage digital photo collections"
   - Cấu hình nền tảng / dịch vụ AI do admin bật tắt (SystemSettings) -> "Manage AI services and platform configurations"
   - Sổ giao dịch cho admin theo dõi thanh toán (vw_PaymentLedger)   -> "Monitor transactions and payments"
   - Hoàn tiền một giao dịch (sp_RefundPayment)                      -> xử lý khiếu nại / hoàn tiền
   Chạy SAU 01, 02, 03, 06_provider_additions, 07. Có thể chạy lại nhiều lần (idempotent).
   ===================================================================== */
USE FilmPhotographyPlatform;
GO

/* ---------- 1. Bộ sưu tập ảnh của khách ---------- */
IF OBJECT_ID(N'dbo.PhotoCollections', N'U') IS NULL
CREATE TABLE dbo.PhotoCollections (
    collection_id INT IDENTITY(1,1) NOT NULL,
    owner_id      INT           NOT NULL,
    name          NVARCHAR(100) NOT NULL,
    description   NVARCHAR(500) NULL,
    created_at    DATETIME      NOT NULL CONSTRAINT DF_PhotoCol_created DEFAULT GETDATE(),
    CONSTRAINT PK_PhotoCollections PRIMARY KEY (collection_id),
    CONSTRAINT FK_PhotoCol_Owner FOREIGN KEY (owner_id) REFERENCES dbo.Users(user_id),
    CONSTRAINT UQ_PhotoCol_Owner_Name UNIQUE (owner_id, name)      -- mỗi khách không có 2 bộ sưu tập trùng tên
);
GO

-- Ảnh nằm trong một bộ sưu tập. File thật lưu trên đĩa (backend/uploads), CSDL chỉ giữ đường dẫn.
-- kind: ORIGINAL = ảnh gốc khách tải lên | RESTORED = ảnh đã phục hồi / tăng chất lượng
IF OBJECT_ID(N'dbo.Photos', N'U') IS NULL
CREATE TABLE dbo.Photos (
    photo_id      INT IDENTITY(1,1) NOT NULL,
    collection_id INT           NOT NULL,
    file_path     VARCHAR(300)  NOT NULL,
    caption       NVARCHAR(200) NULL,
    kind          VARCHAR(10)   NOT NULL CONSTRAINT DF_Photo_kind DEFAULT 'ORIGINAL',
    size_bytes    INT           NOT NULL CONSTRAINT DF_Photo_size DEFAULT 0,
    created_at    DATETIME      NOT NULL CONSTRAINT DF_Photo_created DEFAULT GETDATE(),
    CONSTRAINT PK_Photos PRIMARY KEY (photo_id),
    CONSTRAINT FK_Photo_Collection FOREIGN KEY (collection_id)
        REFERENCES dbo.PhotoCollections(collection_id) ON DELETE CASCADE,   -- xóa bộ sưu tập thì xóa ảnh
    CONSTRAINT CK_Photo_kind CHECK (kind IN ('ORIGINAL', 'RESTORED')),
    CONSTRAINT CK_Photo_size CHECK (size_bytes >= 0)
);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_Photos_Collection' AND object_id = OBJECT_ID(N'dbo.Photos'))
    CREATE INDEX IX_Photos_Collection ON dbo.Photos(collection_id, created_at DESC);
GO

/* ---------- 2. Cấu hình nền tảng (key - value) ---------- */
IF OBJECT_ID(N'dbo.SystemSettings', N'U') IS NULL
CREATE TABLE dbo.SystemSettings (
    setting_key   VARCHAR(60)    NOT NULL,
    setting_value NVARCHAR(200)  NOT NULL,
    value_type    VARCHAR(10)    NOT NULL CONSTRAINT DF_Setting_type DEFAULT 'STRING',
    description   NVARCHAR(300)  NULL,
    updated_by    INT            NULL,
    updated_at    DATETIME       NOT NULL CONSTRAINT DF_Setting_updated DEFAULT GETDATE(),
    CONSTRAINT PK_SystemSettings PRIMARY KEY (setting_key),
    CONSTRAINT FK_Setting_User FOREIGN KEY (updated_by) REFERENCES dbo.Users(user_id),
    CONSTRAINT CK_Setting_type CHECK (value_type IN ('BOOL', 'INT', 'NUMBER', 'STRING'))
);
GO

-- Giá trị mặc định (chỉ thêm khi chưa có, không ghi đè cấu hình admin đã đổi)
INSERT INTO dbo.SystemSettings (setting_key, setting_value, value_type, description)
SELECT v.k, v.v, v.t, v.d
FROM (VALUES
    ('ai.recommendations.enabled', '1',  'BOOL',   N'Bật gợi ý phòng cá nhân hóa cho khách'),
    ('ai.assistant.enabled',       '1',  'BOOL',   N'Bật trợ lý AI hỏi đáp / tìm phòng bằng câu hỏi tự nhiên'),
    ('ai.knowledge_search.enabled','1',  'BOOL',   N'Bật tìm kiếm tri thức trong cộng đồng'),
    ('ai.pricing_suggestions.enabled','1','BOOL',  N'Cho nhà cung cấp xem gợi ý giá động'),
    ('pricing.high_occupancy_pct', '75', 'INT',    N'Lấp đầy từ mức này trở lên thì gợi ý tăng giá (%)'),
    ('pricing.low_occupancy_pct',  '20', 'INT',    N'Lấp đầy từ mức này trở xuống thì gợi ý giảm giá (%)'),
    ('booking.max_hours_per_booking','12','INT',   N'Số giờ tối đa cho một đơn đặt phòng'),
    ('platform.maintenance_mode',  '0',  'BOOL',   N'Bật để tạm ngừng nhận đơn đặt mới (bảo trì hệ thống)')
) AS v(k, v, t, d)
WHERE NOT EXISTS (SELECT 1 FROM dbo.SystemSettings s WHERE s.setting_key = v.k);
GO

/* ---------- 3. Sổ giao dịch: mỗi dòng = 1 lần thanh toán + đơn, khách, studio ---------- */
CREATE OR ALTER VIEW dbo.vw_PaymentLedger
AS
SELECT p.payment_id, p.reservation_id, p.amount, p.payment_method, p.status,
       p.transaction_code, p.paid_at, p.created_at,
       u.user_id AS customer_id, u.full_name AS customer_name,
       s.studio_id, s.name AS studio_name, s.provider_id,
       r.total_amount AS reservation_total, r.status AS reservation_status
FROM dbo.Payments p
JOIN dbo.Reservations r ON r.reservation_id = p.reservation_id
JOIN dbo.Users u        ON u.user_id = r.customer_id
JOIN dbo.Rooms rm       ON rm.room_id = r.room_id
JOIN dbo.Studios s      ON s.studio_id = rm.studio_id;
GO

/* ---------- 4. Hoàn tiền: chỉ admin, chỉ giao dịch SUCCESS ---------- */
CREATE OR ALTER PROCEDURE dbo.sp_RefundPayment
    @payment_id INT,
    @actor_id   INT
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        IF NOT EXISTS (SELECT 1 FROM dbo.Users WHERE user_id = @actor_id AND role = 'ADMIN' AND status = 'ACTIVE')
            THROW 52001, N'Chỉ quản trị viên mới được hoàn tiền.', 1;

        BEGIN TRANSACTION;
        DECLARE @status VARCHAR(20);
        SELECT @status = status FROM dbo.Payments WITH (UPDLOCK, HOLDLOCK) WHERE payment_id = @payment_id;
        IF @status IS NULL            THROW 52002, N'Không tìm thấy giao dịch.', 1;
        IF @status <> 'SUCCESS'       THROW 52003, N'Chỉ hoàn tiền được giao dịch đã thành công.', 1;

        UPDATE dbo.Payments SET status = 'REFUNDED' WHERE payment_id = @payment_id;
        COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;
GO

/* ---------- 5. Dữ liệu mẫu: 1 bộ sưu tập rỗng cho khách đầu tiên (nếu có) ---------- */
INSERT INTO dbo.PhotoCollections (owner_id, name, description)
SELECT TOP 1 u.user_id, N'Ảnh phim của tôi', N'Bộ sưu tập mặc định'
FROM dbo.Users u
WHERE u.role = 'CUSTOMER'
  AND NOT EXISTS (SELECT 1 FROM dbo.PhotoCollections c WHERE c.owner_id = u.user_id)
ORDER BY u.user_id;
GO

PRINT N'08_collections_settings_ledger.sql: xong.';
GO
