Template Studio 1.1.1 mở rộng khu vực chỉnh cấu hình ngay trên màn hình chính. Danh sách video gọn thành một cột bên trái; cấu hình chia nhóm ở giữa và preview ở bên phải. Chữ và điều khiển lớn hơn; nhóm cấu hình tự xếp một cột khi cửa sổ hẹp. Tài nguyên/GPU/updater nằm trong mục Tài nguyên & cập nhật. Giữ preset, hàng đợi, engine GPU và dữ liệu của bản 1.1.0.

Các chức năng từ bản 1.1.0:

- Engine OpenGL nhiều pass dùng chung với CLI, H.264 NVENC hoặc mã hóa CPU; preset ngũ giác 3:4/9:16, màu/nét, chỉ bố cục và đối chiếu mẫu. Preset sản xuất mặc định 1×, không tự lật ngang.
- Preview 3 giây hoặc từ thời điểm tùy chọn, xem nguồn/kết quả và mở file xuất. Có VBR theo ngân sách bitrate hoặc CQ18; profile 3:4 tiêu chuẩn dùng 9.65 Mb/s.
- Hàng đợi tối đa 200 video, chạy tuần tự, snapshot cấu hình theo file, giữ video đã hoàn tất, tiếp tục sau khi mở lại, chọn mục, chạy lại lỗi, dừng sau file hoặc dừng ngay. Có báo cáo JSON/CSV.
- Preset riêng: lưu mẫu, nhập/xuất JSON, chỉnh bố cục/màu/nét/tốc độ/audio. Video nguồn không bị ghi đè; đầu ra dùng tên riêng.
- Worker chạy trong process riêng của EXE, không cần Python. Cache effect nhập một lần từ RAR hoặc thư mục local; ZIP công khai không chứa shader/LUT CapCut. Sau khi chuẩn bị FFmpeg và cache, render offline. Cần driver OpenGL 3.3; mã hóa CPU không thay thế GPU shader.
- Updater GitHub Releases giữ SHA256, kiểm tra ZIP, backup/rollback và bảo toàn dữ liệu/preset/hàng đợi/runtime/cache.

Đã kiểm thử local: batch 20 clip gồm 18 nguồn hợp lệ và 2 nguồn lỗi; Unicode/tên trùng; snapshot/khôi phục; preview; hủy không còn partial. Kiểm tra GPU shader, GUI, EXE và updater có bài kiểm thử riêng. 9:16 chưa đối chiếu source draft gốc; segmentation, stabilization và HDR của CapCut chưa được tái tạo chính xác.

Mã nguồn GPL-3.0-only. Bản Windows x64 portable: giải nén toàn bộ ZIP rồi chạy TemplateStudio.exe. EXE chưa ký Authenticode.
