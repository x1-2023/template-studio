# Kết quả kiểm định — 15/10/2026

Đã chuyển prototype CPU sang pipeline shader GPU, tạo CLI/batch, preview và benchmark thực. Kết quả khớp rõ hơn v7; **chưa tuyên bố tái tạo CapCut 1:1**. Các file lịch sử, media và tài liệu gốc giữ nguyên: kiểm tra đủ 52 checksum trong manifest đều khớp.

## Khoảng trống ban đầu và thay đổi

V7 dùng OpenCV morphology/blur và các khẩu độ vẽ bổ sung, chưa chạy shader aperture nhiều pass; layout và cadence nguồn/tham chiếu chưa được đo. Bản mới thực thi shader GLES lấy trực tiếp từ cache cho BokehBlur, RadialBlur, OpticsCompensation, AntiAliasing và blend LumiLayer; port phép scale 2D của scene hiện có; giữ atlas LUT và sharpen float. [PASS_GRAPH.md](PASS_GRAPH.md) ghi input/uniform/FBO và phần còn ước lượng.

Không dùng clip v7 làm ground truth. Source là `source_original_compre_juguetes.mp4`; ground truth là `capcut_export_test.mp4` do CapCut xuất 1080×1440/30 fps. Case A 9:16 chỉ có draft; không trộn thông số scale/playback của hai case.

## Căn chỉnh và các quyết định có bằng chứng

1. SIFT/RANSAC tại các frame đã hết bokeh xác nhận hflip. Ví dụ t=2s: 428 inliers, sai số trung vị khoảng 0.217 pixel ở reference 360×480; scale source 240px → reference khoảng 1.18274, tương ứng foreground scale 1.0513 so với fit. Translation khoảng (38.14,-11.87) pixel, phù hợp bố cục căn tâm. Các frame 1–7s cho hình học ổn định gần tương tự.
2. Tốc độ clip phù hợp khoảng 1.02x. Đường bao audio 16 giây cho đỉnh tương quan 0.9604 ở rate 1.0204 và offset +5ms; sai số này chưa đủ để chứng minh offset video +5ms. Preset giữ rate 1.02, offset 0. Dò frame 59.94 fps độc lập cho t=1.0/1.5/2.0 → source frame 61/91/122.
3. `fps=30:round=up` lấy frame tại/trước timestamp đầu ra, khớp các frame quan sát trên. Mặc định `near` lấy các frame muộn hơn, làm SSIM ở t=1.5 chỉ khoảng .763; sửa cadence đưa mốc đó lên .914. Không dùng affine riêng từng frame hoặc optical flow để che sai lệch trước khi chấm.
4. Chạy shader tại 1080 cho thấy filter sau effect tái tạo viền ngũ giác tốt hơn. Trước khi sửa cadence, cùng 9 mốc: filter trước effect có PSNR 23.02 dB; filter sau có 24.93 dB (ảnh cùng được thu về 540×720 để chấm ở lần thử này). Chốt filter sau effect, intensity=1 và size=.7 từ cache. Scan size .5/.6/.7/.8, preblur 1/.5 không cải thiện so với thông số cache khi kiểm tra đồng thời hình ảnh và metric.
5. Case B không có draft export đầy đủ. Filter bật từ t=0 được chọn bằng đối chiếu video; case A giữ start .233333s theo draft. Sigma nền blur vẫn ước lượng. Không coi các giá trị fit của case B là cấu hình mặc định cho mọi clip.

Bằng chứng máy đọc được ở `artifacts/alignment_candidates.json`, `refined_alignment.json`, `audio_timing.json`, `cache_inventory.json`, `tuning.json`, `color_tuning.json`. Những file thử `initial`, `uv`, `full_candidates`, `cadence_final` được giữ để truy lại thay đổi; `final_1080` là đánh giá cuối.

## Metric cuối ở 1080×1440

Đánh giá các mốc 0, .1, .2, .3, .5, .8, 1, 1.5, 2s. Cả baseline và GPU đều render tại 1080, cùng bố cục và quy tắc thời gian đã đo. Baseline giữ effect v7 nguyên bản, không bổ sung LUT vào code cũ. Metric là trung bình đều theo 9 frame, không phải trung bình toàn clip và không phải phần trăm giống.

SSIM RGB: Gaussian 11×11, sigma 1.5, C1=(.01×255)², C2=(.03×255)², bỏ viền 5px; PSNR trên RGB 8-bit. Có thêm SSIM Y và ROI foreground x=12–88% để tránh nền mờ chi phối kết quả. LPIPS chưa chạy.

| Bản | SSIM RGB | SSIM Y | PSNR RGB (dB) | SSIM foreground | PSNR foreground (dB) |
|---|---:|---:|---:|---:|---:|
| V7 đã căn, 1080 | 0.73744 | 0.75701 | 17.2409 | 0.72274 | 17.4570 |
| Port GPU, 1080 | **0.95110** | **0.96103** | **32.5356** | **0.94844** | **32.6050** |

| t (s) | GPU SSIM RGB | GPU PSNR RGB (dB) |
|---:|---:|---:|
| 0 | .97119 | 35.8371 |
| .1 | .97251 | 36.8623 |
| .2 | .96356 | 36.7892 |
| .3 | .96588 | 36.2108 |
| .5 | .96940 | 35.7226 |
| .8 | .96655 | 31.6696 |
| 1 | .92288 | 26.6320 |
| 1.5 | .91393 | 27.1524 |
| 2 | .91398 | 25.9447 |

Ảnh: `artifacts/final_1080.jpg`; số liệu đầy đủ: `final_1080.json`; video ba cột: `preview_compare_3s.mp4`. Sai khác còn rõ nhất khi hình đã lấy nét: màu da, sharpen/chi tiết, nền blur và vài vùng chuyển động. Tỷ lệ pixel RGB≥250 trung bình ở GPU khoảng 0.0101%, không có hiện tượng cháy sáng toàn khung như lỗi convolution cũ.

## Hiệu năng và I/O

Máy thực: RTX 2070 Super, driver 596.49, OpenGL 3.3 WGL, Windows; Python 3.14.6, ModernGL 5.13.0, glcontext 3.1.0, NumPy 2.5.4, FFmpeg 7.1.1. Test shader/metric ban đầu dùng Pillow 12.2; bộ cài sạch đã chạy với Pillow 12.3.0. Pillow không tham gia xử lý màu trong shader.

Lệnh benchmark: `python render.py source_original_compre_juguetes.mp4 gpu_benchmark_1080_10s.mp4 --preset capcut-pentagon --encoder h264_nvenc --seconds 10`.

- Decode nguồn đầy đủ 1080×1920; output 1080×1440, 30 fps; **không proxy**.
- 300 frame / **7.6033s** wall time → **39.4564 fps**, bao gồm tạo context, decode, upload/readback, NVENC, audio và mux.
- GPU timer trung bình toàn 10s: **0.4906ms/frame**; riêng cửa sổ bokeh đầu khoảng **1.7979ms/frame**. Không dùng số trung bình 10s để tuyên bố pass bokeh chạy 2000 fps: phần lớn clip đã hết bokeh.
- V7 đã căn cùng layout, test 3s/90 frame ở 1080: **23.39s**, khoảng **3.85 fps**. Độ dài benchmark khác nhau; đây không phải phép đo speedup trực tiếp của từng shader.
- `ffprobe`: video 300 frame, duration 10.000000s, audio AAC stereo 10.000000s, cả hai start=0, SAR=1:1. Audio dùng `atempo=1.02`; không giữ tốc độ audio 1x khi hình chạy 1.02x.

Số liệu gốc và toàn bộ command FFmpeg nằm trong `.render.json`. Kiến trúc còn copy CPU↔GPU và pipe rawvideo; cải tiến tiếp theo có ích là native decode/encode interop hoặc pipeline bất đồng bộ. Không cần giả vờ NVENC tự chuyển OpenCV sang GPU.

## Kiểm thử đã chạy

- Sáu kiểm thử GPU: Bézier/slider, hai atlas so với bộ lấy mẫu CPU (sai số tối đa 1/255), hướng ảnh/hflip, sharpen trên màu phẳng và frame đen không tự xuất hiện polygon.
- Smoke CLI: batch vẫn chạy job sau khi một job lỗi; video không audio; nguồn SAR=2:1 được đổi đúng display aspect sang SAR=1:1; skin mask ngoài; libx264; bảo vệ nguồn và đầu ra có sẵn; preset 9:16 bằng video tổng hợp; dọn file partial.
- Cài mới bằng `setup.ps1`, tạo venv riêng và nạp đủ shader thành công. Không phụ thuộc việc đã cài PySide6 của GUI.
- Ruff check/format cho mã mới; checksum 52 file bàn giao gốc đều khớp.

## Giới hạn và bước cải tiến có căn cứ

- Thiếu `tt_skin_seg`: mặc định `none` dùng LUT background. `chroma` đã thử nhưng metric kém hơn trên cặp này. Chế độ `mask` nhận đầu ra segmenter ngoài; cần mask đúng tọa độ canvas/timeline. Đưa model khác vào chưa thể gọi là segmentation chính xác của CapCut.
- Thiếu stabilization matrix và source case A; chỉ kiểm thử cấu trúc preset 9:16 bằng mẫu tổng hợp, chưa chứng minh khớp video draft gốc.
- Chưa có motion blur bilateral gốc hoặc HDR/tone mapping gốc. Pipeline hiện SDR.
- Bản port LumiLayer hỗ trợ biến đổi 2D của asset này; không phải runtime tổng quát cho scene CapCut. Precision/rounding FBO và GLES mediump có thể khác engine gốc.
- Background Gaussian, thứ tự filter ngoài effect và thông số layout case B có bằng chứng thực nghiệm; chưa có toàn bộ project gốc để xác minh từng thiết lập nội bộ.
- Đã kiểm định 9 mốc trong 3 giây đầu; benchmark 10 giây để đo hiệu năng. Chưa đối chiếu định lượng cả 54 giây và chưa khẳng định khớp mọi video.

Source mới và giấy phép nằm trong `artifacts/capcut_gpu_source.zip`; cache CapCut, LUT, media và bản lịch sử gốc không được đưa vào gói source công khai. CLI này hoạt động độc lập; bản GUI/EXE hiện hữu chưa được đổi renderer trong lần bàn giao này theo phạm vi không GUI/timeline của prompt.
