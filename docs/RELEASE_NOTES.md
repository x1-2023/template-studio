Beta Render 1.2.1 sửa lỗi dừng render khi Windows khóa file tiến độ.

- Ghi JSON bằng file tạm riêng, thử lại khi Windows báo Access is denied. Nếu chưa ghi được tiến độ, video vẫn tiếp tục render; cấu hình và kết quả vẫn báo lỗi khi không lưu được.
- Sửa lỗi đóng pipe che mất lỗi gốc thành `[Errno 22] Invalid argument`.
- Thư mục xuất chỉ nhận MP4. Log, thống kê render và báo cáo lượt chạy được lưu trong thư mục nhật ký của app.
- Cất log/báo cáo của bản cũ đã nhận diện vào `cache/workers/archived-exports/`, giữ nguyên MP4 và file khác của người dùng.
- Chọn video lỗi rồi bấm **Nhật ký lỗi** để mở đúng log. Tên file tạm ngắn hơn để tránh kéo dài đường dẫn theo tên video.

Cập nhật từ app bằng **Cập nhật app**, hoặc tải ZIP và giải nén toàn bộ. Giữ cấu hình, preset, hàng đợi và video đã xuất. Hàng đợi vẫn xử lý lần lượt; bấm **Xuất lại** để chạy lại video lỗi.

Windows 10/11 x64, driver OpenGL 3.3 trở lên. Hiệu ứng có sẵn, FFmpeg tự tải và xác minh ở lần mở đầu nếu thiếu; cần mạng lần đầu, sau đó dùng offline.
