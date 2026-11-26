/* 13 - Chia sẻ bộ sưu tập ảnh bằng liên kết, hoa hồng nền tảng, chỉ mục bổ sung.
   Chạy sau 08 và 10. Chạy lại nhiều lần vẫn an toàn. */
USE FilmPhotographyPlatform;
GO
-- 1) Chia sẻ: có share_token thì ai có liên kết cũng xem được (chỉ xem), bỏ token là thu hồi
IF COL_LENGTH('dbo.PhotoCollections', 'share_token') IS NULL
    ALTER TABLE dbo.PhotoCollections ADD share_token VARCHAR(40) NULL;
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'UX_PhotoCol_Share' AND object_id = OBJECT_ID('dbo.PhotoCollections'))
    CREATE UNIQUE INDEX UX_PhotoCol_Share ON dbo.PhotoCollections(share_token) WHERE share_token IS NOT NULL;
GO
-- 2) Hoa hồng nền tảng (% trên doanh thu đã thu), Admin chỉnh được ở màn hình Cấu hình
INSERT INTO dbo.SystemSettings (setting_key, setting_value, value_type, description)
SELECT 'platform.commission_percent', '10', 'NUMBER', N'Hoa hồng nền tảng (% doanh thu đã thu, dùng trong báo cáo Admin)'
WHERE NOT EXISTS (SELECT 1 FROM dbo.SystemSettings WHERE setting_key = 'platform.commission_percent');
GO
-- 3) Chỉ mục cho các truy vấn cộng đồng, workshop, khiếu nại, lọc người dùng theo vai trò
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_Post_Type_Created' AND object_id = OBJECT_ID('dbo.CommunityPosts'))
    CREATE INDEX IX_Post_Type_Created ON dbo.CommunityPosts(post_type, created_at DESC);
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_Cmt_Post' AND object_id = OBJECT_ID('dbo.PostComments'))
    CREATE INDEX IX_Cmt_Post ON dbo.PostComments(post_id, created_at);
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_Ws_Start' AND object_id = OBJECT_ID('dbo.Workshops'))
    CREATE INDEX IX_Ws_Start ON dbo.Workshops(start_time, status);
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_Disp_Status' AND object_id = OBJECT_ID('dbo.Disputes'))
    CREATE INDEX IX_Disp_Status ON dbo.Disputes(status, created_at DESC);
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_Users_Role_Status' AND object_id = OBJECT_ID('dbo.Users'))
    CREATE INDEX IX_Users_Role_Status ON dbo.Users(role, status);
GO
