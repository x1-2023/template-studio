# Đối chiếu bản sửa 1.3.3

Ngày kiểm tra: 19/10/2026. Nguồn, hai clip CapCut và điểm bắt đầu part giữ nguyên như [báo cáo 1.3.2](FULL_COMPARISON_132.md). Dùng EXE 1.3.3 đã giải nén, PATH chỉ có Windows, mạng chặn trong lúc render; RTX 2070 SUPER, NVENC, 1080 × 1440/30 FPS, mục tiêu 9.65 Mb/s. Video và Draft cá nhân không đưa lên Git.

## Các thay đổi đã kiểm tra

- Seek sớm một giây, giữ PTS nguồn và chuyển FPS với cùng mốc yêu cầu. Kiểm thử FFmpeg so byte từng khung giữa render liên tục và seek giữa khung 24 FPS ở tốc độ 1.02931464386368× đã qua. Sửa nguyên nhân chuyển camera sớm một khung ở bản cũ.
- Bù âm thanh +50 ms trong preset 1012, có tùy chọn chỉnh ±1000 ms. Phép đo so ba cửa sổ dài 10 giây ở đầu/giữa/cuối mỗi part, dùng bao năng lượng 8 kHz và bước tìm độ lệch 10 ms. Đây là hiệu chỉnh từ cặp clip đã đo; không suy đoán nguyên nhân là AAC hay thay đổi cao độ. Preview giữa part không chèn lại khoảng lặng.
- `draft_content.json` được quy đổi về thời gian nguồn trước khi áp tốc độ và chia part. Giữ các token nhiều tiếng, ranh giới câu và thời gian từng từ của Draft. Mẫu Draft này chỉ có phụ đề của hai part đầu; chế độ **Tự nhận lời thoại** vẫn cần dùng khi muốn nhận toàn bộ video gốc.
- Font tìm được có tên họ nội bộ **ZY Trend**, đã dùng qua `fontsdir` riêng của libass trong EXE; cỡ chữ được căn lại bằng ảnh đặt cạnh CapCut. Không có file font/hash gốc trong RAR để xác nhận bản font trùng hoàn toàn. Font này giữ riêng trên máy; bản public có trình nhập TTF/OTF/TTC và dùng Arial Black khi chưa nhập font.
- Màu từ khóa/emoji là quy tắc dựng lại, có thể tắt riêng. Dùng 14 ảnh Twemoji với giấy phép CC-BY-4.0 và manifest SHA-256. Chưa có cache template emoji/flower text CapCut để dựng đúng mọi biểu tượng, hoạt ảnh và phép ngắt nhóm. Nền tiêu đề vẫn khác nhẹ ở góc bo; không tuyên bố khớp 1:1.

## Kết quả đo

Vùng chấm hình là `crop=1070:420:5:440`, tránh chữ tiêu đề, nhãn PART và phụ đề. SSIM dưới đây là chỉ số của vùng này, không phải phần trăm độ giống toàn video. Dữ liệu từng khung nằm trong thư mục QA riêng `.runtime/qa-release-133/local/`.

| Đoạn | Khung đã chấm | SSIM trung bình | SSIM thấp nhất | Khung SSIM < 0.5 | Lệch tiếng đầu/giữa/cuối |
| --- | ---: | ---: | ---: | ---: | --- |
| Part 1 | 5579 | 0.93560 | 0.89722 | 0 | −10 / −10 / 0 ms |
| Part 2 | 5429 | 0.93357 | 0.78164 | 0 | 0 / 0 / −10 ms |

Giá trị âm nghĩa là tiếng GPU sớm hơn CapCut. Cả sáu cửa sổ đo còn lệch 0–10 ms, so với 40–50 ms ở phép đo bản trước. Không còn khung có SSIM dưới 0.5 trong vùng video đã chấm. Khung thấp nhất của part 2 là khung cuối, tại 180.9333 giây. Font, nhóm chữ và emoji phải đánh giá thêm bằng ảnh/video đặt cạnh nhau; không suy ra độ giống phụ đề từ bảng chấm vùng video.

EXE đã xuất đủ 11008 khung của hai part, tốc độ lần lượt 38.8 và 39.2 FPS; thêm preview 540 × 720 gồm 90 khung từ cache lời thoại Whisper thật. Video xem nhanh 24 giây/720 khung: `.runtime/qa-release-133/local/so-sanh-capcut-gpu-1.3.3.mp4`; cột trái CapCut, cột phải GPU + font ZY Trend + lời/mốc Draft. Âm thanh trong video đặt cạnh lấy từ CapCut; âm thanh GPU được đo riêng ở bảng trên. Hai bản render đầy đủ giữ trong cùng thư mục QA.

CI Windows đã qua 95 kiểm thử, lint và hai màn hình GUI. Kiểm thử bổ sung gồm nhập font qua nút GUI, hủy hộp cấu hình, bảo toàn font riêng, an toàn nội dung ASS, token nhiều tiếng, ánh xạ tốc độ/cắt Draft, lịch emoji, màu từ đang đọc và nâng cấu hình 1012 cũ.

Gói local đã kiểm thử có SHA-256 `2f1e4082377d71dc2b9ad59a9b1931e30c3fd0c38142342158fe13235e4f0989`. Gói public giữ nguyên byte này; không kèm video, Draft hoặc font riêng.

## Updater public

Đã public [v1.3.3](https://github.com/x1-2023/template-studio/releases/tag/v1.3.3), ZIP 257666970 byte, digest GitHub và file checksum cùng khớp SHA-256 bên trên. Bản sao public 1.3.2 đã tải qua chính updater, xác minh gói, thay EXE và mở lại 1.3.3 thành công; có `healthy.json` và backup đúng hash EXE cũ.

Kiểm tra giữ nguyên các giá trị cấu hình cũ trong preset/hàng chờ, số part và màu tự chọn, file font trong `runtime/fonts/`, dữ liệu riêng, thư mục xuất và runtime. Ba tùy chọn mới của snapshot 1012 được bổ sung đúng, không tạo bản sao cấu hình lỗi. Chính EXE tải từ GitHub sau nâng cấp đã render offline preview GPU 90 khung/540 × 720 với font riêng, emoji và âm thanh. Bằng chứng giữ trong `.runtime/qa-updater-133/verified.json`, không đưa dữ liệu QA lên Git.
