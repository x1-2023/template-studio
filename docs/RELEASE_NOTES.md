Beta Render 1.2.0 dùng được trên máy mới mà không phải nhập gói hiệu ứng.

- Đóng kèm 22 shader/LUT/texture cần dùng cho ngũ giác và Camera, kiểm tra bằng manifest SHA256. Không cần cài CapCut hay chọn file RAR/cache.
- FFmpeg tự tải và xác minh trong lần mở đầu nếu chưa có; cần mạng lần đầu, sau đó dùng offline.
- Tự kiểm tra cập nhật khi mở và mỗi 4 giờ. Nếu máy đang chuẩn bị runtime hoặc render, chờ tới lúc rảnh để kiểm tra.
- Có bản mới sẽ hiện **Cập nhật app** trên màn hình chính; tải, xác minh, cài và mở lại trong ứng dụng.
- Kiểm tra `--check-gpu` xác nhận cả GPU và gói hiệu ứng, ngoài kiểm tra GUI/worker hiện có.

Windows 10/11 x64, driver hỗ trợ OpenGL 3.3 trở lên. NVIDIA NVENC được dùng tự động nếu sẵn có; hàng đợi vẫn xử lý từng video. Giữ logo, cấu hình, preset, hàng đợi và video đã xuất khi cập nhật.
