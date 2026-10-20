"""HTTPS có CA đóng kèm, giữ xác minh chứng chỉ và tên máy chủ."""

import ssl
import urllib.error
import urllib.parse
import urllib.request

import certifi


def ssl_context():
    # Nạp Mozilla CA trước, bổ sung chứng chỉ Windows/proxy đã được máy tin cậy.
    context = ssl.create_default_context(cafile=certifi.where())
    context.load_default_certs()
    return context


class HttpsRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        if urllib.parse.urlsplit(new_url).scheme != "https":
            raise ValueError("Từ chối chuyển hướng tải xuống sang kết nối không có HTTPS.")
        return super().redirect_request(request, response, code, message, headers, new_url)


def open_https(request, timeout=30):
    url = request.full_url if isinstance(request, urllib.request.Request) else request
    if urllib.parse.urlsplit(url).scheme != "https":
        raise ValueError("Tải xuống yêu cầu kết nối HTTPS.")
    opener = urllib.request.build_opener(
        urllib.request.HTTPSHandler(context=ssl_context()), HttpsRedirectHandler()
    )
    return opener.open(request, timeout=timeout)


def is_certificate_error(error):
    seen = set()
    while isinstance(error, BaseException) and id(error) not in seen:
        seen.add(id(error))
        if isinstance(error, ssl.SSLCertVerificationError) or "CERTIFICATE_VERIFY_FAILED" in str(error):
            return True
        error = getattr(error, "reason", None) or error.__cause__ or error.__context__
    return False


def error_hint(error):
    if is_certificate_error(error):
        return ("Lỗi chứng chỉ HTTPS. Kiểm tra ngày/giờ Windows; "
                "nếu đang dùng bản cũ, tải ZIP app mới bằng trình duyệt. "
                "Mạng có proxy hoặc phần mềm kiểm tra HTTPS cần chứng chỉ tin cậy trong Windows.")
    return str(error)[:500]


def check_connections():
    """Chẩn đoán CLI với URL cố định; chỉ đọc một byte từ các gói lớn."""
    from .media_setup import MEDIA_URL
    from .speech import MODEL_URL
    from .version import REPOSITORY, VERSION

    checks = []
    for name, url in (
        ("github", f"https://api.github.com/repos/{REPOSITORY}/releases/latest"),
        ("ffmpeg", MEDIA_URL),
        ("speech", MODEL_URL),
    ):
        request = urllib.request.Request(url, headers={"User-Agent": "BetaRender/" + VERSION, "Range": "bytes=0-0"})
        try:
            with open_https(request) as response:
                response.read(1)
                checks.append(dict(name=name, ok=True, status=response.status,
                                   host=urllib.parse.urlsplit(response.geturl()).hostname))
        except (OSError, ValueError) as error:
            checks.append(dict(name=name, ok=False, error=error_hint(error)))
    context = ssl_context()
    return dict(ok=all(item["ok"] for item in checks), checks=checks, ca_version=certifi.__version__,
                ca_count=context.cert_store_stats()["x509_ca"], verify_hostname=context.check_hostname,
                verify_required=context.verify_mode == ssl.CERT_REQUIRED)
