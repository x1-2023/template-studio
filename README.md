# Beta Render

<img src="template_studio/assets/beta-render.png" alt="Logo Beta Render" width="96" height="96">

Ứng dụng Windows xuất video hàng loạt bằng GPU. Luồng chính: **thêm video → chọn preset → Xuất video**. App nhớ preset và nơi lưu; mỗi video xuất thành một file, nguồn được giữ nguyên.

Mã nguồn [công khai GPL-3.0-only](https://github.com/x1-2023/template-studio). Dự án độc lập; xem [giấy phép thành phần](THIRD_PARTY_NOTICES.md).

[Logo gốc và các định dạng sử dụng trong ứng dụng](docs/brand/README.md).

## Dùng EXE

1. Tải `TemplateStudio-windows-x64.zip` trong [GitHub Releases](https://github.com/x1-2023/template-studio/releases/latest), giải nén toàn bộ rồi chạy `TemplateStudio.exe`. Tên file được giữ để tương thích updater; tên ứng dụng là **Beta Render**.
2. Lần đầu app kiểm tra GPU/FFmpeg. Nếu thiếu FFmpeg, app tự tải runtime Gyan đã xác minh SHA256; cần mạng cho lần chuẩn bị này, sau đó dùng offline. Cần Windows 10/11 x64 và driver OpenGL 3.3 trở lên.
3. Hiệu ứng ngũ giác và bộ lọc Camera đã có sẵn trong gói app, không cần cài CapCut hay nhập RAR/cache thủ công. Gói chỉ chứa 22 shader/LUT/texture renderer sử dụng, có manifest SHA256; không kèm video, project hoặc dữ liệu người dùng. Mục nhập hiệu ứng trong **Cài đặt** được giữ như tùy chọn nâng cao.
4. Thêm video hoặc thư mục, chọn mẫu, bấm **Xuất video**. Có thể xem thử trước bằng **Xem thử 3 giây**. **Chọn thư mục** để chọn thư mục xuất.

## Preset và cấu hình

- Màn hình chính dành cho **TikTok: video dọc 9:16, 1080 × 1920, 30 FPS**, MP4/H.264 và âm thanh AAC. [TikTok khuyến nghị video dọc 9:16 và xuất 1080 × 1920](https://ads.tiktok.com/business/en/guides/video-advertising-guide).
- Mặc định **TikTok · Ngũ giác + Camera** bật đồng thời **Lớp phủ ngũ giác lấp lánh** (`7491138615477685505`) và **Camera độ nét cao 2** (`7514206177195068689`), tốc độ 1×, không lật ngang. Một preset lưu chung hiệu ứng, bộ lọc, bố cục và thiết lập xuất.
- **TikTok · Chỉ bộ lọc Camera** tắt hiệu ứng mở đầu; **TikTok · Chỉ nền mờ** tắt cả hiệu ứng và bộ lọc. Cả ba đều dùng 9:16. Preset tự lưu vẫn được giữ.
- Profile Tiêu chuẩn TikTok dùng H.264 VBR 12 Mb/s; Tiết kiệm dùng 60% bitrate đã chọn; Chất lượng cao dùng CQ18, dung lượng tùy nội dung.
- **Cài đặt → Dùng cấu hình video mẫu 3:4** mở cấu hình đối chiếu riêng: 1080 × 1440, lật ngang, 1.02× và 9.65 Mb/s theo cặp nguồn–CapCut. Mẫu này được giữ để kiểm tra kết quả, không nằm trong danh sách TikTok chính. Bố cục 9:16 dựa trên draft, chưa có cặp video draft gốc để chấm độ giống.
- Giao diện gồm **Nguồn video → Cấu hình chung → Xem trước**. Bấm **Chỉnh cấu hình…** để mở cửa sổ lớn với các nhóm thu gọn; chỉnh bằng thanh kéo hoặc nhập số. **Lưu thay đổi** áp dụng cho video chưa xuất; **Hủy** bỏ lần chỉnh đó. Preview nằm bên phải; lưu preset và nhập/xuất JSON ngay trong cột cấu hình.
- Shader chạy GPU; NVENC tăng tốc mã hóa. Chọn mã hóa CPU vẫn cần OpenGL cho shader.

Preview và xuất dùng cùng engine. Preview 540px giúp xem nhanh; chất lượng ở kích thước full có thể khác do nội suy và sharpen phụ thuộc kích thước. Xem [báo cáo port GPU](CapCut_FFmpeg_Codex_Handoff/work/REPORT.md) và [đối chiếu dung lượng](CapCut_FFmpeg_Codex_Handoff/work/ENCODING_REPORT.md). Không tuyên bố tái tạo CapCut 1:1; chưa có model segmentation/stabilization/HDR gốc.

## Hàng đợi và dữ liệu

Nhập tối đa 200 video; chạy một job/lần, hiện tiến độ và ETA. Một nguồn lỗi không chặn các file tiếp theo. Tick checkbox để chạy nhóm chọn. **Bỏ khỏi danh sách** chỉ bỏ khỏi danh sách; **Ẩn video đã xuất** giữ nguyên file trên đĩa. **Xuất lại** đặt mục lỗi về hàng chờ; khi có checkbox chọn thì đặt các mục chọn về hàng chờ để xuất lại theo cấu hình hiện tại.

**Dừng sau video này** hoàn tất video hiện tại; **Dừng** hủy worker/FFmpeg và dọn partial của tác vụ. Mở lại app tiếp tục ở cấp file, không nối từ frame đang dở. Cấu hình của file đã hoàn tất được giữ khi đổi preset cho file đang chờ. Báo cáo JSON/CSV nằm cạnh video đầu ra; nhật ký worker có nút mở trong Cài đặt.

`production.json` lưu preset, cấu hình và hàng đợi mới; `session.json` của GUI cũ được giữ và sao lưu khi nhập sang giao diện mới. Dữ liệu mặc định trong `data/template-studio/` cạnh EXE; nếu không ghi được thì dùng `%LOCALAPPDATA%/TemplateStudio`. Có thể đặt `TEMPLATE_STUDIO_HOME`. Tài nguyên mặc định nằm trong `template_studio/assets/effects/` của gói app; cache tùy chọn của người dùng nằm trong `runtime/capcut-cache/` của thư mục dữ liệu. `TEMPLATE_STUDIO_CAPCUT_CACHE` cho phép chỉ định cache riêng.

Lần đầu dùng bản mặc định TikTok, cấu hình hiện tại và video chưa xuất được chuyển sang khung 9:16, giữ các thông số hiệu ứng, âm thanh, tốc độ và vị trí đã chỉnh. `production-before-tiktok.json` giữ bản sao trước khi chuyển. Cấu hình của video hoàn tất và các preset tự lưu không bị ghi đè. Cấu hình đối chiếu 3:4 được chọn sau đó vẫn giữ qua các lần mở app.

GUI thư viện Video-FX cũ vẫn mở được từ source bằng `python template_gui.py --library`; không ghép 150 filter CPU vào chuỗi GPU mới trong phiên bản này.

## Updater

App tự kiểm tra GitHub Releases khi mở và mỗi 4 giờ. Nếu đang tải FFmpeg hoặc xuất video, việc kiểm tra được chờ tới lúc rảnh. Có bản mới sẽ hiện **Cập nhật app** ở màn hình chính; bấm để app tải, xác minh SHA256 và tự cài/mở lại. Cũng có thể kiểm tra thủ công trong **Cài đặt**. Giữ preset, queue, cache riêng, runtime và video xuất. Helper giữ backup và phục hồi nếu bản mới không khởi động được; nhật ký nằm trong `.updates/` cạnh EXE. Tài nguyên mặc định được cập nhật cùng app.

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

QA local có GPU: `python template_gui.py --check-gpu`; GUI với preview thật: `python tools/capture_production.py`. Không commit `.runtime`, dữ liệu, cache cá nhân, video hay binary FFmpeg. CI public kiểm tra GUI/preset/queue/updater, gói hiệu ứng và worker đóng gói; render GPU được kiểm định trên máy local. `tools/prepare_effect_assets.py` tái tạo gói 22 file từ cache nguồn khi cần cập nhật tài nguyên.

Đầu ra build: `release/template-studio/TemplateStudio/TemplateStudio.exe` và ZIP/checksum cạnh đó. Engine chung nằm trong `template_studio/gpu`; CLI trong `CapCut_FFmpeg_Codex_Handoff/work` là wrapper tương thích.

## Phát hành

Cập nhật `VERSION`, release notes, commit rồi đẩy tag `v<phiên bản>`. Workflow Windows kiểm tra, build, smoke test EXE/worker và public GitHub Release. Giữ tên asset `TemplateStudio-windows-x64.zip` để updater bản cũ nhận được bản mới. Không sửa asset của release đã công bố.
