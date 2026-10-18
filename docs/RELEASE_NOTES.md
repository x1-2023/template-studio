Beta Render 1.3.1 thêm preset **1012 · Karaoke đỏ + video nghiêng**.

- Thêm MP4, chọn 1012 rồi xuất: tự nhận lời thoại, karaoke trắng/đỏ hai dòng, video nghiêng trên nền mờ. Theo hai thành phẩm và Draft: 1080 × 1440/30 FPS, khoảng 9.65 Mb/s, tốc độ 1.0293×, video −9°, chữ −11°.
- Nhận lời thoại local bằng Whisper native. Lần đầu tải runtime/model khoảng 150 MB, xác minh SHA256; các lần sau dùng offline. Không cần Python hoặc CUDA.
- Tự chia khoảng 180 giây/part, ưu tiên khoảng nghỉ/cuối câu gần mốc cắt, giữ toàn bộ nội dung. Tự đánh số PART và chạy intro riêng ở đầu mỗi phần. Có thể đổi thời lượng hoặc chọn một video/hai/ba phần đều nhau.
- Preview và các phần xuất dùng chung phụ đề đã nhận. Tiêu đề mặc định lấy từ tên file; có thể sửa/tắt, chọn SRT/JSON riêng và chỉnh góc video/chữ.
- Có nút mở từng phần. Dừng/lỗi rồi chạy lại cùng nguồn, cấu hình và nơi xuất sẽ kiểm tra các phần hoàn tất và tiếp tục phần thiếu.
- Giữ nguyên các preset TikTok, cấu hình, hàng đợi và các sửa lỗi tiến độ Windows của 1.2.1. Thư mục xuất chỉ nhận MP4; nhật ký và sổ chia phần nằm trong dữ liệu app.
- Tự bổ sung cấu hình mới cho video đang chờ từ 1.2.1, giữ các thông số cũ và sao lưu vào `production-before-karaoke.json` trước khi chuyển. Không cần chọn lại preset để tiếp tục hàng chờ cũ.

Cập nhật qua **Cài đặt → Kiểm tra cập nhật → Cập nhật và mở lại**, hoặc tải ZIP và giải nén toàn bộ. Giữ tên `TemplateStudio.exe` để tương thích updater.

Karaoke dùng ASS/Arial Black để mô phỏng phong cách mẫu; chưa có emoji động và tô màu từ khóa của template gốc. Điểm chia tự động có thể khác cắt thủ công. Lời nhận tự động có thể sai; nên xem thử. Video không có âm thanh cần tắt phụ đề hoặc chọn file có sẵn.

Windows 10/11 x64, driver OpenGL 3.3 trở lên. FFmpeg và bộ nhận giọng nói cần mạng khi chuẩn bị lần đầu; sau đó dùng offline. Shader chạy GPU; Whisper hiện chạy CPU để tương thích máy khác.
