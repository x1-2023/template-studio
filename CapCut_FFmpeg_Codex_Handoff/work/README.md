# Bản port GPU của effect ngũ giác CapCut

CLI chạy offline trên Windows: FFmpeg decode → OpenGL nhiều pass → NVENC hoặc libx264. Không cần GUI/timeline. Các shader GLES, texture LUT và noise được đọc từ cache local của người dùng. Không vẽ polygon ngẫu nhiên và không ghi đè các bản v2–v7.

Hai preset riêng: `capcut-pentagon` cho cặp tham chiếu 3:4 và `draft-9x16` cho draft 9:16. Preset 3:4 chứa phép lật ngang, scale 1.0513 và playback 1.02 **đo từ cặp video cụ thể**; với clip khác thường cần đặt playback_rate=1 và sửa layout.

## Cài và chạy

Yêu cầu Python 3.10+, FFmpeg/ffprobe trong PATH và driver OpenGL 3.3+. Đã chạy thực trên Windows, Python 3.14.6, ModernGL 5.13.0, FFmpeg 7.1.1, RTX 2070 Super / driver 596.49. ModernGL dùng WGL standalone, không mở cửa sổ. Đây chưa phải bản zero-copy CUDA: upload một lần, các pass ở GPU, readback một lần mỗi frame; decode và vận chuyển raw frame vẫn dùng CPU.

Từ thư mục `work`:

```powershell
powershell -ExecutionPolicy Bypass -File .\setup.ps1
.\render.bat "..\02_REFERENCE_MEDIA\source_original_compre_juguetes.mp4" ".\artifacts\preview.mp4" --preset capcut-pentagon --encoder h264_nvenc --seconds 3
```

Trong workspace hiện tại có thể dùng ngay Python đã cài:

```powershell
Set-Location -LiteralPath 'E:\.capcut\CapCut_Studio_Pro\TemplateStudio_Standalone'
.runtime\build-env\Scripts\python.exe CapCut_FFmpeg_Codex_Handoff\work\render.py CapCut_FFmpeg_Codex_Handoff\02_REFERENCE_MEDIA\source_original_compre_juguetes.mp4 CapCut_FFmpeg_Codex_Handoff\work\artifacts\preview.mp4 --seconds 3
```

`setup.ps1` tạo venv riêng. Nếu `py` không chọn đúng Python, truyền `-Python 'C:\duong-dan\python.exe'`. `prepare_cache.py` kiểm tra SHA256 của RAR gốc và chặn entry vượt thư mục trước khi giải nén bằng bsdtar (`tar.exe` trên Windows 11). Có thể giải nén bằng 7-Zip vào `work/cache` hoặc truyền `--cache` tới cache đã có. Shader không được tải từ Internet khi render.

## Các tùy chọn cần dùng

```powershell
# Preview nhỏ; cần chỉ định đủ hai chiều để giữ đúng canvas 3:4.
python render.py source.mp4 preview.mp4 --width 540 --height 720 --proxy --seconds 3

# Case A: không lấy layout/tốc độ của case B áp vào.
python render.py source-9x16.mp4 output.mp4 --preset draft-9x16 --seconds 3

# Clip thông thường: playback 1x. KEY=JSON hỗ trợ số, boolean, chuỗi, mảng.
python render.py source.mp4 output.mp4 --set playback_rate=1 --set flip=false --seconds 3

# Fallback màu da; không có model tt_skin_seg trong cache.
python render.py source.mp4 chroma.mp4 --skin chroma --seconds 3
python render.py source.mp4 masked.mp4 --skin mask --skin-mask segmentation.mp4 --seconds 3

# Tắt từng nhánh để kiểm tra, hoặc dùng bộ mã hóa CPU.
python render.py source.mp4 layout.mp4 --no-effect --no-filter --seconds 3
python render.py source.mp4 cpu-encode.mp4 --encoder libx264 --seconds 3

# Giữ bitrate gần bản CapCut tham chiếu; mặc định CQ18 không giới hạn dung lượng.
python render.py source.mp4 output-9650k.mp4 --video-bitrate 9.65 --full

# Batch: đường dẫn input/output tương đối tính từ vị trí file JSON.
python render.py --batch batch.example.json --seconds 3

# Chỉ chạy hết video sau khi đã xem preview.
python render.py source.mp4 full.mp4 --full
```

`--skin mask` nhận PNG grayscale cố định hoặc video mask đúng kích thước **canvas đầu ra**, trắng=da, đen=nền, theo timeline đầu ra 30 fps. Nếu segmenter tạo mask trong tọa độ nguồn, cần biến đổi mask cùng layout trước. Mask thiếu frame sẽ báo lỗi, không im lặng thay bằng mask rỗng.

`--video-bitrate` dùng đơn vị Mb/s và VBR theo ngân sách bitrate; NVENC dùng multipass quarter resolution. Dung lượng dự kiến xấp xỉ `(bitrate video + bitrate audio) × thời lượng / 8`, không phải cam kết đúng số byte. Bỏ tùy chọn này để giữ chế độ chất lượng CQ/CRF 18 ban đầu.

Mặc định xuất thử 3 giây, từ chối ghi đè file có sẵn trừ `--overwrite`, từ chối đầu ra trùng nguồn. File `.partial.mp4` chỉ đổi thành đầu ra sau khi FFmpeg thành công. Audio dùng cùng source offset, `atempo=playback_rate` và reset PTS, rồi encode AAC cùng một lượt mux. Output SAR=1:1. Chỉ hỗ trợ SDR; không dùng flag HDR để giả vờ tái tạo HDR.

## Kiểm chứng và giao nộp

- [Báo cáo kết quả](REPORT.md): đo định lượng, benchmark, giới hạn và các giả thuyết.
- [Đối chiếu dung lượng bản full](ENCODING_REPORT.md): nguồn / CapCut / GPU, profile VBR 9.65 Mb/s và video ba cột đủ thời lượng.
- [Đồ thị pass](PASS_GRAPH.md): input/FBO/uniform và mức chắc chắn của từng phần.
- `artifacts/preview_compare_3s.mp4`: CapCut thật / v7 đã căn / GPU mới.
- `artifacts/gpu_final_1080_3s.mp4`: preview 1080×1440 có audio.
- `artifacts/final_1080.jpg`, `final_1080.json`: contact sheet và SSIM/PSNR tại 9 mốc.
- `artifacts/gpu_benchmark_1080_10s.mp4` và `.render.json`: 10 giây, số frame/audio/PAR và thời gian thực.

```powershell
python test_gpu.py
python align.py
python refine_alignment.py
python check_timing.py
python baseline_aligned.py --width 1080 --height 1440
python evaluate.py GPU=artifacts/gpu_final_1080_3s.mp4 V7-aligned=artifacts/baseline_v7_aligned_1080_3s.mp4 --width 1080 --height 1440 --prefix final_1080
python make_preview.py
powershell -ExecutionPolicy Bypass -File .\benchmark.ps1
```

`align.py` tìm affine và hflip từ đặc trưng SIFT, `refine_alignment.py` kiểm tra cadence bằng frame nguồn 59.94 fps, `check_timing.py` đo đường bao audio độc lập. Quy tắc `fps=30:round=up` chọn frame nguồn tại hoặc trước timestamp đầu ra, khớp cadence quan sát tốt hơn mặc định `near`. Không warp từng frame đầu ra để làm đẹp metric. Các script `tune*.py` là thí nghiệm hữu hạn, không phải bộ tối ưu tự sửa ảnh đích.

Mã port do dự án viết dùng GPL-3.0-only theo repository. Cache CapCut, LUT, video nguồn/tham chiếu và lịch sử gốc là tài nguyên local riêng; không nằm trong gói source công khai. Bản source chỉ chạy nhánh này khi người dùng cung cấp cache tương ứng. Không có tuyên bố shader/asset của CapCut được cấp lại GPL.
