# Template Studio

Ứng dụng Windows xử lý video dọc 9:16, nền mờ, hiệu ứng mở đầu mô phỏng pha lê và thư viện 150 preset Video-FX. Nhập tối đa 200 video, dùng chung cấu hình và xuất tuần tự; không ghi đè video nguồn.

Mã nguồn công khai theo **GPL-3.0-only**. Dự án độc lập, không liên kết với CapCut. Xem [đánh giá và cải tiến](docs/REVIEW.md) và [giấy phép thành phần](THIRD_PARTY_NOTICES.md).

## Dùng bản EXE

1. Tải TemplateStudio-windows-x64.zip trong [GitHub Releases](https://github.com/x1-2023/template-studio/releases/latest).
2. Giải nén toàn bộ thư mục và chạy TemplateStudio.exe; cần Windows 10/11 x64.
3. Nếu máy chưa có FFmpeg, lần mở đầu app tải bản Gyan 7.1.1 trực tiếp từ nhà phát hành, kiểm tra SHA-256 và chuẩn bị runtime. Cần khoảng 600 MiB trống cho bước này. Sau đó xử lý video offline.
4. Thêm video → **Thư viện filter** → chọn nhóm/tìm tên → chọn một mục → chỉnh cường độ/thời gian → **Preview video 8 giây** → **Áp dụng vào cấu hình** → **Xuất tất cả**.

Double click một mục để áp dụng nhanh. Thumbnail dùng cường độ 65%; tạo lại thumbnail để lấy hình từ video đang chọn. Nếu chưa thêm video, thư viện dùng ảnh mẫu. Thay đổi bản nháp trong thư viện chưa đổi cấu hình xuất cho đến khi áp dụng.

Video-FX có các nhóm glitch, VHS, màu điện ảnh, camera/ống kính, ánh sáng/hạt/thời tiết và nghệ thuật. 150 tên preset dùng chung các engine; hiện chọn một filter tại một thời điểm. Các filter xử lý CPU; NVENC hỗ trợ phần mã hóa nếu GPU dùng được.

Hiệu ứng pha lê hiện là mô phỏng PNG/blur/fade, **chưa khớp chính xác effect CapCut trong video tham chiếu**.

## Dữ liệu và cập nhật

- Dữ liệu mặc định: data/template-studio/ cạnh EXE. Nếu không ghi được, app dùng %LOCALAPPDATA%/TemplateStudio. Có thể chỉ định bằng TEMPLATE_STUDIO_HOME.
- session.json lưu cấu hình, hàng đợi và thư mục xuất; video xuất mặc định trong exports/ của thư mục dữ liệu.
- Bản EXE kiểm tra GitHub Releases khi mở app; cũng có nút **Kiểm tra cập nhật**.
- Khi có bản mới: **Cài và khởi động lại**. App chỉ cập nhật khi không có tác vụ đang chạy, xác minh SHA-256 do GitHub công bố và kiểm tra cấu trúc ZIP trước khi thay file.
- Updater giữ cấu hình, video xuất và runtime FFmpeg. Nếu bản mới không báo khởi động thành công, helper phục hồi bản cũ.
- Nhật ký và bản sao phục hồi: .updates/ cạnh EXE. Staging cùng ổ với app, kể cả khi dữ liệu ở ổ khác. Có thể xóa các thư mục cập nhật cũ khi đã xác nhận app chạy ổn để thu hồi dung lượng.
- EXE chưa ký Authenticode. SHA-256 bảo vệ toàn vẹn tải xuống; độ tin cậy phát hành phụ thuộc repository GitHub đã cấu hình.

## Chạy từ source

Khuyến nghị Python 3.14 x64 trên Windows. Launcher hỗ trợ Python 3.11 trở lên với dependency tương thích.

    py -3.14 template_gui.py

Hoặc chạy run_template.bat. Launcher tự chuẩn bị dependency cục bộ nếu thiếu. Để dùng môi trường riêng và các phiên bản đã kiểm thử:

    py -3.14 -m venv .runtime/dev
    .\.runtime\dev\Scripts\python.exe -m pip install -r requirements-lock.txt
    .\.runtime\dev\Scripts\python.exe template_gui.py

Không commit dữ liệu cá nhân, video nguồn, cache hoặc binary FFmpeg. Repository chỉ chứa mã nguồn và cấu hình phát hành.

## Kiểm thử và build EXE

    $env:PYTHONUTF8 = "1"
    .\.runtime\dev\Scripts\python.exe tools/prepare_media.py
    .\.runtime\dev\Scripts\python.exe -m ruff check template_studio template_gui.py build_template.py tools tests --select F
    .\.runtime\dev\Scripts\python.exe -m unittest discover -s tests -v
    .\.runtime\dev\Scripts\python.exe template_gui.py --check --library --capture .runtime/gallery.png
    .\.runtime\dev\Scripts\python.exe build_template.py

Kết quả trong release/template-studio/: thư mục portable, ZIP và file .sha256. Gói phát hành không chứa FFmpeg; app tự chuẩn bị nếu máy đích chưa có.

## Phát hành phiên bản mới

Sửa VERSION trong template_studio/version.py và cập nhật docs/RELEASE_NOTES.md, commit rồi đẩy tag khớp phiên bản:

    git add template_studio/version.py docs/RELEASE_NOTES.md
    git commit -m "Phát hành phiên bản 1.0.1"
    git tag v1.0.1
    git push origin main
    git push origin v1.0.1

Workflow Windows chạy kiểm thử, build, kiểm tra EXE rồi tải ZIP/checksum lên GitHub Releases. Không nhúng token vào app. Repository cố định cho updater nằm trong template_studio/version.py; nếu fork, đổi REPOSITORY trước khi build.
