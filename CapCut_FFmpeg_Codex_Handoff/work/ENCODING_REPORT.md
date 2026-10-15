# Đối chiếu ba bản đủ thời lượng

Đã xuất bản GPU đầy đủ từ cùng nguồn để so với CapCut, dùng ngân sách bitrate video 9.65 Mb/s. Cấu hình CQ18 cũ vẫn dùng được cho kiểm định chất lượng; CQ18 không phải giới hạn dung lượng.

| Bản | Dung lượng | Thời lượng container | Codec / kích thước / fps | Bitrate tổng |
|---|---:|---:|---|---:|
| Nguồn | 15.620 MiB | 55.356s | AV1 / 1080×1920 / 59.94 | 2.367 Mb/s |
| CapCut thật | 63.675 MiB | 54.242s | H.264 / 1080×1440 / 30 | 9.847 Mb/s |
| GPU mới, đủ video | **64.657 MiB** | **54.233s** | H.264 / 1080×1440 / 30 | **10.001 Mb/s** |

Bản GPU lớn hơn CapCut khoảng **1.54%**; cả hai có đúng **1627 frame**, video duration **54.233333s**, SAR=1:1. Nguồn và CapCut khác codec, fps, kích thước và bitrate; dung lượng file riêng lẻ không đo được độ giống hiệu ứng.

Audio GPU AAC stereo start=0, duration 54.220998s; chênh phần đuôi so với video khoảng 12ms, dưới một frame 30 fps. Render full mất **39.833s**, đạt **40.85 fps** trên máy đã nêu trong REPORT.md. Đây là thời gian chạy bản có ngân sách bitrate, không dùng lại số benchmark CQ18.

Lệnh từ thư mục `work`:

```powershell
python render.py "../02_REFERENCE_MEDIA/source_original_compre_juguetes.mp4" "artifacts/gpu_full_capcut_bitrate.mp4" --preset capcut-pentagon --encoder h264_nvenc --video-bitrate 9.65 --full
python compare_full.py
```

File xem:

- `artifacts/gpu_full_capcut_bitrate.mp4`: đầu ra GPU thật, đầy đủ thời lượng và audio.
- `artifacts/compare_source_capcut_gpu_full.mp4`: ba cột nguồn / CapCut / GPU. Cột nguồn được lật và căn thời gian để đối chiếu chuyển động; không thêm effect/filter. Video ba cột được encode riêng để xem, không dùng dung lượng file này thay cho đầu ra GPU.
- `artifacts/three_full_videos.json`: metadata trực tiếp từ ffprobe.
- `artifacts/gpu_full_capcut_bitrate.render.json`: cấu hình, toàn bộ lệnh FFmpeg, timing và metadata đầu ra.

Kiểm tra chất lượng trước khi xuất full: cùng 9 mốc 0–2s, cùng shader/layout/thời gian, bản thử 3s ở 9.65 Mb/s đạt SSIM RGB **0.95273**, PSNR RGB **32.5269 dB**; CQ18 cũ đạt **0.95110 / 32.5356 dB**. Chênh lệch nhỏ; đây không phải tuyên bố chất lượng đã được chấm ở toàn bộ 54 giây. Dữ liệu ở `artifacts/bitrate_9650k.json`.

VBR có thể lệch nhẹ bitrate mục tiêu. Ngân sách này dùng để tạo preset sản xuất có dung lượng dự đoán được; không dùng lại video nguồn nén AV1 làm mục tiêu dung lượng mặc định cho đầu ra H.264.
