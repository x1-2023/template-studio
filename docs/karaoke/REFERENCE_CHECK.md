# Đối chiếu 1012 với nguồn thật

Ngày 18/10/2026. Nguồn do người dùng cung cấp: [video YouTube](https://www.youtube.com/watch?v=RklXxpuf2Sc), bản H.264 1920×1080/24 FPS; luồng video dài 509.125 giây. Hai thành phẩm CapCut là hai part đầu; người dùng xác nhận bản mẫu thiếu part cuối và app phải giữ toàn bộ nguồn.

Đã render hai đoạn GPU 1080×1440/30 FPS từ nguồn này: part 1 bắt đầu nguồn tại 0; part 2 tại 191.433333 giây. Tốc độ theo Draft 1.02931464386368×. Dùng 1182 từ đọc từ Draft để kiểm tra bố cục/kiểu chữ riêng với sai số ASR. Luồng sản xuất và preview thực tế dùng Whisper tự nhận lời thoại; không dùng sẵn lời của video mẫu cho nguồn khác.

Đã chỉnh lại hướng xoay, dịch X, cỡ chữ, dòng trên lớn hơn dòng dưới, tiêu đề và nhãn PART. Giới hạn ngữ cảnh phụ đề theo từng part để không hiển thị cụm cuối của part trước; preview ở giữa part vẫn giữ cùng ngữ cảnh với bản full.

## Số đo trên bốn khung hình

SSIM và PSNR trên ảnh xám 1080×1440 cùng thời điểm, không tìm offset để tối ưu số đo. SSIM dùng cửa sổ Gaussian 11×11, sigma 1.5, L=255; bỏ viền 5 pixel. Cột vùng hình bỏ ba dải ngang chứa chữ: y=0–419, 875–1119 và 1150–1329. Các dải này rộng hơn biên chữ thật, nên không thay thế số đo toàn khung.

| Part | Giây | SSIM toàn khung | PSNR toàn khung | SSIM vùng hình | PSNR vùng hình |
|---|---:|---:|---:|---:|---:|
| 1 | 0.3 | 0.8324 | 15.88 dB | 0.9356 | 27.24 dB |
| 1 | 1.5 | 0.8388 | 15.57 dB | 0.9344 | 26.04 dB |
| 2 | 0.3 | 0.8616 | 16.93 dB | 0.9539 | 28.79 dB |
| 2 | 1.5 | 0.8564 | 16.54 dB | 0.9377 | 30.27 dB |

Đây là bốn mẫu kiểm tra đầu clip, không phải phần trăm độ giống hay đánh giá toàn bộ video. Khác biệt rõ nhất còn ở font ZY Trend/Arial Black, cách chia cụm chữ, giữ chữ trong khoảng nghỉ, emoji và màu nhấn từ khóa. Chưa có emoji động/tô màu từ khóa của template CapCut.

## Luồng tự động

Whisper nhận 1457 từ từ toàn bộ nguồn. Với mốc 180 giây, kế hoạch xuất là 180 + 188.8 + khoảng 125.825237 giây ở tốc độ đã đổi; phần cuối được giữ. Điểm cắt ưu tiên nghỉ lời thoại và tránh giữa từ, nên có thể lệch mốc 180 giây và khác điểm cắt thủ công. Tiêu đề mặc định lấy từ tên file; có thể bỏ chọn để nhập tiêu đề riêng hoặc để trống để tắt. Preview thật 3 giây đã được dựng từ phụ đề ASR và tiêu đề tự động.

Đã xuất full nguồn trên RTX 2070 SUPER: ba part 180.000000/188.800000/125.833333 giây, 5400/5664/3775 khung, tổng 14839 khung. Cả ba H.264 1080×1440/30 FPS, khoảng 9.6 Mb/s, có âm thanh. Tổng thời lượng sai khác kế hoạch dưới một khung; thư mục xuất chỉ có ba MP4. Thời gian render khoảng 429 giây trên máy QA, không tính nhận lời thoại. Đây không phải cam kết tốc độ cho máy khác.

80/80 kiểm thử local và [Windows CI](https://github.com/x1-2023/template-studio/actions/runs/39144830992) đạt ở mã chức năng `f16e645eb54165abf19d096fccc48392fc301db8`. ZIP EXE cuối giải nén sang dữ liệu sạch, PATH chỉ có Windows và mạng bị chặn: chuyển cấu hình 1.2.1, sao lưu nguyên trạng, xuất preset cũ, nhận 163 từ và xuất hai part karaoke 1079/533 khung có âm thanh. Phần ASR dùng runtime/model đã tải và xác minh từ lượt kiểm tra sạch trước.

Đã kiểm tra cập nhật thực bằng gói [1.3.1 public](https://github.com/x1-2023/template-studio/releases/tag/v1.3.1), SHA256 `a486c52441f456c83cc0e6766cc59d4fb6eaea5f2781535c6cbc64df365fc3ea`: tải qua updater, kiểm tra hash, giải nén, cài lên bản sao 1.2.1 và mở lại app thành công. Cấu hình cũ, dữ liệu, video xuất và runtime được giữ; backup EXE cũ đúng SHA256. EXE public sau cập nhật render GPU offline 90 khung 1080×1440 với phụ đề ASR và tiêu đề tự động, PATH chỉ có Windows. Thử nghiệm dùng thư mục QA riêng, không thay app người dùng đang mở.

Video nguồn, Draft, phụ đề của mẫu và ảnh đối chiếu giữ local; không đóng gói vào EXE hay đưa lên Git.

Đã bổ sung [đối chiếu đủ 11008 khung của cả hai part bằng EXE public 1.3.2](FULL_COMPARISON_132.md) ngày 19/10/2026, có video ba cột và kiểm tra âm thanh. Báo cáo bên trên ghi lại lượt bốn khung ban đầu; báo cáo mới ghi rõ các sai khác chuyển cảnh và âm thanh phát hiện khi so đủ thời lượng.

Bản [sửa và đối chiếu 1.3.3](UPDATE_133.md) khắc phục seek/FPS, bù âm thanh, thêm nhập font, đọc mốc Draft và dựng lại màu từ khóa/emoji. Đây là trạng thái mới hơn các giới hạn trong báo cáo ban đầu bên trên.
