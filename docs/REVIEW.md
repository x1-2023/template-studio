# Đánh giá dự án và đối chiếu video

Đối chiếu bản ghi màn hình CapCut dài 42,73 giây do người dùng cung cấp. Các frame khoảng 18–27 giây cho thấy effect “Trong như pha lê”; khoảng 30–36 giây có chỉnh tỷ lệ clip, một frame hiển thị 87%, với vùng viền tối. Không đưa video hoặc ảnh riêng tư của người dùng lên repository.

## Kết luận về độ giống

| Thành phần | Trước thay đổi | Hiện tại |
| --- | --- | --- |
| Khung dọc 9:16, clip chính và nền mờ | Có | Giữ nguyên |
| Scale clip | Có, 30–100% | Giữ nguyên; không phải zoom theo keyframe |
| Âm thanh theo tốc độ, hàng đợi, hủy tác vụ | Có | Giữ nguyên, bổ sung kiểm thử với nhánh filter |
| Filter màu / thư viện hiệu ứng | Chưa có trong pipeline template | Tích hợp Video-FX: 150 preset, 6 nhóm |
| Thumbnail và thử filter trước khi chọn | Chưa có | Thumbnail từ clip hoặc ảnh mẫu, preview 8 giây, áp dụng cấu hình |
| Khúc xạ, tia sáng và viền của effect CapCut | PNG lục giác tĩnh và blur/fade | Chưa tái tạo chính xác |
| Chuyển cảnh giữa nhiều clip | Chưa có | Chưa tích hợp GL Transitions |
| Updater EXE | Chưa có | Có tải, xác minh, thay app và phục hồi |

Phần lớn bản ghi là thao tác điều chỉnh khi playhead ở đầu clip. Chưa đủ bằng chứng để định lượng chuyển động, keyframe và độ giống theo từng frame của effect CapCut. Không tuyên bố hiệu ứng hiện tại giống 100%.

## Phát hiện và xử lý

- **P1 – Khởi động EXE:** thư mục dữ liệu chưa được tạo trước khi tạo lock; thư mục xuất mặc định lấy từ bundle. Đã tạo dữ liệu trước khi khóa và chuyển đầu ra mặc định vào thư mục dữ liệu có thể ghi.
- **P1 – QtQuick trên Windows:** Qt tải plugin động nhưng chưa có DLL directory của wheel trên đường tìm thư viện. Đã thêm DLL directory trong launcher và entry EXE; kiểm tra QML thực.
- **P1 – DLL từ môi trường build:** PyInstaller có thể gom nhầm ICU của Poppler từ PATH, khiến QtCore lỗi trong EXE. Đã giới hạn PATH và đường dẫn Qt của tiến trình build vào Python, wheel PySide6 và thư mục hệ thống; kiểm tra lại EXE với PATH sạch.
- **P1 – Đổi cấu hình nhưng không xuất lại:** hàng đợi bỏ qua mọi dòng “Hoàn tất”, dù vừa đổi filter. Đã đưa các dòng này về chờ xử lý khi cấu hình thay đổi; giữ đường dẫn bản xuất cũ.
- **P1 – Phát hành:** chưa có version, repository, pipeline hay updater. Đã thêm manifest, workflow Windows, checksum và bộ kiểm thử cập nhật.
- **P2 – Độ giống effect:** hàm texture tạo ảnh lục giác tĩnh, overlay chỉ fade. Thư viện filter mới giúp tạo nhiều phong cách, chưa thay thế shader khúc xạ của CapCut.
- **P2 – Tốc độ xử lý:** filter Video-FX chạy CPU; NVENC chỉ giúp mã hóa. Adapter dùng luồng RGBA, không dùng API upstream vốn đọc cả video vào một danh sách frame.
- **P2 – Chất lượng catalog:** 150 preset dùng chung khoảng 30 engine; một số preset có hình thức gần nhau. Chưa kiểm chứng chất lượng nghệ thuật trên mọi loại cảnh.
- **P2 – Encoder:** nhận diện hiện thử H.264 NVENC; khả năng HEVC có thể khác trên GPU khác. Chưa có fallback tự động cho mọi lỗi encoder.
- **P2 – Ký mã:** SHA-256 kiểm tra toàn vẹn gói từ GitHub, chưa có chữ ký Authenticode cho EXE.

## Lựa chọn thư viện

1. [Video-FX](https://github.com/tomastimelock/video-fx/tree/751315965bc5e740b62136153ec4a9bf4e21ea20): đã tích hợp tại commit cố định, MIT; có catalog và API xử lý frame. Adapter riêng giữ âm thanh, hủy tác vụ và giới hạn RAM.
2. [Frei0r](https://github.com/dyne/frei0r): hợp cho plugin video; FFmpeg essentials hiện tại không biên dịch hỗ trợ. Cần FFmpeg phù hợp cùng plugin DLL và kiểm thử ABI trước khi thêm.
3. [GL Transitions](https://github.com/gl-transitions/gl-transitions): hợp cho chuyển cảnh hai texture; cần renderer OpenGL/WebGL và kiểm tra giấy phép từng shader. Chưa nằm trong pipeline một clip hiện tại.
4. [Crazy Video Glitch Editor](https://github.com/willbearfruits/videoglitchcrazynes): có thể tham khảo xử lý glitch và đồng bộ âm thanh, nhưng kéo cả ứng dụng vào sẽ tăng phạm vi dependency và đóng gói.

## Cải tiến tiếp theo

1. Xây preset pha lê riêng: khúc xạ theo vùng, nhân ảnh, tách màu và ánh sáng hướng tâm; thêm lựa chọn viền tối/nền mờ, thời lượng và fade. Đối chiếu bằng clip xuất mẫu của CapCut.
2. Thêm LUT .cube có kiểm tra định dạng/kích thước và nội suy màu, kèm preview trước/sau. Không đóng kèm LUT chưa rõ giấy phép.
3. Cho phép xếp nhiều filter theo thứ tự, bật/tắt từng lớp và lưu preset. Hiện áp dụng một filter thư viện tại một thời điểm.
4. Thử NVENC theo từng codec và tự thử lại bằng CPU khi gặp lỗi phần cứng; giữ nguyên quy trình xác minh đầu ra.
5. Nếu cần chuyển cảnh: thêm mô hình nhiều clip và điểm nối trước khi tích hợp GL Transitions.
6. Ký Authenticode, cập nhật runtime FFmpeg đã kiểm thử và mở rộng kiểm thử trên máy Windows không có Python/GPU.
