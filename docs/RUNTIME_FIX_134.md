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
5. Thư mục dữ liệu mới chưa có runtime, chặn mạng hoàn toàn: vẫn giữ rõ lỗi tải kể cả GPU đã nhận, ghi log và thoát đúng mã 1 ở chế độ kiểm tra. Log JSON tương thích bảng mã cp1252 của Windows, không bị `UnicodeEncodeError` khi thông báo có dấu.

Máy QA dùng RTX 2070 SUPER. Không truy cập máy GTX 1660 SUPER qua UltraViewer; ảnh người dùng chỉ được dùng để chẩn đoán triệu chứng.

Gói cuối đã kiểm tra SHA-256: `81c8e5aee079e2b02dd780692e5c6ab18865321e37a2925d34a8ce46a0ac02b8`. Bằng chứng riêng: `.runtime/qa-native-134b/verified.json`; không commit runtime, video hoặc dữ liệu người dùng. 102 kiểm thử đã qua trên local và CI Windows, gồm checksum/cache/tải ngắt, tách lỗi runtime khỏi nguồn, phục hồi cấu hình và không để trạng thái GPU che lỗi cài đặt. CI đã kiểm tra cả hai màn hình GUI.

## Updater public

Đã public [v1.3.4](https://github.com/x1-2023/template-studio/releases/tag/v1.3.4), ZIP 257672418 byte, digest GitHub khớp checksum trên. Bản sao public 1.3.3 có runtime thiếu ffprobe đã tải qua updater, thay EXE, báo `healthy.json` phiên bản 1.3.4 và giữ backup đúng hash EXE cũ. Giữ nguyên dữ liệu riêng, font đã nhập, preset, số part, màu, cấu hình từng nguồn và thư mục xuất; mục cũ lỗi thiếu công cụ được đọc lại về hàng chờ.

Sau nâng cấp, mở chính EXE vừa tải với PATH chỉ có Windows và mạng chặn: runtime riêng tự phục hồi ffprobe từ ZIP cache, nhận GPU rồi xuất offline 90 khung có âm thanh. Bằng chứng riêng: `.runtime/qa-updater-134/verified.json`. Không truy cập hoặc cài trực tiếp trên máy từ ảnh UltraViewer.
