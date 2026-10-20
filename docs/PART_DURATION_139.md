# Số part và thời lượng tùy chọn — 1.3.9

## Hành vi

Trong **Đoạn nguồn & chia part → Chọn số part**:

- Để trống **Giây mỗi part (tùy chọn)**: chia đều toàn bộ đoạn nguồn đã chọn thành đúng số part. Ví dụ nguồn 20 phút, chọn 00:00–10:00, 3 part, tốc độ 1×: 200 + 200 + 200 giây. Không xuất phần sau phút 10.
- Nhập 1–1800 giây: xuất tối đa số part đã chọn, giây tính sau khi cắt/bỏ quảng cáo/đổi tốc độ. Mốc thời lượng được làm tròn về lưới 30 FPS.
- **Bỏ phần dư**: đoạn 600 giây, 3 × 180 giây → 180 + 180 + 180, bỏ 60 giây cuối đoạn.
- **Gộp vào part cuối**: cùng ví dụ → 180 + 180 + 240 giây. Không lấy nội dung ngoài mốc Đến.
- Nguồn thiếu thì phần cuối ngắn hơn; nếu chỉ đủ một phần thì xuất một phần, không tạo file rỗng. Giao diện báo trước số phần và độ dài của đoạn đang cấu hình.

Hai trường mới `part_fixed_seconds=0` và `part_remainder="drop"` được lưu cùng preset. Preset/queue cũ nhận giá trị 0 nên tiếp tục chia đều, không tự giới hạn thành 180 giây. Chế độ tự chia theo thời lượng và xuất một video không dùng hai trường này.

`parts_duration` được dùng chung cho kế hoạch part, giới hạn preview và dung lượng dự kiến. Preview từ đoạn đã chọn bỏ bị chặn trước khi nhận lời. Các part vẫn dùng cùng renderer, phụ đề và nhãn PART theo thứ tự. Sửa thêm nhánh trạng thái hàng đợi dùng đường dẫn kết quả thực khi chế độ chia part chỉ có một file kết quả; trước đây nhánh này đọc nhầm tên đích chưa được tạo và báo lỗi sau khi đã render thành công.

Ô giây có xử lý riêng khi mất focus/lưu để xóa trắng vẫn có hiệu lực dù `DoubleValidator` coi chuỗi rỗng là trạng thái trung gian. Hủy chỉ bỏ bản nháp, không thay cấu hình đã lưu.

## Kiểm định

- Commit ứng dụng: `c2fc011ab24a990a413ab72f8c0dca98dce2b7bf`.
- **137 kiểm thử local đạt**, Ruff và `git diff --check` đạt. Có kiểm thử bàn phím/chuột nhập giây, đổi phần dư, xóa về chia đều, hủy, lưu preset; kiểm thử nguồn 20 phút chỉ lấy 10 phút, cả hai chính sách phần dư, tốc độ/cắt quảng cáo, lưới frame, nguồn ngắn và chặn preview ngoài phần sẽ xuất.
- [CI Windows 39429045489](https://github.com/x1-2023/template-studio/actions/runs/39429045489) đạt. Runner không có OpenGL 3.3 nên bỏ qua lớp kiểm tra pixel GPU; kiểm tra GPU và EXE thực chạy trên RTX 2070 SUPER/NVENC local.
- Gói EXE mới giải nén ở thư mục riêng, PATH chỉ có Windows, runtime FFmpeg đã xác minh trong dữ liệu kiểm thử. Nguồn thật 509.125 giây: giữ 60–70 giây, bỏ 62–63.25 và 66.1–67.2, tốc độ 1.02931464386368×, chọn 3 part. Nội dung sau cắt còn 7.432130 giây.
- Với 2 giây/part và bỏ dư: **60 + 60 + 60 = 180 khung**, đúng 6 giây.
- Với 2 giây/part và gộp dư: **60 + 60 + 103 = 223 khung**, giữ hết đoạn chọn; part cuối dài hơn 2 giây.
- Để trống giây: **74 + 74 + 75 = 223 khung**, chia đều trên lưới frame. Tổng ba lượt **626 khung**, tất cả có âm thanh, font ZY Trend và nhãn PART riêng. Nhật ký xác nhận không lấy ngoài mốc Đến hoặc lọt đoạn quảng cáo.
- Chạy điều phối batch với worker EXE thật trên đoạn 1.5 giây nguồn: chỉ đủ một part, vẫn **Hoàn tất**, đường dẫn kết quả tồn tại; không ghi đè nguồn. SHA-256 nguồn giữ nguyên.
- Bằng chứng riêng: `.runtime/qa-native-parts-139/verified.json`, ảnh `.runtime/part-seconds-139.png`; không public video, lời thoại hoặc dữ liệu cá nhân.

## Gói đã kiểm định

- `TemplateStudio-windows-x64.zip`: **257836232 byte**.
- SHA-256: `18a0753981b9c5abb88a703931b33d63576ae52a9c3e924cf10d1fe6d5e87bae`.
- Tên EXE/asset và cơ chế updater được giữ. Không có dependency mới; thư viện, font, shader/LUT và CA đã đóng kèm như 1.3.8. FFmpeg/Whisper cần tải lần đầu nếu máy chưa có runtime.
