/* 12 - CHỈ DÙNG TRÊN MÁY THỬ: mật khẩu tài khoản mẫu = 3 chữ đầu của tên đăng nhập (viết hoa chữ đầu) + @1234.
   admin -> Adm@1234 | expert1..3 -> Exp@1234 | provider1..4 -> Pro@1234 | customer001.. -> Cus@1234
   Chỉ đổi các tài khoản mẫu theo tên; tài khoản tự đăng ký không bị đụng. Chạy lại được nhiều lần.
   Không chạy khi nộp bài hoặc triển khai thật. */
USE FilmPhotographyPlatform;
GO
UPDATE dbo.Users SET password_hash = N'pbkdf2_sha256$120000$f3d670f7dabc9f861b75c62ed6b4e4d6$d9f9ac10bbbc5724766719658c7fb783086ac6cc7e5e3cddc936a49e29f3d130' WHERE username = N'admin';
UPDATE dbo.Users SET password_hash = N'pbkdf2_sha256$120000$ebc73f6d7a3df098799fdf522d5b835f$3f2c2f8d68865e2925da811c814a519139154f7f8b4df6b55c1589037ef9c6aa' WHERE username LIKE N'expert[0-9]%';
UPDATE dbo.Users SET password_hash = N'pbkdf2_sha256$120000$7f131419473eed8828fae8d18943650b$82a6fc10661aecde69c0c3b3644351c375f2c2b9f5ee2ca08a05eef87b61bf16' WHERE username LIKE N'provider[0-9]%';
UPDATE dbo.Users SET password_hash = N'pbkdf2_sha256$120000$5361fecdcf339ad5a0c2691b82509997$bd94f8ab1af9d9605e4da9268f461fb2dbc419d90bc0cc4e34589bd4e4e83509' WHERE username LIKE N'customer[0-9]%';
GO
SELECT username, role FROM dbo.Users WHERE username = N'admin' OR username LIKE N'expert[0-9]%' OR username LIKE N'provider[0-9]%' OR username LIKE N'customer[0-9]%' ORDER BY role, username;
GO
