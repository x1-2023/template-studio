# Màu tiêu đề và PART — 1.3.5

Trong **Chỉnh cấu hình → Phụ đề karaoke**, bốn mục độc lập là **Chữ tiêu đề**, **Nền tiêu đề**, **Chữ PART**, **Nền PART**. Mỗi mục màu, kể cả màu phụ đề, có 10 ô chọn nhanh, nút mở bảng màu tùy ý và ô HEX.

`part_color` và `part_background` được lưu trong cấu hình/preset. Khi đọc preset cũ thiếu hai trường này, app lấy đúng màu tiêu đề đã lưu; không đổi sang màu mặc định. Đổi màu PART sau đó không tác động tiêu đề. Preview và xuất truyền cùng các giá trị xuống hai style ASS riêng.

## Kiểm chứng

- 105 kiểm thử trên máy Windows: qua; [CI Windows](https://github.com/x1-2023/template-studio/actions/runs/39373270811) cũng qua. Ruff F và `git diff --check`: qua.
- Kiểm thử GUI bấm các ô màu, lưu thay đổi, lưu preset và hủy lần chỉnh tiếp theo. Thử cả cửa sổ 1100 × 720.
- EXE giải nén từ ZIP phát hành, PATH chỉ có Windows; dùng bộ FFmpeg riêng đã xác minh, chặn mạng khi kiểm tra khởi động/render.
- GPU NVIDIA GeForce RTX 2070 SUPER, mã hóa NVENC: 90 khung 1080 × 1440 và 90 khung preview 540 × 720; cả hai có âm thanh.
- Đọc khung hình ở giây 1: tiêu đề vàng/nền đen, PART đỏ/nền xanh ngọc; đếm pixel tại vùng tiêu đề và PART xác nhận đủ bốn màu trên cả hai kích thước.
- [Release public 1.3.5](https://github.com/x1-2023/template-studio/releases/tag/v1.3.5): ZIP 257.671.948 byte; digest GitHub khớp gói đã kiểm tra.
- Chạy updater thật **1.3.4 → 1.3.5** từ gói public: helper tải/xác minh/cài/mở lại thành công, có backup; giữ dữ liệu, font và màu tùy chỉnh cũ trong cấu hình, preset, hàng chờ. Chữ/nền PART kế thừa đúng hai màu tiêu đề cũ.
- EXE sau cập nhật render thêm 90 khung với màu riêng; khung hình đã giải mã trùng bản kiểm chứng trước phát hành.

Gói đã kiểm tra: `TemplateStudio-windows-x64.zip`, SHA-256:

```text
1cd327c9f6a9289989223df7cc0b7ece81fe79719b1d1cc7ce906ea591272765
```

Kết quả và kịch bản QA cục bộ nằm trong `.runtime/qa-colors-135/`, `.runtime/qa_colors_135.py`, `.runtime/qa-updater-135/`, `.runtime/qa_updater_135.py`; ảnh giao diện `.runtime/palette-135.png`. Dữ liệu/video/font riêng không nằm trong repository.
