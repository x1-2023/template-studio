# Logo Beta Render

Logo chữ B kết hợp nút phát và dải khung hình, dùng màu xanh ngọc của giao diện ứng dụng.

- `beta-render-logo.png`: ảnh gốc được tạo bằng công cụ tích hợp `image_gen`, nền trong suốt.
- `../../template_studio/assets/beta-render.png`: PNG 512 × 512 cho giao diện.
- `../../template_studio/assets/beta-render.ico`: biểu tượng Windows với các kích thước 16, 20, 24, 32, 40, 48, 64, 96, 128 và 256 px.

PNG và ICO được đổi kích thước/định dạng từ ảnh gốc bằng Pillow, không thêm thư viện chạy ứng dụng. PyInstaller nhúng ICO vào EXE và đóng gói tài nguyên GUI. Qt dùng cùng ICO cho thanh tiêu đề và taskbar.

## Mô tả dùng để tạo logo

Thiết kế một logo biểu tượng ứng dụng Windows hoàn chỉnh cho phần mềm dựng/xuất video tên Beta Render. Chỉ tạo MỘT biểu tượng vuông, không phải bảng ý tưởng hay mockup. Bố cục: một ô vuông bo góc lớn màu than xanh rất đậm #10181c, đặt giữa canvas vuông với khoảng trống trong suốt nhỏ xung quanh. Bên trong là một chữ B hình học độc đáo, chắc nét, được tạo từ hai hoặc ba dải khung hình xếp lớp; khoảng âm ở phần bụng dưới gợi một tam giác nút phát hướng sang phải. Biểu tượng mang cảm giác render video nhanh, gọn, chính xác. Màu chủ đạo xanh ngọc #73e9ce và xanh teal; có thể dùng chuyển sắc rất nhẹ giữa mint và teal trên chính biểu tượng. Phong cách thiết kế vector phẳng, hình học tối giản, đường biên sắc, cân bằng thị giác, chuyên nghiệp. Chữ B phải đọc được ngay khi thu nhỏ xuống 32px. Biểu tượng chiếm khoảng 65–70% chiều rộng ô nền. Không chữ tên app, không slogan, không chữ khác ngoài cấu trúc hình chữ B, không số, không watermark. Không dùng họa tiết AI hình sao, không tia lấp lánh, không neon glow, không bóng đổ ngoài ô, không 3D, không viền mảnh. Nền ngoài ô bo góc phải trong suốt thật; giữ alpha. Tạo ảnh vuông độ phân giải cao dùng được trực tiếp làm icon phần mềm. Không sao chép logo CapCut hoặc thương hiệu khác.
