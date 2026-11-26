# Research-Based Learning (RBL)

Mỗi chủ đề: câu hỏi nghiên cứu, những gì nhóm đã làm trong hệ thống, hạn chế và hướng mở rộng. Phần "Tài liệu nên đọc" là gợi ý để nhóm tự trích dẫn đúng nguồn khi viết báo cáo.

## 1. Resource Scheduling and Allocation Algorithms
- **Câu hỏi**: làm sao phát hiện xung đột và dùng ít tài nguyên nhất khi nhiều đơn cần cùng thiết bị/phòng?
- **Đã làm**: bài toán xếp lịch khoảng (interval scheduling). `equipment_load` quét sự kiện (sweep line, O(n log n)) tìm khung giờ nhu cầu vượt tồn kho; `assign_units` tô màu đồ thị khoảng theo giờ bắt đầu (greedy tối ưu về số "màu" tối thiểu); `best_fit_rooms` chọn phòng để lại ít khoảng vụn nhất. Phía CSDL, tính nhất quán dựa trên khóa `UPDLOCK, HOLDLOCK`.
- **Hạn chế**: một ngày, một cơ sở; chưa tối ưu toàn cục nhiều ràng buộc (giảng viên, di chuyển giữa phòng).
- **Mở rộng**: quy hoạch nguyên (ILP) hoặc tìm kiếm cục bộ cho lịch nhiều ngày; so sánh với thuật toán tham lam.
- **Đọc**: Kleinberg & Tardos, *Algorithm Design*, chương Interval Scheduling và Interval Partitioning.

## 2. Recommendation Systems
- **Đã làm**: lọc theo nội dung và độ phổ biến trong SQL (`sp_RecommendRooms`); gợi ý thiết bị theo đồng xuất hiện (item-to-item co-occurrence).
- **Hạn chế**: cold-start (khách mới chỉ nhận gợi ý phổ biến), chưa đánh giá offline.
- **Mở rộng**: matrix factorization hoặc kNN trên ma trận khách × phòng; đo precision@k bằng chia tập đặt chỗ theo thời gian.
- **Đọc**: Ricci et al., *Recommender Systems Handbook*.

## 3. Artificial Intelligence for Creative Service Platforms
- **Đã làm**: ghép AI vào nghiệp vụ (gợi ý, giá động, trợ lý, phục hồi ảnh) với công tắc bật/tắt của Admin (`ai.*.enabled`), để kiểm soát và so sánh có/không AI.
- **Hạn chế**: thuật toán luật và thống kê, chưa có LLM.
- **Mở rộng**: nối OpenAI API ở `ai/service.ask` (RAG trên kho bài viết đã có TF-IDF), giữ luật hiện tại làm phương án dự phòng.

## 4. Computer Vision for Image Restoration
- **Đã làm**: chuỗi xử lý cổ điển (cân bằng tương phản, khử nhiễu median, làm nét unsharp mask, phóng 2×), đảo âm bản. Luôn tạo ảnh mới, giữ ảnh gốc.
- **Hạn chế**: không xử lý được xước/rách lớn, không tô màu.
- **Mở rộng**: mô hình học sâu (Real-ESRGAN cho siêu phân giải, inpainting cho vết xước); đánh giá bằng PSNR/SSIM trên bộ ảnh có bản gốc.

## 5. Demand Forecasting
- **Đã làm**: dự báo theo trung bình cùng thứ (seasonal naive), nhãn mức cao/thường/thấp, cảnh báo khi dữ liệu ít.
- **Mở rộng**: làm mượt mũ (Holt-Winters), ARIMA/Prophet; so sánh MAE/MAPE với baseline hiện tại bằng backtest cuốn chiếu.

## 6. Semantic Search and Knowledge Retrieval
- **Đã làm**: chuẩn hóa tiếng Việt không dấu, mở rộng từ đồng nghĩa, TF-IDF có trọng số tiêu đề, đoạn trích.
- **Hạn chế**: không hiểu ngữ cảnh sâu, từ điển đồng nghĩa nhỏ.
- **Mở rộng**: embedding câu (đa ngữ) + cosine, kết hợp BM25; đo MRR trên bộ truy vấn do nhóm gán nhãn.

## 7. Multi-sided Platform Design
- **Đã làm**: 4 vai trò + AI, mô hình nhiều phía: khách ↔ nhà cung cấp ↔ chuyên gia, Admin điều tiết (duyệt, hoàn tiền, khiếu nại, cấu hình). Hiệu ứng mạng: nhiều phòng → nhiều khách → nhiều đánh giá → xếp hạng tốt hơn; cộng đồng giữ chân người dùng.
- **Hạn chế**: chưa có mô hình hoa hồng/phí nền tảng; chưa chống gian lận.
- **Đọc**: Parker, Van Alstyne, Choudary, *Platform Revolution*.
