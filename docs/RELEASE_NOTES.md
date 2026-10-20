Beta Render 1.3.9 cho chọn số part kèm thời lượng tùy chọn và cách xử lý phần dư.

- Trong **Chọn số part**, ô **Giây mỗi part (tùy chọn)** để trống sẽ chia đều đoạn đã chọn. Ví dụ nguồn 20 phút, chọn `00:00 → 10:00`, nhập 3 part: chỉ chia 10 phút đầu, phần sau không xuất.
- Nếu nhập thêm số giây (1–1800), app xuất tối đa số part đã chọn. Nguồn thiếu thì part cuối ngắn hơn, không tạo part rỗng.
- **Phần dư → Bỏ phần dư**: ví dụ đoạn 600 giây, 3 × 180 giây sẽ xuất 540 giây, bỏ 60 giây cuối đoạn. **Gộp vào part cuối** xuất 180 + 180 + 240 giây.
- Phần dư chỉ tính trong đoạn Từ/Đến sau khi bỏ quảng cáo và đổi tốc độ. Gộp vào part cuối vẫn không lấy nội dung ngoài mốc Đến. Ranh giới thời lượng được làm tròn theo khung 30 FPS.
- Hiện kế hoạch chia ngay trong cấu hình; giới hạn xem thử và dung lượng dự kiến theo đúng phần sẽ xuất. Lưu giây/phần dư cùng preset; preset cũ vẫn chia đều như trước.
- Sửa báo lỗi sai khi chế độ chia part chỉ xuất được một phần vì nguồn ngắn. Giữ font ZY Trend, màu riêng cho chữ/PART, chỉnh màu GPU và updater.

Cập nhật qua **Cài đặt → Kiểm tra cập nhật → Cập nhật và mở lại** nếu bản cũ còn kết nối được. Nếu bản cũ báo lỗi SSL như `unable to get local issuer certificate`, tải ZIP bằng trình duyệt, tắt app và chép **nội dung thư mục TemplateStudio trong ZIP** đè vào thư mục app cũ. Giữ `data/`, `runtime/`, `exports/`. Sau đó mở app và bấm **Thử lại FFmpeg** nếu chưa có runtime. Máy mới vẫn cần mạng cho lần tải FFmpeg/Whisper đầu tiên.

Các khoảng quảng cáo được chọn thủ công, app chưa tự nhận diện quảng cáo. Khi cắt riêng video đã hoàn tất, mục đó trở về hàng chờ để xuất bản mới; bản xuất cũ vẫn được giữ.
