# Sửa lỗi thiếu ffprobe trong 1.3.4

Ngày kiểm tra: 20/10/2026. Triệu chứng người dùng gửi: GPU GTX 1660 SUPER đã nhận nhưng cả ba video báo `Thiếu công cụ local ffprobe`.

## Nguyên nhân và cách sửa

Gói app có Python/Qt/thư viện dựng GPU trong `_internal`; FFmpeg/ffprobe được tải từ Gyan ở lần chuẩn bị đầu. Khi chuẩn bị runtime thất bại hoặc công cụ bị mất, luồng kiểm tra GPU vẫn có thể thành công rồi ghi đè thông báo lỗi thành trạng thái sẵn sàng. Nhập nguồn sau đó gọi ffprobe và đánh dấu mỗi video lỗi. Ảnh không đủ để kết luận vì sao máy người dùng mất công cụ hoặc tải thất bại; bản sửa xử lý các trường hợp đó và giữ log nguyên nhân tải.

- Kiểm tra cả hai công cụ, xác minh hash runtime do app quản lý, kiểm tra khởi động với công cụ ngoài trước khi đọc video.
- Lỗi runtime giữ rõ trên màn hình chính, có **Thử lại FFmpeg** và log `media-setup-error.log`. Kiểm tra GPU không che lỗi này.
- Tải ngắt tự thử lại tối đa ba lần. Giữ ZIP đã kiểm tra checksum trong cache để sửa runtime offline; hỗ trợ chọn ZIP Gyan 7.1.1 từ máy khác trong Cài đặt.
- Sau khi chuẩn bị thành công, chỉ những mục cũ lỗi thiếu công cụ được đọc lại, khôi phục metadata và đưa về hàng chờ. Giữ cấu hình từng video, không xóa video nguồn hay kết quả.

## EXE đã kiểm tra

Giải nén ZIP 1.3.4 vào thư mục QA sạch, không copy runtime từ máy phát triển, PATH chỉ có Windows:

1. Khởi động EXE, tải bộ FFmpeg thật từ URL Gyan đã ghim và xác minh SHA-256. App phục hồi ba mục hàng chờ có lỗi thiếu ffprobe và đọc thêm một nguồn mới.
2. Xóa riêng `ffprobe.exe` trong bản sao QA rồi chặn mạng: app giải nén lại từ cache và nhận GPU thành công.
3. Ghi dữ liệu hỏng vào riêng `ffmpeg.exe` trong QA: app phát hiện hash sai và sửa lại khi offline.
4. Chính EXE sau sửa xuất NVENC 90 khung, 1080 × 1920/30 FPS, có âm thanh. Tên nguồn có dấu và ký tự `#`.

Máy QA dùng RTX 2070 SUPER. Không truy cập máy GTX 1660 SUPER qua UltraViewer; ảnh người dùng chỉ được dùng để chẩn đoán triệu chứng.

Gói đã kiểm tra SHA-256: `bfc0a10a24dffd22e33efd4a5794160098db7762fc4ce4ad3a5f5956993249c8`. Bằng chứng riêng: `.runtime/qa-native-134/verified.json`; không commit runtime, video hoặc dữ liệu người dùng. 102 kiểm thử local đã qua, gồm checksum/cache/tải ngắt, tách lỗi runtime khỏi nguồn, phục hồi cấu hình và không để trạng thái GPU che lỗi cài đặt.
