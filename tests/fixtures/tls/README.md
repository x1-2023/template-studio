# Chứng chỉ chỉ dùng trong kiểm thử

`localhost.pem` và `localhost-key.pem` là cặp chứng chỉ tự ký/khóa giả lập công khai để chạy máy chủ TLS trên loopback trong `test_network.py`. Không dùng cho máy chủ thật, không cài vào kho tin cậy Windows và không đóng kèm bản EXE.

Chứng chỉ chỉ có SAN `localhost`; kiểm thử xác nhận kết nối qua IP bị từ chối dù CA đã được tin cậy riêng trong bài thử. App mặc định phải từ chối chứng chỉ tự ký này.
