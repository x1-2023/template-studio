# Số part và màu chữ — 1.3.2

- Cho nhập 2–100 part, giữ chế độ một video và tự chia theo thời lượng. Số part cố định chia đều theo khung hình, giữ toàn bộ nguồn sau mốc cắt đầu và thay đổi tốc độ. Video quá ngắn được báo lỗi trước khi xuất.
- Năm màu: chữ phụ đề, từ đang đọc, viền, chữ tiêu đề/PART, nền tiêu đề/PART. Nhập HEX hoặc mở bảng chọn; hủy bảng chọn không đổi cấu hình. Lưu cùng preset, dùng cho preview và xuất.
- 84 kiểm thử đạt; Ruff nhóm F đạt. Kiểm thử Qt nhấn chọn màu/hủy, nhập HEX, chọn chế độ chia, nhập 5 part, lưu cấu hình và preset. Kiểm thử chia 7 part với tốc độ khác 1 và mốc cắt đầu xác nhận không mất/lặp khung ở biên.
- Giao diện 1366×768: các ô màu và số part hiển thị đủ; không có cảnh báo QML. Chọn part đã xuất bằng combobox để tránh tràn khi có nhiều phần.
- Render GPU từ source và từ EXE giải nén: video thử 15 giây có tiếng, cắt đầu 0.15 giây, tốc độ 1.02931464386368×, chia 5 part. Đầu ra 1080×1440/30 FPS, số khung 86/87/86/87/87, có âm thanh ở cả 5 phần; thư mục xuất chỉ có 5 MP4. Preview 540×720/30 FPS, 60 khung trong 2 giây.
- Kiểm tra điểm ảnh trong video full và preview xác nhận cả năm màu thử `00FFCC`, `3366FF`, `FF00FF`, `FFDD00`, `123D56` xuất hiện đúng. Đây là màu QA, không đổi màu mặc định của preset 1012.
- EXE chạy với PATH chỉ Windows, chặn proxy mạng, dùng runtime đã lưu. Cấu hình 1.3.1 của preset/hàng chờ được bổ sung màu mặc định trắng/đen/hồng; giữ số part, màu highlight đã chỉnh và mọi thông số cũ.

File kiểm chứng local: `.runtime/tests-132-final.log`, `.runtime/qa-colors-parts-132/verified.json`, `.runtime/qa-native-132/verified.json`. Video và dữ liệu QA không đưa lên Git.
