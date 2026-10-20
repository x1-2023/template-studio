# Chọn đoạn nguồn và chỉnh màu — 1.3.8

## Cách dùng

- **Chỉnh cấu hình → Đoạn nguồn & chia part**: nhập Từ/Đến theo mốc video gốc. Nhận giây, `phút:giây` hoặc `giờ:phút:giây`, có thể có phần mili giây. Để trống Đến để lấy hết.
- Nguồn 20 phút, Từ `00:00`, Đến `10:00`, Chọn số part `3`: chỉ chia 10 phút đầu. Thời lượng xuất còn phụ thuộc tốc độ đã chọn.
- Mỗi dòng trong **Bỏ quảng cáo / đoạn không cần** là một khoảng như `02:10 - 02:35`. Tối đa 20 khoảng, tự gộp khoảng trùng, bỏ phần ngoài đoạn chọn; không tự nhận diện quảng cáo. Các đoạn được giữ được nối trước khi chia part.
- Quảng cáo khác vị trí ở từng nguồn: chọn video bên trái → **Chọn đoạn riêng…**. Mốc riêng giữ qua đổi preset, chỉnh cấu hình, thử lại và mở lại app. **Dùng đoạn chung** đưa nguồn về mốc chung. Đổi đoạn của mục hoàn tất đưa mục đó về hàng chờ, giữ bản xuất cũ.
- **Chỉnh màu video** có sáng, tương phản, bão hòa và tông màu. Giá trị mặc định 0 giữ đường render cũ. Thực hiện sau bộ lọc/hiệu ứng và trước lớp chữ/emoji; lưu cùng preset. Nút đặt lại chỉ đưa bốn mức màu về 0.
- **Phụ đề karaoke** có các nhóm màu riêng cho phụ đề, tiêu đề và PART; chữ/nền PART không phụ thuộc màu tiêu đề.

## Cách xử lý thời gian

`source_offset` giữ nghĩa cắt đầu của cấu hình cũ. Thêm `source_end=0` (hết nguồn), `source_skip=[]` và bốn mức màu bằng 0; preset cũ được chuẩn hóa với các giá trị này.

`SourceTimeline` là ánh xạ dùng chung cho kế hoạch part, preview, decode, âm thanh và mốc từng từ. Khoảng quảng cáo được loại khỏi lời trước khi tìm điểm ngắt câu/chia part. Chia theo số part giữ đủ nội dung được chọn trên một lưới 30 FPS. Thời gian preview tính trên video đã cắt và đổi tốc độ.

Mỗi khoảng hình được seek trực tiếp từ nguồn, truyền frame qua GPU rồi vào một encoder cho mỗi file kết quả. Không tạo video trung gian hoặc mã hóa video hai lần. Các khoảng tiếng được trim và concat trong FFmpeg, đổi tốc độ một lần sau nối rồi bù trễ trên trục part. Preview giữa part lùi âm thanh theo trục đã cắt để không chèn lại khoảng lặng đầu part. Phụ đề tự động vẫn được nhận/cache một lần cho nguồn gốc, tái dùng khi thay đổi mốc cắt.

Đoạn chung được áp dụng cho hàng chờ; đoạn riêng lưu trong cấu hình từng nguồn cùng cờ `sourceRangeCustom`. Những mục hoàn tất giữ cấu hình cũ khi chỉ thay đổi cấu hình chung. Nguồn ngắn hơn mốc Đến lấy tới hết nguồn; đoạn không còn nội dung báo lỗi trước khi nhận lời/render.

## Kiểm chứng

- Mã ứng dụng đóng gói: `1361d95c95c70dc8c84b79422a94ad9d01494b8d`. Commit `4d72dfec8e1035c06824bdd9b4ffecf778ce3933` chỉ bổ sung chờ focus/xác minh nội dung trong kiểm thử GUI.
- Local: **129 kiểm thử đạt**, Ruff và `git diff --check` đạt. Kiểm thử thật FFmpeg chứng minh frame khi seek qua mối nối khớp byte bản liên tục; phổ âm thanh giữ ba đoạn 600/1000/1400 Hz, không còn các đoạn bị bỏ; kiểm tra khoảng lặng 50 ms, preview giữa part, tốc độ 1.5× và preview ngắn 20 ms.
- [CI Windows 39425038211](https://github.com/x1-2023/template-studio/actions/runs/39425038211) đạt: 127 kiểm thử, bỏ qua một lớp kiểm tra GPU do runner không có OpenGL 3.3. Hai kiểm thử pixel GPU đã chạy đạt trên máy local.
- EXE giải nén ở thư mục mới, PATH chỉ có Windows: Qt, hiệu ứng, font và RTX 2070 SUPER/NVENC khởi động đủ. Dùng bản FFmpeg/Whisper đã xác minh trong thư mục dữ liệu kiểm thử; không dùng Python hay font hệ thống để render. EXE nhận **51 từ** từ MP4 15 giây.
- Nguồn thật 509.125 giây: chỉ giữ **60–70 giây**, bỏ **62–63.25** và **66.1–67.2**, tốc độ 1.02931464386368×. EXE xuất ba PART **74 + 74 + 75 = 223 khung**, có âm thanh, font ZY Trend. Nhật ký từng part chỉ ra đầy đủ các khoảng nguồn được giữ, không lấy quảng cáo hay đuôi nguồn. Tiêu đề vàng/nền đen và PART xanh ngọc/nền đỏ đã kiểm tra trên ảnh xuất thực.
- Bốn mốc preview qua mối nối lệch trung bình **0.57–0.88/255** so với bản đầy đủ sau hai lần mã hóa NVENC riêng. Kiểm thử raw frame phía trên khớp byte. Bốn mốc đường mặc định so EXE 1.3.7 có sai khác pixel **0** khi các mức màu bằng 0.
- Hủy worker EXE khi đang render: không công bố MP4, không còn file partial; SHA-256 nguồn giữ nguyên.
- Bằng chứng local riêng: `.runtime/qa-native-edits-138/verified.json`, ảnh giao diện `.runtime/part-range-138.png`, `.runtime/color-adjust-138.png`, `.runtime/video-range-138.png`. Không đưa video, lời thoại hoặc dữ liệu kiểm thử cá nhân lên Git.

## Gói phát hành đã kiểm định

- `TemplateStudio-windows-x64.zip`: **257833073 byte**.
- SHA-256: `b9ef1f2ac75134795a70ed00387bbde5d210907d3bb9662ea1d2a9b1b6056812`.
- Giữ tên EXE/asset cũ để các máy đang dùng updater nhận được phiên bản mới. Bộ chứng chỉ CA, font ZY Trend, shader/LUT và thư viện ứng dụng được giữ trong gói. FFmpeg/Whisper vẫn được tải ở lần dùng đầu nếu máy chưa có runtime.

## Kiểm chứng updater public

[Beta Render 1.3.8](https://github.com/x1-2023/template-studio/releases/tag/v1.3.8) đã public với đúng kích thước và SHA-256 ở trên. Lượt thử dùng ZIP public 1.3.7, tải thật gói 1.3.8 từ API/release GitHub, xác minh checksum rồi chạy helper thay app và mở lại. Helper báo thành công, callback healthy xác nhận 1.3.8, backup EXE khớp bản 1.3.7.

Preset, queue, màu riêng, font Arial đã nhập và các file đánh dấu trong data/runtime/exports đều được giữ. Cấu hình cũ nhận các giá trị mặc định mới qua `normalize`, không sinh bản sao `production-invalid`. EXE sau nâng cấp xuất **74 khung PART 2** với hai khoảng quảng cáo đã bỏ, tông màu 8° và font đóng kèm. Bằng chứng riêng: `.runtime/qa-updater-138/verified.json`. Không thay asset hoặc di chuyển tag sau phát hành.
