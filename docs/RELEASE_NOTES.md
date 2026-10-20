Beta Render 1.3.4 sửa lỗi thiếu ffprobe trên máy mới hoặc bản cũ.

- Kiểm tra cả FFmpeg và ffprobe trước khi đọc video; công cụ thiếu/hỏng được tải hoặc sửa lại. Không đánh dấu hàng loạt video lỗi chỉ vì thiếu runtime.
- Giữ rõ thông báo cài runtime thất bại ở màn hình chính, kể cả khi GPU đã nhận. Có nút **Thử lại FFmpeg** và log `media-setup-error.log`.
- Tải bị gián đoạn tự thử lại tối đa ba lần. Giữ ZIP đã xác minh để sửa công cụ offline ở lần sau.
- Có thể chọn ZIP FFmpeg 7.1.1 essentials của Gyan tại **Cài đặt → Cài từ ZIP FFmpeg đã tải…**. Cài từ ZIP vẫn kiểm tra checksum của cả gói và từng EXE.
- Tự đọc lại các video bản cũ lỗi thiếu công cụ rồi đưa về hàng chờ, giữ nguyên cấu hình từng video.

Cập nhật qua **Cài đặt → Kiểm tra cập nhật → Cập nhật và mở lại**; hoặc tải ZIP app, giải nén toàn bộ rồi mở `TemplateStudio.exe`. Giữ dữ liệu, preset, font và video xuất. Máy chưa từng chuẩn bị runtime cần mạng cho lần tải đầu, hoặc chọn ZIP FFmpeg đã tải sẵn.

Bao gồm các cải tiến phụ đề 1.3.3: nhập font riêng, mốc phụ đề Draft, màu từ khóa/emoji và sửa đồng bộ hình/tiếng.
