Beta Render 1.3.8 thêm chọn đoạn nguồn trước khi chia part, bỏ quảng cáo và chỉnh màu video.

- **Đoạn nguồn & chia part**: nhập Từ/Đến theo video gốc, ví dụ `00:00 → 10:00`, rồi chọn 3 part hoặc số giây mỗi part. Để trống Đến để lấy hết video.
- Bỏ tối đa 20 khoảng quảng cáo/đoạn không cần bằng mốc bắt đầu–kết thúc. App nối phần còn lại trước khi chia; hình, tiếng và phụ đề cùng dùng các mốc đã cắt. Khoảng trùng nhau được gộp.
- **Chọn đoạn riêng…** dưới danh sách nguồn để đặt mốc khác cho từng video. Đổi preset hoặc thử lại vẫn giữ đoạn riêng; **Dùng đoạn chung** đưa video về cấu hình chung.
- **Chỉnh màu video**: độ sáng, tương phản, bão hòa và tông màu, có nút đặt lại. Chạy trên GPU sau bộ lọc/hiệu ứng, không đổi màu chữ; lưu cùng preset và dùng cho xem thử lẫn bản xuất.
- Phân nhóm rõ màu phụ đề, tiêu đề và PART; chữ/nền PART vẫn chọn riêng bằng bảng màu cơ bản, bảng chọn màu hoặc HEX.
- Giữ font ZY Trend có sẵn, phụ đề tự động và sửa HTTPS từ 1.3.7. Nguồn và file đã xuất không bị ghi đè.

Cập nhật qua **Cài đặt → Kiểm tra cập nhật → Cập nhật và mở lại** nếu bản cũ còn kết nối được. Nếu bản cũ báo lỗi SSL như `unable to get local issuer certificate`, tải ZIP bằng trình duyệt, tắt app và chép **nội dung thư mục TemplateStudio trong ZIP** đè vào thư mục app cũ. Giữ `data/`, `runtime/`, `exports/`. Sau đó mở app và bấm **Thử lại FFmpeg** nếu chưa có runtime. Máy mới vẫn cần mạng cho lần tải FFmpeg/Whisper đầu tiên.

Các khoảng quảng cáo được chọn thủ công, app chưa tự nhận diện quảng cáo. Khi cắt riêng video đã hoàn tất, mục đó trở về hàng chờ để xuất bản mới; bản xuất cũ vẫn được giữ.
