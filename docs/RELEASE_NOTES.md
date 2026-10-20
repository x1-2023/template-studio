Beta Render 1.3.7 bổ sung CA đóng kèm để sửa lỗi xác minh HTTPS khi tải runtime và cập nhật.

- Tải FFmpeg/ffprobe, Whisper/model và updater dùng chung HTTPS với Mozilla CA đóng kèm, bổ sung chứng chỉ tin cậy của Windows.
- Giữ xác minh chứng chỉ và tên máy chủ; chặn chuyển hướng xuống HTTP. Vẫn kiểm tra SHA-256 gói/runtime trước khi cài.
- Lỗi chứng chỉ được báo riêng trong cập nhật và nhận giọng nói; không thử tải FFmpeg lặp lại ba lần với cùng lỗi chứng chỉ.
- Giữ ZY Trend có sẵn, bảng màu riêng cho tiêu đề/PART, phụ đề tự động, cách chia part và dữ liệu người dùng.

Cập nhật qua **Cài đặt → Kiểm tra cập nhật → Cập nhật và mở lại** nếu bản cũ còn kết nối được. Nếu bản cũ báo lỗi SSL như `unable to get local issuer certificate`, tải ZIP bằng trình duyệt, tắt app và chép **nội dung thư mục TemplateStudio trong ZIP** đè vào thư mục app cũ. Giữ `data/`, `runtime/`, `exports/`. Sau đó mở app và bấm **Thử lại FFmpeg** nếu chưa có runtime. Máy mới vẫn cần mạng cho lần tải FFmpeg/Whisper đầu tiên.

Ngày/giờ Windows phải đúng; mạng có proxy/phần mềm kiểm tra HTTPS cần chứng chỉ tin cậy tương ứng trong Windows.
