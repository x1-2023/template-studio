# Màu tiêu đề và PART — 1.3.5

Trong **Chỉnh cấu hình → Phụ đề karaoke**, bốn mục độc lập là **Chữ tiêu đề**, **Nền tiêu đề**, **Chữ PART**, **Nền PART**. Mỗi mục màu, kể cả màu phụ đề, có 10 ô chọn nhanh, nút mở bảng màu tùy ý và ô HEX.

`part_color` và `part_background` được lưu trong cấu hình/preset. Khi đọc preset cũ thiếu hai trường này, app lấy đúng màu tiêu đề đã lưu; không đổi sang màu mặc định. Đổi màu PART sau đó không tác động tiêu đề. Preview và xuất truyền cùng các giá trị xuống hai style ASS riêng.

## Kiểm chứng

- 105 kiểm thử trên máy Windows: qua; [CI Windows](https://github.com/x1-2023/template-studio/actions/runs/39373270811) cũng qua. Ruff F và `git diff --check`: qua.
- Kiểm thử GUI bấm các ô màu, lưu thay đổi, lưu preset và hủy lần chỉnh tiếp theo. Thử cả cửa sổ 1100 × 720.
- EXE giải nén từ ZIP phát hành, PATH chỉ có Windows; dùng bộ FFmpeg riêng đã xác minh, chặn mạng khi kiểm tra khởi động/render.
- GPU NVIDIA GeForce RTX 2070 SUPER, mã hóa NVENC: 90 khung 1080 × 1440 và 90 khung preview 540 × 720; cả hai có âm thanh.
- Đọc khung hình ở giây 1: tiêu đề vàng/nền đen, PART đỏ/nền xanh ngọc; đếm pixel tại vùng tiêu đề và PART xác nhận đủ bốn màu trên cả hai kích thước.

Gói đã kiểm tra: `TemplateStudio-windows-x64.zip`, SHA-256:

```text
1cd327c9f6a9289989223df7cc0b7ece81fe79719b1d1cc7ce906ea591272765
```

Kết quả và kịch bản QA cục bộ nằm trong `.runtime/qa-colors-135/`, `.runtime/qa_colors_135.py`; ảnh giao diện `.runtime/palette-135.png`. Dữ liệu/video/font riêng không nằm trong repository.
