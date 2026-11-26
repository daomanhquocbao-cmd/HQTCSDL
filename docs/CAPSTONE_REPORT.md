# Báo cáo đồ án: Nền tảng kết nối cộng đồng nhiếp ảnh phim với dịch vụ phòng tối và phòng chụp

> Bản khung có nội dung. Các mục đánh dấu **[ĐIỀN]** cần nhóm bổ sung số liệu thật sau khi chạy trên SQL Server (không tự bịa số).

## Chương 1. Giới thiệu
**1.1 Bối cảnh.** Nhiếp ảnh phim phát triển trở lại; tài nguyên (phòng tối, studio, thiết bị) phân tán, đặt chỗ thủ công qua tin nhắn, nhà cung cấp quản lý bằng bảng tính nên xung đột lịch và khó phân tích hiệu quả.
**1.2 Mục tiêu.** Xây dựng nền tảng đa phía kết nối khách, nhà cung cấp, chuyên gia, quản trị; đặt chỗ an toàn khi đồng thời; hỗ trợ AI (gợi ý, dự báo, giá động, tối ưu phân bổ, phục hồi ảnh, trợ lý, tìm kiếm ngữ nghĩa).
**1.3 Phạm vi.** Xem bảng đối chiếu ở Chương 6.
**1.4 Phân công.** Thành viên 1: **[ĐIỀN]**. (Danh sách nhóm ở `README.md`.)

## Chương 2. Phân tích yêu cầu
- 5 vai trò: Customer, Provider, Expert, Admin, AI Assistant (chi tiết trong đề tài).
- 6 luồng nghiệp vụ: (1) quản lý không gian, (2) tài nguyên và thiết bị, (3) đặt chỗ và phân bổ, (4) phiên dịch vụ (check-in/out), (5) gói dịch vụ, (6) cộng đồng tri thức.
- Phi chức năng: phản hồi < 3 giây, đặt chỗ đồng thời an toàn, JWT + OAuth 2.0 + RBAC, kiến trúc mô-đun, sao lưu và phục hồi, dễ mở rộng.
- Sơ đồ use case, sơ đồ hoạt động đặt phòng: **[ĐIỀN: vẽ bằng draw.io/PlantUML từ các luồng trong `docs/USER_MANUAL.md`]**.

## Chương 3. Thiết kế hệ thống
- **3.1 Kiến trúc**: xem `docs/TECHNICAL.md` mục 1.
- **3.2 Thiết kế CSDL**: 26 bảng; ERD **[ĐIỀN: xuất từ SSMS Database Diagram]**; chuẩn hóa 3NF (giá lưu lại tại thời điểm đặt ở `ReservationEquipments.unit_price`, `ReservationPackages.price` là phi chuẩn hóa có chủ đích để đơn cũ không đổi khi giá đổi).
- **3.3 Stored procedure, trigger, view, index**: danh sách ở `docs/TECHNICAL.md` mục 2; truy vấn nghiệp vụ mẫu ở `04_business_queries.sql`.
- **3.4 API**: `docs/API.md`, `docs/PROVIDER_API.md`, Swagger `/docs`.
- **3.5 Giao diện**: web (customer, provider, expert, admin) và app Flutter.

## Chương 4. Hiện thực
**4.1 Đặt chỗ đồng thời an toàn.** `sp_CreateReservation` kiểm tra giờ mở cửa, trạng thái phòng, trùng lịch phòng và đủ thiết bị trong một transaction với `UPDLOCK, HOLDLOCK`. `concurrency_test.py` cho N luồng đặt cùng khung giờ: kết quả **[ĐIỀN: số luồng, số thành công = 1]**.
**4.2 Thanh toán và hoàn tiền.** `sp_ProcessPayment` khóa đơn, chặn tổng thanh toán vượt tổng tiền; `sp_RefundPayment`; VNPay sandbox ký HMAC-SHA512, ghi nhận idempotent.
**4.3 AI.** Bảng ở `docs/TECHNICAL.md` mục 4 và nghiên cứu ở `docs/RBL.md`.
**4.4 Bảo mật.** JWT, RBAC, kiểm tra sở hữu, tham số hóa truy vấn, Google OAuth.
**4.5 Sao lưu và phục hồi.** `09_backup_recovery.sql`; kịch bản thử: sao lưu FULL, tạo dữ liệu, sao lưu LOG, "làm hỏng", khôi phục đến thời điểm **[ĐIỀN: ảnh chụp kết quả]**.

## Chương 5. Kiểm thử và đánh giá
| Hạng mục | Cách đo | Kết quả |
|---|---|---|
| Kiểm thử đơn vị | `pytest` | 100 test đạt (cursor giả) |
| Đặt đồng thời | `scripts/concurrency_test.py` | **[ĐIỀN]** |
| Thời gian phản hồi | `scripts/measure_latency.py --n 30` trên dữ liệu `05_seed_bulk.sql` | **[ĐIỀN: trung bình/p95, yêu cầu < 3 s]** |
| Hiệu năng truy vấn | `06_performance_demo.sql` (trước/sau chỉ mục) | **[ĐIỀN]** |
| Kiểm thử chức năng web | Thao tác theo `USER_MANUAL.md` | **[ĐIỀN: bảng pass/fail]** |
| Chất lượng AI | Dự báo: MAE trên backtest; tìm kiếm: MRR; ảnh: đánh giá trực quan | **[ĐIỀN]** |

## Chương 6. Đối chiếu với đề tài
| Yêu cầu đề tài | Tình trạng | Ghi chú |
|---|---|---|
| Web portal provider, web admin | Hoàn thành | HTML/JS thay cho React |
| Cộng đồng tri thức, workshop | Hoàn thành | |
| Mô-đun AI (gợi ý, dự báo, giá động, tối ưu phân bổ, trợ lý, tìm kiếm, phục hồi ảnh) | Hoàn thành ở mức thuật toán | Không dùng LLM/học sâu; hướng mở rộng ở RBL |
| JWT + RBAC | Hoàn thành | |
| OAuth 2.0 | Google | Cần Client ID |
| Thanh toán trực tuyến | VNPay sandbox | MoMo, Stripe chưa |
| App di động | Flutter, chưa kiểm thử trên thiết bị | Xem `mobile/README.md` |
| Đặt chỗ đồng thời | Hoàn thành | |
| Sao lưu và phục hồi | Script SQL | Chưa chạy trên đám mây |
| Đám mây, Blob Storage | Chưa | Hướng dẫn ở TECHNICAL mục 7 |
| Google Maps | Nhúng bản đồ và liên kết | Chưa có API key/tìm theo bản đồ |
| Stack | FastAPI + SQL Server | Chọn vì trọng tâm môn là hệ quản trị CSDL |

## Chương 7. Kết luận và hướng phát triển
Kết quả: nền tảng đa phía chạy end-to-end với phần lõi CSDL chặt chẽ. Hướng phát triển: triển khai đám mây, LLM/embedding, mô hình phục hồi ảnh học sâu, MoMo/Stripe, hoa hồng nền tảng.

## Tài liệu tham khảo
Xem `docs/RBL.md` (gợi ý), tài liệu Microsoft SQL Server (isolation, locking, backup), tài liệu VNPay, Google Identity.
