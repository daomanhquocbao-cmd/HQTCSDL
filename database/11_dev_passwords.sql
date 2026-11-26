/* 11 - CHỈ DÙNG TRÊN MÁY THỬ: đặt mật khẩu Test@1234 cho các tài khoản mẫu của 02_seed_data.sql.
   Chỉ đổi những tài khoản còn mật khẩu giữ chỗ nên không đụng tài khoản đã đăng ký thật.
   Không chạy file này khi nộp bài hoặc triển khai. */
USE FilmPhotographyPlatform;
GO
UPDATE dbo.Users
SET password_hash = N'pbkdf2_sha256$120000$f65858832edae0c2100dd3d63ffa385d$d592d06cf64df637faa36782ed06f51b1dffe6f4bbed000e28f3e0249d8d5a0a'
WHERE password_hash LIKE '%SEED.PLACEHOLDER%';
SELECT @@ROWCOUNT AS tai_khoan_da_cap_nhat;
GO
