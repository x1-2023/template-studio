# Kế hoạch GUI xuất video hàng loạt và EXE có updater

Ngày lập: 16/10/2026. GUI mới và EXE 1.1.0 đã triển khai, kiểm định local; kế hoạch dưới đây được giữ để tra cứu định hướng ban đầu.

Theo yêu cầu đơn giản hóa sau đó, bản thực tế dùng một màn hình. Bản 1.1.1 thu danh sách video thành một cột gọn bên trái, đưa cấu hình preset ra khu vực lớn ở giữa, preview bên phải và nút Chạy phía dưới. Ngăn Tài nguyên & cập nhật chỉ dành cho cache/GPU/runtime/updater. Chưa thêm thẻ preset/thumbnail, tìm kiếm, giữ tỷ lệ nguồn, mẫu tên tùy chỉnh, giữ cây thư mục, HEVC hay mask ngoài vào GUI.

Đã kiểm tra 22 bài unittest, regression GPU/CLI, batch thật 20 clip (18 hợp lệ, 2 nguồn hỏng), preview, hủy/dọn partial, khôi phục hàng đợi, EXE render trên RTX 2070 Super và nâng cấp EXE thật 1.0.0 → 1.1.0 giữ preset/cache/output. Các checklist dưới đây là phạm vi dự kiến, không phải danh sách tính năng đã nghiệm thu toàn bộ. Xem README và release notes cho hành vi đã phát hành.

## Hướng thực hiện

Nâng cấp GUI PySide6/QML hiện có để dùng renderer GPU đã kiểm định. Luồng chính: **chọn preset → thêm video/thư mục → chọn nơi lưu → xuất hàng loạt**. Tách cấu hình nâng cao khỏi luồng này; preset và nơi xuất gần nhất được nhớ cho lần mở sau.

Giữ updater GitHub Releases, hàng đợi tuần tự, thư viện filter và cơ chế bảo vệ nguồn đang có. Đưa engine GPU về module dùng chung để GUI, CLI và EXE chạy cùng mã xử lý, không duy trì hai phiên bản renderer khác nhau.

## Hiện trạng đã xác minh

| Thành phần | Đã có | Cần bổ sung |
|---|---|---|
| GUI | PySide6/QML, kéo thả, nhập file/thư mục, preview, tối đa 200 video | Chọn preset sản xuất, tỷ lệ khung linh hoạt, preview đúng engine GPU |
| Hàng đợi | Chạy tuần tự, phần trăm/ETA từng file, dừng, lỗi một file vẫn chạy tiếp | Snapshot cấu hình theo job, tiếp tục phiên trước, chạy lại mục lỗi, tổng tiến độ |
| Engine | Port GPU và CLI chạy thật, H.264 NVENC/libx264, skin fallback, VBR tùy chọn | API dùng chung, worker đóng gói được, hủy an toàn, đường dẫn runtime từ app |
| Preset | JSON case B 3:4 và case A 9:16 | Catalog có tên/ảnh/tóm tắt; preset tùy chỉnh; tách cấu hình đối chiếu khỏi sản xuất |
| Build | PyInstaller onedir, ZIP portable, CI Windows, kiểm tra EXE | Đóng ModernGL/glcontext, kiểm tra worker trong EXE không cần Python |
| Updater | GitHub Releases, SHA256, ZIP validation, backup/rollback | Migration cấu hình/job, giữ asset local, kiểm tra sức khỏe bản GPU |

Renderer GUI hiện tại vẫn là mô phỏng pha lê cũ. CLI GPU chưa được tích hợp vào EXE 1.0.0.

## Phạm vi

**Trong bản 1.1.0:** GUI phục vụ xuất hàng loạt; preset GPU có sẵn và tùy chỉnh; preview; queue có lưu trạng thái; cấu hình chất lượng/dung lượng; quản lý asset local; EXE portable x64; updater từ bản 1.0.0; báo cáo kết quả và chẩn đoán.

**Để sau bản đầu:** timeline, render farm, nhiều job GPU đồng thời, lịch chạy/watch folder, chuỗi nhiều filter Video-FX, chuyển cảnh giữa nhiều clip, stabilization/motion blur/HDR chính xác của CapCut. Không coi bản 9:16 chưa có source gốc là đã kiểm định tương đương case B.

## Giao diện đề xuất

Ba khu vực chính trên trang Sản xuất:

- **Trái — danh sách video:** thêm video/thư mục, kéo thả, chọn nhiều, tìm/lọc theo trạng thái, xóa mục khỏi danh sách. Hiện thumbnail, thời lượng, kích thước, preset gán, tiến độ và kết quả của từng job.
- **Giữa — preset và preview:** chọn preset dạng thẻ, tóm tắt khung/hiệu ứng/màu/chất lượng. Preview 3 giây đầu và một đoạn tùy chọn, phát/dừng/tua; xem nguồn hoặc kết quả. Hiển thị khi preview đã cũ sau khi đổi cấu hình. Nút mở video bằng trình phát hệ thống.
- **Phải — xuất:** nơi lưu, preset chất lượng, ước tính dung lượng theo thời lượng/bitrate, tổng job chờ/đang chạy/lỗi/hoàn tất, tổng tiến độ có trọng số thời lượng, nút bắt đầu/dừng sau file hiện tại/dừng ngay.

Khu vực Cấu hình nâng cao mở khi cần; trang Thiết lập quản lý runtime/cache/cập nhật. Giữ thư viện 150 filter hiện có; chế độ cũ vẫn mở được. Bản đầu không hứa ghép mọi filter CPU vào chuỗi GPU mới.

## Bộ preset ban đầu

| Preset | Thiết lập chính | Ghi chú |
|---|---|---|
| Ngũ giác 3:4 | 1080×1440, 30 fps, intro ngũ giác và LUT, playback 1× | Mặc định sản xuất; không tự lật ngang. Dựa trên renderer đã thử nhưng không tự áp thông số thời gian của clip mẫu |
| Ngũ giác 9:16 | 1080×1920, 30 fps, intro/LUT, playback 1× | Kế thừa layout draft, cho sửa scale/offset; đánh dấu chưa đối chiếu source case A |
| Màu và nét | Intro tắt, LUT/sharpen bật, playback 1× | Chọn 3:4 hoặc 9:16 |
| Chỉ bố cục | Nền mờ và clip chính, intro/LUT tắt | Phù hợp tạo hàng loạt bản có cùng bố cục |
| Đối chiếu mẫu 3:4 | hflip, playback 1.02×, scale 1.0513, VBR 9.65 Mb/s | Preset riêng để tái lập kết quả tham chiếu; không dùng làm mặc định cho video mới |

Ba lựa chọn xuất: **Tiết kiệm**, **Tiêu chuẩn**, **Chất lượng cao**. Tiêu chuẩn 3:4 dùng H.264 VBR 9.65 Mb/s đã đo; preset 9:16 cần thử bitrate riêng vì số pixel cao hơn. Tiết kiệm sẽ được chốt sau thử nén; Chất lượng cao dùng CQ18 và ghi rõ dung lượng thay đổi theo nội dung. H.264 mặc định; HEVC chỉ bật khi phát hiện encoder tương ứng và có kiểm thử. Không tự chuyển codec để đạt đúng một kích thước file.

Preset hệ thống không ghi đè. Người dùng có thể nhân bản, đặt tên, lưu preset riêng, khôi phục mặc định và nhập/xuất JSON đã kiểm tra schema. Thiết lập nâng cao không nhận lệnh shell hoặc mã shader tùy ý từ JSON.

## Cấu hình được mở cho người dùng

- Khung 9:16/3:4/giữ tỷ lệ nguồn; 720 hoặc 1080 theo cạnh ngang cho các khung định sẵn; hiển thị kích thước thật. FPS 30 mặc định.
- Scale clip, vị trí X/Y, lật ngang, cường độ nền mờ, playback speed. Tốc độ clip và slider effect có nhãn riêng để tránh nhầm.
- Bật/tắt intro, thời điểm bắt đầu, thời lượng segment, độ mạnh/khẩu độ; giới hạn theo khoảng engine hỗ trợ.
- Bật/tắt LUT, intensity, sharpness; skin fallback mặc định none. Chroma là tùy chọn nâng cao có mô tả; mask ngoài cần đúng tọa độ và timeline.
- Encoder Tự động/NVENC/CPU; H.264, bitrate hoặc CQ; giữ/tắt audio, bitrate audio. Nếu GPU mã hóa không dùng được, báo rõ chuyển sang mã hóa CPU; shader vẫn cần OpenGL.
- Mẫu tên `{ten_goc}_{preset}_{so_thu_tu}`, giữ cấu trúc thư mục con nếu chọn, chống trùng tên. Không ghi đè nguồn; đầu ra trùng tự tăng hậu tố.
- Kiểm tra nguồn thiếu/hỏng, quyền ghi, dung lượng đĩa, asset/driver trước khi bắt đầu batch. Dung lượng dự kiến từ VBR là ước tính, không cam kết số byte.

## Checklist triển khai theo thứ tự

- [ ] **Chốt schema cấu hình và job:** thêm phiên bản schema; ánh xạ preset có sẵn; tạo snapshot cấu hình/engine version/source identity cho mỗi job; giữ bản sao trước migration `session.json`. Mục hoàn tất không bị đưa về hàng chờ chỉ vì người dùng chọn preset cho batch mới.
- [ ] **Đưa engine GPU về module dùng chung:** chuyển `gpu.py`, phần render và tra cứu asset vào `template_studio/gpu/`; CLI hiện tại thành wrapper giữ tương thích. Bổ sung progress có cấu trúc, preview offset đúng timeline và hủy qua `managed_process`. Giữ thuật toán shader đã kiểm định.
- [ ] **Thêm worker EXE và kiểm tra runtime:** chạy render trong process riêng, dispatch `TemplateStudio.exe --render-worker` trước khi nạp GUI; trao đổi JSON/progress; không cần Python ngoài máy đích. Kiểm tra OpenGL, NVENC và asset; lỗi driver/worker không làm cửa sổ chính chết theo.
- [ ] **Xây catalog và quản lý preset:** thẻ preset, bản nháp chỉnh sửa, áp dụng vào lựa chọn/cả danh sách, lưu/nhân bản/nhập/xuất preset riêng; mặc định production 1×. Tách preset đối chiếu 1.02× khỏi luồng thông thường.
- [ ] **Nâng trang Sản xuất và preview:** luồng bốn bước, nhập hàng loạt, thông tin video, trạng thái sẵn sàng; preview nguồn/kết quả, segment tùy chọn, kích thước theo preset, phát/dừng/tua; vô hiệu thao tác xung đột khi đang chạy.
- [ ] **Hoàn thiện hàng đợi bền vững:** lưu nguyên tử sau chuyển trạng thái, chạy một job GPU/lần; chạy mục chọn, chạy lại lỗi, bỏ qua mục đã hoàn tất với cùng snapshot. Sau crash/dừng, tiếp tục ở cấp file; không tuyên bố nối từ frame dở. Dừng sau file và dừng ngay là hai hành vi riêng; bảo toàn đầu ra đã hoàn tất, dọn đúng partial do job tạo.
- [ ] **Bổ sung thiết lập sản xuất và báo cáo:** thư mục/mẫu tên, profile bitrate/CQ, audio, preset nâng cao; kiểm tra dung lượng; log lỗi dễ mở; tổng kết batch JSON/CSV; nút mở file/thư mục và dọn preview có giới hạn. Lưu log cục bộ, không tải video hay đường dẫn cá nhân lên dịch vụ ngoài.
- [ ] **Chuẩn bị asset local và đóng gói:** nhận cache từ thư mục/RAR của người dùng hoặc tự nhận diện cache local phù hợp; kiểm tra cấu trúc/hash, sao chép vào thư mục dữ liệu riêng. Giữ cache/media ngoài Git và ZIP public; thêm ModernGL/glcontext vào lockfile, build và thông báo dependency; chốt profile chất lượng bằng clip thật.
- [ ] **Kiểm thử bản sản xuất và updater:** chạy regression shader, snapshot/migration/queue/cancel, batch tối thiểu 20 clip hỗn hợp (có/không audio, tên Unicode, nguồn hỏng, trùng tên), preview so full render, kiểm tra RAM/VRAM; test EXE trên Windows không cài Python. CI public kiểm tra phần không cần GPU/cache; kiểm định GPU và asset dùng môi trường local có phần cứng phù hợp.
- [ ] **Phát hành 1.1.0 và thử nâng cấp thật:** build ZIP portable, checksum, release notes và GitHub Release GPL-3.0; thử updater từ 1.0.0 và rollback; kiểm tra preset/job/output/cache/runtime giữ nguyên. Chỉ công bố đã cập nhật thành công sau khi UI, cấu hình và worker smoke test sẵn sàng; thiếu cache/thiếu GPU trên máy đích được báo là vấn đề thiết lập, không gây vòng lặp rollback.

## Điều kiện nghiệm thu

1. Máy hiện tại mở EXE, chọn preset sản xuất, thêm thư mục video và xuất được cả batch mà không sửa JSON/chạy terminal.
2. GUI và CLI dùng cùng engine; preview đúng frame/thời điểm so với xuất full trong dung sai đã nêu. Profile đối chiếu 3:4 không làm giảm rõ chất lượng bokeh đã đạt; báo cáo metric được chạy lại khi đổi thuật toán hoặc encode.
3. 20 clip thử có trạng thái đúng; một clip lỗi không làm mất queue; dừng/crash/mở lại không xuất lại những mục đã hoàn tất cùng cấu hình. Nguồn không bị sửa; không có ffmpeg/process con còn sót sau hủy.
4. Giao diện không treo khi decode/render; hiện tiến độ từng file và toàn batch, báo rõ tác vụ đang chờ khi chưa đủ dữ liệu ETA. Cấu hình của job đang chạy không thay đổi ngầm.
5. Bản VBR cùng clip mẫu đạt dung lượng gần bản CapCut (lần thử hiện có chênh 1.54%); không cam kết tỷ lệ này cho mọi clip. Đầu ra đủ frame, SAR đúng, audio theo playback và sai lệch thời gian dưới một frame khi nguồn cho phép.
6. EXE chạy không cần Python, không chứa cache độc quyền/video; sau khi nhập asset một lần thì xử lý offline. Không có OpenGL tương thích phải được phát hiện trước batch; fallback CPU encode không được quảng cáo là thay thế GPU shader.
7. Updater xác minh SHA256, từ chối ZIP sai, không cài giữa job, giữ dữ liệu/preset/queue/cache; thử thành công nâng cấp 1.0.0→1.1.0 và phục hồi khi bản mới không khỏe. Kiểm thử hiện có của updater tiếp tục qua.

## Mở rộng sau khi bản đầu ổn định

Ưu tiên sau: theo dõi thư mục đầu vào và chống xử lý file đang copy; lịch chạy; preset riêng theo thư mục; watermark/logo; trim đầu/cuối; chuỗi filter có thứ tự; nhiều profile xuất cho một nguồn; thông báo hoàn tất của Windows. Chỉ thêm chạy song song GPU sau khi đo VRAM, throughput và độ đáp ứng trên RTX 2070 Super.

Không có câu hỏi đang chặn việc triển khai. Lựa chọn mặc định đề xuất: PySide6/QML hiện tại, EXE portable x64, một job GPU/lần, H.264 NVENC khi khả dụng, production 1×, giữ nguyên cơ chế updater GitHub Releases.
