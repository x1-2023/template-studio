# Thành phần và giấy phép bên thứ ba

Mã nguồn Beta Render do dự án cung cấp được cấp phép GPL-3.0-only; xem `LICENSE`. Tài nguyên bên thứ ba được ghi riêng bên dưới, không tự động thuộc giấy phép GPL của mã dự án. Không có quan hệ tài trợ hoặc liên kết chính thức với CapCut.

| Thành phần | Phiên bản / nguồn | Giấy phép |
| --- | --- | --- |
| Video-FX | [commit 7513159](https://github.com/tomastimelock/video-fx/tree/751315965bc5e740b62136153ec4a9bf4e21ea20) | MIT, bản quyền 2026 Trollfabriken AITrix AB |
| PySide6 / Shiboken6 / Qt | 6.11.2, [mã nguồn Qt for Python](https://code.qt.io/cgit/pyside/pyside-setup.git/), [mã nguồn Qt](https://code.qt.io/cgit/qt/) | Các lựa chọn GPL/LGPL và thông báo riêng của Qt |
| Pillow | 12.2.0, [mã nguồn](https://github.com/python-pillow/Pillow) | HPND và giấy phép của thư viện đi kèm |
| NumPy | Xem requirements-lock.txt, [mã nguồn](https://github.com/numpy/numpy) | BSD và giấy phép của thư viện đi kèm |
| ModernGL | 5.13.0, [mã nguồn](https://github.com/moderngl/moderngl) | MIT |
| glcontext | 3.1.0, [mã nguồn](https://github.com/moderngl/glcontext) | MIT |
| OpenCV headless | Xem requirements-lock.txt, [mã nguồn](https://github.com/opencv/opencv-python), [OpenCV](https://github.com/opencv/opencv) | Apache-2.0 và giấy phép của thư viện đi kèm |
| Pydantic | Xem requirements-lock.txt, [mã nguồn](https://github.com/pydantic/pydantic) | MIT |
| Python | 3.14 khi build bản Windows, [mã nguồn](https://www.python.org/downloads/source/) | PSF và giấy phép kèm theo |
| PyInstaller | Chỉ dùng để build, [mã nguồn](https://github.com/pyinstaller/pyinstaller) | GPL với ngoại lệ phân phối bootloader |

Bản EXE giữ nguyên thư viện liên kết động. Thông báo giấy phép lấy từ các wheel và danh sách phiên bản/đường dẫn mã nguồn được đóng trong `_internal/licenses/`, gồm `package-sources.json`. Mã nguồn của app có tại [repository công khai](https://github.com/x1-2023/template-studio); source dependency không sửa đổi có tại các dự án gốc và các bản phân phối source trên PyPI ghi trong danh sách này.

FFmpeg không được commit vào Git và không nằm trong ZIP phát hành của app. Nếu máy chưa có FFmpeg, app tải trực tiếp bản [Gyan 7.1.1 essentials](https://github.com/GyanD/codexffmpeg/releases/tag/7.1.1), kiểm tra SHA-256 của ZIP và từng EXE rồi lưu vào thư mục dữ liệu. Đây là bản GPLv3 theo [nhà phát hành Gyan](https://www.gyan.dev/ffmpeg/builds/); [mã nguồn FFmpeg n7.1.1](https://github.com/FFmpeg/FFmpeg/tree/n7.1.1) và [thông tin giấy phép FFmpeg](https://ffmpeg.org/legal.html). Người phân phối lại runtime cần xử lý các nghĩa vụ tương ứng cho cả FFmpeg và thư viện mà nó liên kết.

Catalog gồm 150 preset của Video-FX, nhiều preset dùng chung engine. Không đồng nghĩa có 150 thuật toán khác nhau. Adapter của Template Studio xử lý tuần tự từng frame, bổ sung trạng thái cho các preset giữ/đóng băng frame để không nạp toàn bộ video vào RAM. Không sửa source package upstream.

Frei0r, GL Transitions, FFmpeg GL Effects, FFmpeg Concat và Crazy Video Glitch Editor đã được xem xét, hiện chưa được đóng kèm hoặc gọi trong pipeline của bản này.

Từ bản 1.2.0, `template_studio/assets/effects/` chứa bản sao tối thiểu 22 shader/LUT/texture của hai tài nguyên CapCut `7491138615477685505` và `7514206177195068689`, lấy từ gói cache người dùng cung cấp để app chạy mà không cần nhập thủ công. Manifest lưu SHA256 từng file. Giữ nguyên nội dung các tài nguyên; không kèm model, Lua, scene, project, video hay dữ liệu cá nhân. Các tài nguyên này không được cấp lại GPL bởi dự án; gói cache nguồn không kèm một giấy phép mã nguồn mở riêng cho chúng. Mã adapter và công cụ đóng gói không chuyển quyền sở hữu tài nguyên CapCut. Cache riêng của người dùng vẫn được giữ trong dữ liệu khi cập nhật.
