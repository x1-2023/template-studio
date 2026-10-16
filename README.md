# Beta Render

Ứng dụng Windows xuất video hàng loạt bằng GPU. Luồng chính: **thêm video → chọn preset → Xuất video**. App nhớ preset và nơi lưu; mỗi video xuất thành một file, nguồn được giữ nguyên.

Mã nguồn [công khai GPL-3.0-only](https://github.com/x1-2023/template-studio). Dự án độc lập; xem [giấy phép thành phần](THIRD_PARTY_NOTICES.md).

## Dùng EXE

1. Tải `TemplateStudio-windows-x64.zip` trong [GitHub Releases](https://github.com/x1-2023/template-studio/releases/latest), giải nén toàn bộ rồi chạy `TemplateStudio.exe`. Tên file được giữ để tương thích updater; tên ứng dụng là **Beta Render**.
2. Lần đầu app kiểm tra GPU/FFmpeg. Nếu thiếu FFmpeg, app tải runtime Gyan đã xác minh SHA256; sau đó dùng offline. Cần Windows 10/11 x64 và driver OpenGL 3.3 trở lên.
3. Trong **Cài đặt**, nhập cache effect từ RAR/thư mục local một lần. Bản EXE công khai không chứa shader/LUT hay video CapCut. Trong workspace phát triển, app tự nhận cache handoff đã có và sao chép vào dữ liệu riêng.
4. Thêm video hoặc thư mục, chọn mẫu, bấm **Xuất video**. Có thể xem thử trước bằng **Xem thử 3 giây**. **Chọn thư mục** để chọn thư mục xuất.

## Preset và cấu hình

- Hiệu ứng **Lớp phủ ngũ giác lấp lánh** (`7491138615477685505`) và bộ lọc **Camera độ nét cao 2** (`7514206177195068689`) dùng tên theo tài liệu bàn giao CapCut. Preset có hậu tố 3:4/9:16 để phân biệt khung hình; mặc định tốc độ 1× và không tự lật ngang. **Nền mờ 9:16** chỉ xử lý bố cục.
- Preset **Lớp phủ ngũ giác lấp lánh · Đối chiếu 3:4** tái lập clip thử: 3:4, hflip, 1.02×. Đây là cấu hình riêng của clip tham chiếu.
- Profile Tiêu chuẩn 3:4 dùng H.264 VBR 9.65 Mb/s; Tiết kiệm dùng 60% bitrate đã chọn; Chất lượng cao dùng CQ18, dung lượng tùy nội dung. Preset 9:16 dùng 12 Mb/s đề xuất, chưa được chấm với source draft gốc.
- Giao diện gồm **Nguồn video → Cấu hình chung → Xem trước**. Bấm **Chỉnh cấu hình…** để mở cửa sổ lớn với các nhóm thu gọn; chỉnh bằng thanh kéo hoặc nhập số. **Lưu thay đổi** áp dụng cho video chưa xuất; **Hủy** bỏ lần chỉnh đó. Preview nằm bên phải; lưu preset và nhập/xuất JSON ngay trong cột cấu hình.
- Shader chạy GPU; NVENC tăng tốc mã hóa. Chọn mã hóa CPU vẫn cần OpenGL cho shader.

Preview và xuất dùng cùng engine. Preview 540px giúp xem nhanh; chất lượng ở kích thước full có thể khác do nội suy và sharpen phụ thuộc kích thước. Xem [báo cáo port GPU](CapCut_FFmpeg_Codex_Handoff/work/REPORT.md) và [đối chiếu dung lượng](CapCut_FFmpeg_Codex_Handoff/work/ENCODING_REPORT.md). Không tuyên bố tái tạo CapCut 1:1; chưa có model segmentation/stabilization/HDR gốc.

## Hàng đợi và dữ liệu

Nhập tối đa 200 video; chạy một job/lần, hiện tiến độ và ETA. Một nguồn lỗi không chặn các file tiếp theo. Tick checkbox để chạy nhóm chọn. **Bỏ khỏi danh sách** chỉ bỏ khỏi danh sách; **Ẩn video đã xuất** giữ nguyên file trên đĩa. **Xuất lại** đặt mục lỗi về hàng chờ; khi có checkbox chọn thì đặt các mục chọn về hàng chờ để xuất lại theo cấu hình hiện tại.

**Dừng sau video này** hoàn tất video hiện tại; **Dừng** hủy worker/FFmpeg và dọn partial của tác vụ. Mở lại app tiếp tục ở cấp file, không nối từ frame đang dở. Cấu hình của file đã hoàn tất được giữ khi đổi preset cho file đang chờ. Báo cáo JSON/CSV nằm cạnh video đầu ra; nhật ký worker có nút mở trong Cài đặt.

`production.json` lưu preset, cấu hình và hàng đợi mới; `session.json` của GUI cũ được giữ và sao lưu khi nhập sang giao diện mới. Dữ liệu mặc định trong `data/template-studio/` cạnh EXE; nếu không ghi được thì dùng `%LOCALAPPDATA%/TemplateStudio`. Có thể đặt `TEMPLATE_STUDIO_HOME`. Cache effect trong `runtime/capcut-cache/` của thư mục dữ liệu; `TEMPLATE_STUDIO_CAPCUT_CACHE` cho phép chỉ định cache để app nhập bản sao.

GUI thư viện Video-FX cũ vẫn mở được từ source bằng `python template_gui.py --library`; không ghép 150 filter CPU vào chuỗi GPU mới trong phiên bản này.

## Updater

App kiểm tra GitHub Releases khi mở, hoặc bấm **Cài đặt → Kiểm tra cập nhật → Cập nhật và mở lại**. Chỉ cập nhật lúc rảnh; kiểm tra SHA256 và cấu trúc ZIP trước khi thay EXE/thư viện. Giữ preset, queue, cache, runtime và video xuất. Helper giữ backup và phục hồi nếu bản mới không khởi động được; nhật ký nằm trong `.updates/` cạnh EXE.

EXE chưa ký Authenticode. SHA256 xác minh toàn vẹn gói tải xuống; nguồn phát hành cố định trong `template_studio/version.py`.

## Chạy source, kiểm thử và build

```powershell
py -3.14 -m venv .runtime/dev
.runtime/dev/Scripts/python.exe -m pip install -r requirements-lock.txt
.runtime/dev/Scripts/python.exe template_gui.py
```

Hoặc dùng `run_template.bat`; launcher chuẩn bị các dependency còn thiếu. Bản build được kiểm thử bằng Python 3.14 x64.

```powershell
$env:PYTHONUTF8 = '1'
.runtime/dev/Scripts/python.exe -m ruff check template_studio template_gui.py build_template.py tools tests --select F
.runtime/dev/Scripts/python.exe -m unittest discover -s tests -v
.runtime/dev/Scripts/python.exe template_gui.py --check --capture .runtime/production.png
.runtime/dev/Scripts/python.exe build_template.py
```

QA local có GPU/cache: `python tools/qa_production.py`; GUI với preview thật: `python tools/capture_production.py`. Không commit `.runtime`, dữ liệu, cache, video hay binary FFmpeg. CI public kiểm tra GUI/preset/queue/updater và worker đóng gói; GPU/cache được kiểm định trên máy local.

Đầu ra build: `release/template-studio/TemplateStudio/TemplateStudio.exe` và ZIP/checksum cạnh đó. Engine chung nằm trong `template_studio/gpu`; CLI trong `CapCut_FFmpeg_Codex_Handoff/work` là wrapper tương thích.

## Phát hành

Cập nhật `VERSION`, release notes, commit rồi đẩy tag `v<phiên bản>`. Workflow Windows kiểm tra, build, smoke test EXE/worker và public GitHub Release. Giữ tên asset `TemplateStudio-windows-x64.zip` để updater bản cũ nhận được bản mới. Không sửa asset của release đã công bố.
