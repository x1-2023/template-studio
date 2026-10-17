Beta Render 1.3.1 thêm preset **1012 · Karaoke đỏ + video nghiêng**.

- Thêm MP4, chọn 1012 rồi xuất: tự nhận lời thoại, karaoke trắng/đỏ hai dòng, video nghiêng trên nền mờ. Mặc định 1080 × 1440, 30 FPS, ba phần đều nhau.
- Nhận lời thoại local bằng Whisper native. Lần đầu tải runtime/model khoảng 150 MB, xác minh SHA256; các lần sau dùng offline. Không cần Python hoặc CUDA.
- Preview và các phần xuất dùng chung phụ đề đã nhận. Có thể chọn SRT/JSON riêng, chỉnh tiêu đề, góc video/chữ, lặp hiệu ứng và xuất một video hoặc ba phần.
- Có nút mở từng phần. Dừng/lỗi rồi chạy lại cùng nguồn, cấu hình và nơi xuất sẽ kiểm tra các phần hoàn tất và tiếp tục phần thiếu.
- Giữ nguyên các preset TikTok, cấu hình, hàng đợi và các sửa lỗi tiến độ Windows của 1.2.1. Thư mục xuất chỉ nhận MP4; nhật ký và sổ chia phần nằm trong dữ liệu app.
- Tự bổ sung cấu hình mới cho video đang chờ từ 1.2.1, giữ các thông số cũ và sao lưu vào `production-before-karaoke.json` trước khi chuyển. Không cần chọn lại preset để tiếp tục hàng chờ cũ.

Cập nhật qua **Cài đặt → Kiểm tra cập nhật → Cập nhật và mở lại**, hoặc tải ZIP và giải nén toàn bộ. Giữ tên `TemplateStudio.exe` để tương thích updater.

Karaoke dùng ASS/Arial để mô phỏng phong cách mẫu, không khẳng định giống template CapCut 1:1. Điểm chia đều có thể khác cắt thủ công. Lời nhận tự động có thể sai; nên xem thử. Video không có âm thanh cần tắt phụ đề hoặc chọn file có sẵn.

Windows 10/11 x64, driver OpenGL 3.3 trở lên. FFmpeg và bộ nhận giọng nói cần mạng khi chuẩn bị lần đầu; sau đó dùng offline. Shader chạy GPU; Whisper hiện chạy CPU để tương thích máy khác.
