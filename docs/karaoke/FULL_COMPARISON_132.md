# Đối chiếu đủ hai part 1012 — EXE public 1.3.2

Ngày 19/10/2026. Nguồn: video YouTube `RklXxpuf2Sc`, H.264 1920×1080/24 FPS, luồng video 509.125 giây. Tham chiếu: `Part1,2-1.mp4`, `Part1,2-2.mp4` và Draft 1012 trong `CapCut Drafts.rar` do người dùng gửi. Nguồn và các thành phẩm giữ local.

## Cách đối chiếu

- Dùng đúng EXE public 1.3.2 đã tải qua updater, RTX 2070 SUPER/NVENC, 1080×1440/30 FPS, bitrate mục tiêu 9.65 Mb/s. Worker chạy ngoại tuyến, PATH chỉ Windows và dùng runtime đã lưu.
- Dùng preset 1012 mặc định cùng phụ đề Whisper đã tự nhận từ toàn bộ nguồn (1457 từ). Không thay lời tự nhận bằng phụ đề Draft để làm điểm số đẹp hơn. Tiêu đề lấy tên file.
- Căn điểm bắt đầu theo Draft: nguồn 0 giây cho part 1 và 191.433333 giây cho part 2, tốc độ 1.02931464386368×. Thời lượng tính từ số khung tham chiếu chia 30, tránh làm tròn metadata thành thừa một khung. Giới hạn ngữ cảnh phụ đề và đặt lại intro ở đầu mỗi part.
- Đây là lượt QA căn theo hai thành phẩm. Chế độ tự chia khoảng 180 giây của app vẫn giữ toàn nguồn, không dùng cố định các điểm cắt của mẫu này cho video khác. Part cuối của nguồn không có bản CapCut để so; lượt kiểm tra trước đã xuất đủ ba part và giữ phần đuôi.
- Chấm mọi khung ở kích thước gốc bằng SSIM/PSNR luma của FFmpeg, không tìm offset hay biến dạng riêng từng khung để tăng điểm. PSNR toàn clip tính từ MSE trung bình; SSIM lấy trung bình từng khung. Cách tính này khác cửa sổ Gaussian của báo cáo bốn ảnh trước nên không so trực tiếp hai số SSIM.
- Ngoài ra lấy chín mốc mỗi part (0.3, 1.5, 5, 30, 60, 90, 120, 150 giây và một giây trước cuối). Tính lại SSIM Gaussian 11×11/sigma 1.5 trên ảnh xám; số ngoài dải chữ bỏ cùng ba vùng y=0–419, 875–1119 và 1150–1329, cùng viền 5 pixel như báo cáo trước. Đây là vùng còn lại sau khi bỏ dải chữ, không đại diện toàn khung.

## Kết quả toàn bộ hai part

| Part | Khung đã so | Thời lượng | SSIM luma trung bình | PSNR luma toàn clip | SSIM ngoài dải chữ tại 9 mốc |
|---|---:|---:|---:|---:|---:|
| 1 | 5579 | 185.966667 s | 0.8402 | 15.36 dB | 0.9156–0.9363 |
| 2 | 5429 | 180.966667 s | 0.8274 | 15.38 dB | 0.8960–0.9538 |

Tổng 11008 khung, đủ thời lượng của cả hai thành phẩm, có âm thanh. Các số này không phải phần trăm độ giống. Khác biệt chữ/phần nền chữ đóng góp nhiều vào sai số toàn khung.

## Sai khác đã xác nhận

- Bố cục, hướng nghiêng, intro ngũ giác và vị trí tiêu đề/PART đã gần mẫu ở ảnh đầu, giữa và cuối. Màu/độ nét/nền mờ vẫn có khác biệt; chưa tái tạo chính xác toàn bộ engine CapCut.
- Font Arial Black thay cho ZY Trend; cỡ/cách chia cụm, thời gian giữ cụm và mốc từ tự nhận khác CapCut. Bản GPU chưa có emoji động hay tô màu từ khóa theo nghĩa như mẫu. Chữ `PART 1` cũng khác chữ `PART1` của thành phẩm.
- Part 2 có 21 khung SSIM dưới 0.5; tất cả là các mốc đơn lẻ trong thống kê. Đã xem năm khung quanh 173.433333 giây: GPU chuyển sang góc máy mới trước CapCut một khung 30 FPS, hai bản lại cùng cảnh ở khung tiếp theo. Chưa sửa hoặc căn bù để che khác biệt này. Chưa kiểm tra bằng mắt từng mốc trong 21 mốc; cần kiểm tra cách seek và pha đổi 24→30 FPS khi bắt đầu part giữa nguồn nếu muốn khớp frame chính xác.
- So đường bao năng lượng âm thanh 10 giây ở đầu, giữa và cuối mỗi part, lấy mẫu 8 kHz, cửa sổ 10 ms, tìm độ lệch trong ±500 ms. GPU sớm hơn CapCut khoảng 50 ms ở part 1 và 40–50 ms ở part 2; tương quan 0.932–0.973. Chưa thấy lệch tăng dần tại sáu cửa sổ đã đo. Đây là độ lệch giữa hai file, không thay thế đo đồng bộ môi–tiếng của người xem và chưa được sửa trong 1.3.2.

## File xem và bằng chứng local

Trong `.runtime/compare-1012-full/`:

- `xem-nhanh-so-sanh-2-part-bt709.mp4`: 24 giây/720 khung, mỗi part lấy 3 giây ở đầu, 60 giây, 120 giây và gần cuối.
- `so-sanh-nguon-capcut-gpu-part1-bt709.mp4`, `so-sanh-nguon-capcut-gpu-part2-bt709.mp4`: đủ hai part, ba cột nguồn / CapCut / GPU. Cột nguồn chỉ đổi tốc độ để đồng bộ và thu vừa khung, giữ tỷ lệ gốc. Các cột được đổi sang cùng BT.709 cho file xem. Âm thanh lấy từ CapCut để tránh phát ba luồng cùng lúc.
- `gpu-part1-full.mp4`, `gpu-part2-full.mp4`: đầu ra GPU 1080×1440 thật, có âm thanh riêng; dùng các file này để đo chất lượng và nghe âm thanh GPU. Không chấm điểm trên video ba cột đã thu nhỏ/encode lại.
- `contact-part1.jpg`, `contact-part2.jpg`: ảnh ở 0.3/60/120 giây và gần cuối, ba cột.
- `inputs.json`: SHA256 của nguồn, hai thành phẩm và RAR; cấu hình thực tế. `renders.json`: metadata ffprobe của từng đầu ra. `analysis.json`, `part*.ssim.log`, `part*.psnr.log`: số đo từng khung/cửa sổ âm thanh. `cut-differences.json` và `cut-difference-part2.jpg`: mốc và ảnh chuyển cảnh lệch. `verified.json`: các kiểm tra hoàn tất và đường dẫn file xem.

Kết luận: đã đối chiếu đủ hai part bằng bản app public; chưa khớp CapCut 1:1. Các bước cải tiến có căn cứ là kiểu/chia cụm phụ đề, template emoji/màu từ khóa, pha chọn khung ở đầu part và độ lệch âm thanh so với thành phẩm.
