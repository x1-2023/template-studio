# Sửa xác minh HTTPS — 1.3.7

Ảnh lỗi 1.3.5 báo `CERTIFICATE_VERIFY_FAILED: unable to get local issuer certificate` khi tải FFmpeg; kiểm tra GitHub cũng thất bại. Bản cũ gọi `urllib` bằng context mặc định và chưa đóng kèm CA, nên kết quả phụ thuộc kho tin cậy có trên máy chạy app. Không thể xác định đầy đủ kho chứng chỉ/proxy của máy trong ảnh chỉ từ thông báo này.

Đã tái hiện cùng lỗi khi kết nối GitHub bằng context không có CA. Khi bỏ qua CA hệ điều hành và dùng bundle certifi đóng kèm, cùng yêu cầu trả HTTP 200. Không sửa kho chứng chỉ Windows.

## Thay đổi

- `network.open_https` dùng CA Mozilla từ certifi 2026.10.19 và bổ sung chứng chỉ tin cậy hệ điều hành. Giữ `CERT_REQUIRED`, xác minh tên máy chủ và chặn chuyển hướng từ HTTPS xuống HTTP.
- FFmpeg, Whisper/model và updater dùng chung đường tải này. Các kiểm tra SHA-256, giới hạn tải/giải nén và máy chủ updater được giữ.
- Lỗi chứng chỉ được phân biệt với lỗi kết nối thông thường; FFmpeg không thử lại ba lần cùng lỗi chứng chỉ. Tải lỗi không để lại file cài chưa xác minh.
- CA bundle được đóng vào `_internal/certifi/cacert.pem`, kèm giấy phép MPL-2.0. Không yêu cầu người dùng cài Python hoặc thêm chứng chỉ thủ công cho các nguồn tải công khai thông thường.

Tài liệu gốc: [Python SSLContext](https://docs.python.org/3.14/library/ssl.html#ssl.SSLContext.load_default_certs), [certifi](https://github.com/certifi/python-certifi).

## Kiểm chứng

- 114 kiểm thử local và [Windows CI](https://github.com/x1-2023/template-studio/actions/runs/39389616663) qua; Ruff F và `git diff --check` qua.
- Máy chủ TLS localhost: chứng chỉ tự ký bị từ chối; CA tin cậy riêng hoạt động; sai hostname vẫn bị từ chối. HTTP và chuyển hướng hạ HTTPS xuống HTTP bị chặn.
- Kho CA hệ điều hành giả lập trống: bundle vẫn nạp được trên 100 CA, giữ xác minh hostname/chứng chỉ.
- ZIP EXE giải nén vào thư mục sạch, PATH chỉ Windows, chưa có runtime. App tải thật FFmpeg/ffprobe, Whisper và model; xác minh checksum đúng, tự nhận 51 từ từ MP4, render 90 khung GPU có âm thanh và font ZY Trend đóng kèm.
- Worker EXE kiểm tra ba nguồn GitHub API, release-assets GitHub và Hugging Face qua HTTPS thành công; `verify_hostname=true`, `verify_required=true`.

Gói kiểm chứng: ZIP 257.818.100 byte, SHA-256:

```text
764c2492c2c83db381b7c997ed397bc8e8cbfa8df5103b95542d6c4731c556a1
```

CA bundle 238.856 byte, SHA-256 `50f79f98dac192b20dbf73f35c56f0b0c557ab267ff5199d1117cc1180b70785`. Kết quả cục bộ trong `.runtime/qa-https-137/verified.json`; kịch bản `.runtime/qa_https_137.py`.

## Cập nhật từ máy đang lỗi SSL

Nếu bản cũ không kết nối được updater, tải ZIP mới bằng trình duyệt. Tắt app, chép **nội dung thư mục TemplateStudio trong ZIP** đè vào thư mục app cũ; giữ `data/`, `runtime/`, `exports/`. Mở lại app và bấm **Thử lại FFmpeg** nếu runtime chưa có. Những lần sau có thể dùng updater bình thường khi kết nối HTTPS đã được xác minh.

Ngày/giờ sai hoặc proxy/phần mềm chặn HTTPS chưa được Windows tin cậy vẫn cần xử lý trên máy/mạng tương ứng; app không bỏ qua xác minh để tải file.
