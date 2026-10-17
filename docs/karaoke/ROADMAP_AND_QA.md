# Tích hợp preset 1012

Ngày 17/10/2026, nền `v1.2.1` / `a36081087a5940bf002837acf37609f2db1170b8`. Handoff gốc: `BetaRender_1012_Karaoke_Update_Patch.zip`. Không đưa video, Draft hay dữ liệu riêng vào Git.

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

Các công cụ tái hiện: `python tools/qa_karaoke.py` và `python tools/qa_portable.py --input <MP4-có-lời-thoại> --karaoke`.

## Cổng phát hành

Đang kiểm tra ZIP sạch, native ASR, ba phần bằng EXE, CI và updater. Chưa có video CapCut hoàn chỉnh của project 1012 trong gói gửi nên chưa chấm độ giống; các điểm cắt đều nhau và hiệu ứng lặp là thiết kế hiện tại. Model ASR có thể nhận sai từ/thời gian, cần xem thử với nguồn thực tế.
