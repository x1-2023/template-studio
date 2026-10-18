# Tích hợp preset 1012

Ngày 18/10/2026, nền `v1.2.1` / `a36081087a5940bf002837acf37609f2db1170b8`. Handoff gốc: `BetaRender_1012_Karaoke_Update_Patch.zip`. Không đưa video, Draft hay dữ liệu riêng vào Git.

## Đối chiếu hai thành phẩm và Draft 1012

- MP4 part 1: H.264, 1080×1440, 30 FPS, 5579 khung/185.966667 giây, video 9.602 Mb/s. Part 2: 5429 khung/180.966667 giây, video 9.668 Mb/s. Cả hai AAC stereo 44.1 kHz khoảng 194 kb/s.
- Draft gốc: canvas 1440×1920, hai compound nối nhau. Part 1 dùng nguồn từ 0 đến 191.418212 giây, xuất 185.966666 giây. Part 2 dùng nguồn từ 191.433333 đến 377.670663 giây, xuất 180.933333 giây. Video nguồn khai báo dài 509.133333 giây; Draft chỉ dùng một phần nguồn.
- Cả hai có tốc độ 1.02931464386368×, scale 1.124821386, góc video −9.005883649°, dịch X −0.094637224 theo hệ tọa độ Draft; góc chữ khoảng −11°. Đã quy đổi dịch X sang nửa kích thước canvas của renderer.
- Thành phẩm cho thấy ngũ giác rõ ở đầu từng part, hết sau intro. Đã bỏ mặc định lặp suốt clip, đặt lại intro ở mỗi part; sửa chiều xoay để cạnh phải đi lên như mẫu, vị trí chữ .66534 chiều cao, tiêu đề .14066 và nhãn part .85461.
- Preset sản xuất dùng quy tắc tổng quát: khoảng 180 giây/part, tìm khoảng nghỉ/cuối câu trong ±8 giây, tránh cắt giữa từ và gộp đuôi ngắn. Không gán hai điểm cắt riêng của mẫu cho mọi nguồn; giữ toàn bộ video sau mốc cắt đầu.
- Tự lấy tên file làm tiêu đề, tự đánh số PART. Dùng Arial Black của Windows thay font ZY Trend riêng của CapCut; chưa có emoji động/tô màu từ khóa.
- 80 kiểm thử source đạt; render GPU một nguồn có lời thoại 55.3 giây ở tốc độ theo Draft thành hai part 35.966667 và khoảng 17.763503 giây (đặt mốc thử 30 giây, sai số mã hóa trong một khung), có âm thanh. Thư mục xuất chỉ có MP4. Đã kiểm tra ảnh đầu part hai và ảnh sau intro. Preview và xuất cùng đọc thời lượng luồng video; phụ đề cạnh video cũng tham gia chọn điểm cắt.
- Đã nhận nguồn YouTube thật, dựng hai đoạn GPU và đo bốn khung đối chiếu; đã nhận 1457 từ từ toàn bộ nguồn và tạo preview ASR. Người dùng xác nhận mẫu thiếu part cuối, app phải giữ hết nguồn. Xem [đối chiếu và giới hạn](REFERENCE_CHECK.md).

## Đã sửa và kiểm thử source

- Installer gốc dừng vì anchor `temp-auto-cancel` xuất hiện hai lần. Đã tích hợp các thay đổi vào source và viết riêng phần điều phối chia video.
- Thay phụ thuộc faster-whisper tùy chọn bằng Whisper.cpp native để EXE chạy không cần Python/CUDA. Runtime/model tải một lần từ nguồn chính thức, ghim revision và SHA256. ASR chạy trong worker có hủy; cache phụ đề theo nguồn và model.
- ASS dùng tên tương đối cố định trong thư mục worker, tránh ghép đường dẫn Windows vào filtergraph. Đã render trên đường dẫn có dấu, dấu nháy, khoảng trắng và ngoặc vuông.
- Xoay trong tọa độ pixel để giữ tỷ lệ hình; đồng nhất chiều xoay với ASS. Đã kiểm tra bằng đường ngang và so sánh renderer cũ/mới: preset cũ giống từng pixel tại 0, 0.5 và 3 giây.
- Tiêu đề/nhãn phần giữ hết thời lượng xuất. Phụ đề cắt theo đoạn đang render; công thức thời gian dùng source offset và playback rate đúng một lần.
- Chia theo khung hình, ghi sổ từng phần, xác minh file trước khi tiếp tục. Hủy ở phần hai rồi chạy lại giữ nguyên thời gian sửa/file phần một, chỉ xuất phần còn thiếu.
- GUI có chọn nguồn phụ đề, chọn file, tiêu đề, góc video/chữ, lặp hiệu ứng, chọn một video/ba phần và nút mở từng phần.

## Kết quả local

Windows, RTX 2070 SUPER, OpenGL/NVENC và FFmpeg có libass:

- Nhận từ MP4 khoảng 55 giây: 163 từ, khoảng 10 giây CPU; lần gọi sau dùng cache.
- Nguồn tổng hợp 9 giây có âm thanh và JSON tiếng Việt: preview 540×720/90 khung; bản một video 1080×1440/270 khung; ba phần 1080×1440/90 khung mỗi phần, có âm thanh.
- Đã chụp và xem ảnh từ preview, bản full và ba phần.
- Mã hóa CPU x264, 720×960, tốc độ 1.02×, cắt đầu 0.2 giây, tắt tiếng: ba phần có tổng thời lượng trong sai số một khung.
- Kiểm thử GUI lưu/hủy cấu hình karaoke, chọn file phụ đề và giữ các preset cũ.

Các công cụ tái hiện: `python tools/qa_karaoke.py` và `python tools/qa_portable.py --input <MP4-có-lời-thoại> --karaoke`. Để kiểm tra chế độ tự chia trong EXE: `python tools/qa_portable.py --input <MP4-có-lời-thoại> --archive <ZIP-ứng-viên> --karaoke --part-seconds 30` (nguồn trên 45 giây để có ít nhất hai phần).

## Nghiệm thu 1.3.1

Kiểm tra nâng cấp bằng cấu hình 1.2.1 thật phát hiện từng hàng chờ chưa được bổ sung các trường mới. Đã chuẩn hóa cấu hình của tất cả hàng khi đọc phiên làm việc, giữ thông số cũ và tạo `production-before-karaoke.json` trước khi chuyển. Kiểm thử mới xuất tiếp hàng cũ mà không chọn lại preset, giữ video hoàn tất, preset tùy chỉnh và bản sao nguyên trạng. 1.3.0 được chuyển sang prerelease để updater tiếp tục dùng 1.2.1 trong lúc nghiệm thu 1.3.1.

## Nghiệm thu nền 1.3.0

Ứng viên 1.3.0 đã vượt qua các kiểm tra source và EXE:

- 69/69 kiểm thử local và [Windows CI](https://github.com/x1-2023/template-studio/actions/runs/39037301798) đạt. Mã chức năng: `031ae2473512118638dd683b3f82ddebc712491b`; fixture TEMP của runner được chuẩn hóa ở `d7a8f43`.
- ZIP giải nén vào dữ liệu sạch, PATH chỉ có Windows, không Python/FFmpeg/cache effect: app tự tải và xác minh FFmpeg; các preset cũ render offline bằng NVENC.
- Worker EXE trực tiếp tự xác định data_home, tải runtime Whisper và model khoảng 150 MB có checksum. Nhận 163 từ từ nguồn; ba phần sau đó xuất với mạng bị chặn.
- Kế hoạch chia dùng thời lượng luồng video, tách phần đệm AAC của container: mỗi phần 553 khung, 18.433333 giây, 1080×1440/30 FPS, có âm thanh. Thư mục xuất chỉ có ba MP4.
- GUI 1366×768 với preview MP4 thật đã được xem bằng mắt. Preview có nhãn đúng phần; khi xem sát điểm cắt sẽ dừng ở ranh giới phần đó.
- Phát hiện và sửa lỗi riêng của worker chạy trực tiếp không có biến môi trường; thêm kiểm thử hồi quy. Renderer gọi trực tiếp cũng dùng tên ASS an toàn và dọn file tạm.

Nền 1.3.0 ở GitHub Releases đã chuyển sang prerelease trong lúc nghiệm thu 1.3.1. Các kiểm tra ba phần bên trên ghi nhận thiết kế ban đầu của handoff; preset hiện đã đổi sang tự chia và intro đầu part theo nguồn thật cùng hai thành phẩm nhận ngày 18/10. Kết quả full nguồn và EXE cuối ở [báo cáo đối chiếu](REFERENCE_CHECK.md). Model ASR có thể nhận sai từ/thời gian, cần xem thử với nguồn thực tế.
