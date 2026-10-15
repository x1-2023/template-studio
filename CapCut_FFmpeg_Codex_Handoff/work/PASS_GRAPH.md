# Đồ thị pass và bằng chứng

Hai resource được giải nén từ RAR SHA256 `0ab5b75f72ada6132f7e6dd3812b950934e1608bb724dc98e764978c0503cf47`:

- Effect: `7491138615477685505/5b7a93fc0ffd188dedb3285340566f3b/AmazingFeature`.
- Filter: `7514206177195068689/17a86357c081e0d080c9d501a66382d0/AmazingFeature`.

`inspect_cache.py` lập SHA256 từng file và đọc các chuỗi tham chiếu trong scene/material/xshader. Các file `.ausl` bắt đầu bằng `ASLE`, không phải GLSL đọc được; renderer dùng bản GLES `.frag` mà `.xshader` tham chiếu. `graph.dat` chưa được giải mã đầy đủ. Đồ thị dưới đây được xác định từ tuyến texture trong `main.scene`, binding material và Lua runtime, không suy diễn từ tên effect.

| Thứ tự | Pass | Input | Output theo cache | Uniform chính / phép tính |
|---|---|---|---|---|
| 1 | `gaussBlur0` | `InputTex` | `OutputTex` dùng làm scratch | Blur dọc; sample `22*(sample/79)^.35*.7`; kích thước thiết kế có cạnh ngắn 720 |
| 2 | `gaussBlur1` | Scratch trên, `darkFilter.png`, `noise.png` | Shared `outputTex.rt` | Blur ngang; LUT tối với hệ số `.5*(sample/79)*darkIns`; darkIns=2; nhân noise theo luma |
| 3 | `polygon` | Shared texture trên | `effects/LumiBokehBlur/rt/bokeh.rt` | 5 cạnh bán kính cơ sở 11; lấy mẫu bên trong và dọc cạnh; weight `pow(color,9)*539.45+.4`; max/highlight mix |
| 4 | `in2out` | `bokeh.rt` từ material | `LumiTempRT0.rt` | Lấy mẫu texture để phóng về kích thước đầu ra |
| 5 | `LumiLayer_102-trs` | `LumiTempRT0.rt` | `LumiTempRT1.rt` | Scale 85→100%; mirror edge; anchor/position ở tâm; opacity 100 |
| 6 | `LumiRadialBlur_101-effect0` | `LumiTempRT1.rt` | `outputTex.rt` | Fading Zoom; amount 33→0 / 200; quality `.1497894759*100`; decay .965; dither .5 |
| 7 | `LumiOpticsCompensation_101-effect1` | `outputTex.rt` | Shared `LumiTempRT0.rt` | Pincushion; FOV 20→0; hệ số distortion tính đúng theo Lua; tỉ lệ Y=H/W |
| 8 | `AntiAliasing` | Shared texture trên | `LumiTempRT2.rt` | Shader GLES gốc; giữ nguyên cả phép lấy mẫu đặc biệt `v_uv*texelSize` |
| 9 | `LumiLayer_101-blend` | Source `LumiTempRT2.rt`; base `LumiTempRT1.rt` | `outputTex.rt` | Normal, Adjustment, opacity 1, không matte |
| 10 | Filter `pass0` | Effect đã composite | FBO sharpen của bản port | Center `f`, 4 láng giềng `(1-f)/4`; float; unpremultiply/premultiply alpha |
| 11 | Filter `filter` | Sharpen; atlas bg/skin; mask alpha | FBO tone của bản port | Hai atlas 512×512, 64³; nội suy lát blue và bilinear R/G; intensity=1 |

Các pass ghi đè toàn màn hình; bản port tắt fixed-function blending và chạy phép blend trong fragment shader `LumiLayer`. Chưa chứng minh byte-for-byte trạng thái render của engine CapCut. FBO của bản port dùng RGBA8 và linear sampling; precision GLES `mediump` chuyển thành float desktop OpenGL. Đây là các khác biệt cần giữ trong báo cáo.

Kích thước FBO polygon lấy từ Lua: `W,H * mix(1, mix(.3,.4,quality), (sample/79)^.35)`. Bản port làm tròn về số nguyên; engine gốc có thể làm tròn khác. Khi sample về 0, bỏ qua nhánh bokeh đã thành identity.

## Keyframe và slider đã xác định

- `sample`: 80→0; `lightIns`: 5.72→4; cùng thời gian 0→.966667s, Bézier (.5,0,.43,1).
- Scale XY: 85→100%, Bézier (.287356321,5e-9,0,1.000000038), 0→.966667s. Giải Bézier bằng đảo tọa độ X như `AETools.lua`.
- Radial amount: 33→0, 0→.333333s, Bézier (.333333332,0,.66666667,1).
- Optics FOV: 20→0, 0→.333333s, Bézier (.041666681,0,.208333379,1).
- `LumiParamsSetter.lua` biến `effects_adjust_speed` từ [0,1] sang [0,2] rồi **nhân amount và FOV**. Slider 1/3 tương ứng hệ số 2/3. Không làm video chậm 1/3 và không kéo dài keyframe bokeh.
- `LumiManager` ở Once: giữ AE time tại cuối composition 1.133333s. Effect segment dài 2.166667s không có nghĩa bokeh còn mạnh hết đoạn.

## Các phần đã rút gọn hoặc còn ước lượng

- `LumiLayer` vẫn dùng fragment shader gốc cho mirror/alpha/blend. Riêng phép ray/ma trận trong nhánh TRS được rút gọn thành `(uv-.5)/scale+.5`, tương đương trường hợp hiện có: anchor=position=tâm, rotation=0, không parent transform. Không hỗ trợ một scene 3D tùy ý.
- Tuyến pass bên trong effect và bên trong filter xác định được từ cache. Thứ tự **filter sau effect** nằm ngoài hai asset độc lập: chọn bằng thử nghiệm ở 1080 và kiểm tra viền bokeh, SSIM/PSNR; không gọi đây là thông tin đọc trực tiếp từ draft của case B.
- Layout nền blur không có shader canvas gốc trong hai resource. Dùng cover + Gaussian separable trên GPU; sigma đang ước lượng. Foreground scale 1.0513 và hflip của case B được đo từ video.
- Skin mask `tt_skin_seg` không có model trong gói; mặc định `none` dùng LUT background cho toàn ảnh. `chroma` là heuristic; `mask` nhận đầu ra của segmenter bên ngoài. Không gọi fallback là model CapCut.
- Chưa tái tạo stabilization mức 2 vì thiếu matrix; chưa port motion blur bilateral và HDR/tone mapping gốc. Case A chưa có source để kiểm định.
