# ZY Trend có sẵn — 1.3.6

Preset 1012 dùng ZY Trend đóng trong `template_studio/assets/fonts/ZYTrend.ttf` cho phụ đề, tiêu đề và PART. Renderer lấy font cạnh module trong source hoặc `_internal/` của EXE, kiểm tra SHA-256 rồi chép riêng vào `fonts/caption.ttf` của worker cho libass. Không cài font vào Windows hoặc tìm file trên máy tạo preset.

Preset lưu `subtitle_font_builtin="zy-trend"`, `subtitle_font_name="ZY Trend"`, `subtitle_font_file=""`. File font riêng được ưu tiên nếu có. Nút **ZY Trend** đưa về font có sẵn. Các cấu hình 1012 cũ còn dùng Arial Black mặc định được chuyển một lần; lựa chọn font riêng và lựa chọn đã lưu rõ ràng được giữ.

Font giữ nguyên metadata/bản quyền, không cấp lại GPL. Xem [thông tin tài nguyên](../../template_studio/assets/fonts/README.md).

## Kiểm chứng

- 109 kiểm thử trên máy Windows: qua. [Kiểm thử Windows GitHub của source c83e450](https://github.com/x1-2023/template-studio/actions/runs/39378491369): qua. Ruff F và `git diff --check`: qua.
- GUI mặc định hiển thị ZY Trend; nút khôi phục font hoạt động không cần mở hộp thoại nhập, lưu được vào preset.
- EXE chạy với PATH chỉ có Windows, mạng bị chặn sau khi chuẩn bị runtime. Tự nhận 51 từ từ MP4 thử 15 giây; dùng Whisper native, không dùng Draft hay cache lời cũ.
- Xuất ba part 1080 × 1440/30 FPS bằng NVIDIA RTX 2070 SUPER/NVENC, có âm thanh và nhãn PART 1–3. Phụ đề, tiêu đề và PART cùng dùng ZY Trend được stage từ tài nguyên app; không có font trong `runtime/fonts/`.
- Số khung các part là 146, 146, 145; tổng thời lượng container khớp nguồn sau đổi tốc độ trong sai số dưới 1/30 giây. Độ dài không nguyên khung được kiểm tra cả hình và tiếng.
- Preview 540 × 720 gồm 90 khung; so khung đã giải mã với cùng font nhập riêng: sai khác trung bình 0.0. Cỡ chữ và ScaleX được giữ như bản ZY Trend đã đối chiếu trước đây.
- Updater public **1.3.5 → 1.3.6** tải/xác minh/cài/mở lại thành công, có backup; giữ preset, hàng chờ, màu/số part và font riêng. Font mặc định cũ chuyển sang font nhúng. EXE sau cập nhật render 90 khung dùng đúng font trong gói public.

[Gói public 1.3.6](https://github.com/x1-2023/template-studio/releases/tag/v1.3.6) được build bằng workflow GitHub, ZIP 257.650.315 byte:

```text
SHA-256 ZIP: edfb759c8821bdba691e82e65d05dc9c0a4a50a8e7765b941879d2aed7a394ac
SHA-256 font: e6b721d49a34786e34a4d198a1734b73f2ffff3b8b23461efc827e7dedc1b3db
```

Kịch bản và kết quả cục bộ: `.runtime/qa_font_136.py`, `.runtime/qa-font-136b/`, `.runtime/qa-font-136-public/`, `.runtime/qa_updater_136.py`, `.runtime/qa-updater-136/`. Gói public được tải qua updater và kiểm tra lại riêng; không ghi đè asset đã phát hành. Video/font tùy chọn/dữ liệu người dùng không được đưa vào bài kiểm thử công khai.
