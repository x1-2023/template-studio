"""Chuẩn bị FFmpeg từ nhà phát hành gốc; không phân phối lại binary trong gói app."""
import hashlib
import os
import shutil
import urllib.request
import uuid
import zipfile
from pathlib import Path

from offline_studio.cancellation import check_cancelled
from offline_studio.process import binary

MEDIA_VERSION = '7.1.1'
MEDIA_URL = 'https://github.com/GyanD/codexffmpeg/releases/download/7.1.1/ffmpeg-7.1.1-essentials_build.zip'
MEDIA_SHA256 = '04861d3339c5ebe38b56c19a15cf2c0cc97f5de4fa8910e4d47e5e6404e4a2d4'
MAX_ARCHIVE = 256 * 1024 ** 2
FILES = {'ffmpeg.exe': 'b90225987bdd042cca09a1efb5e34e9848f2d1dbf5fbcd388753a44145522997',
         'ffprobe.exe': '05e8fa639450f8191635192871ae37a3ec3e4638fa12f3b7d49c6522ba16a8ed'}


def install_archive(archive, destination):
    archive, destination = Path(archive), Path(destination)
    if archive.stat().st_size > MAX_ARCHIVE:
        raise ValueError('Gói FFmpeg vượt giới hạn kích thước.')
    with archive.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    if digest != MEDIA_SHA256:
        raise ValueError('Checksum FFmpeg không khớp; không cài runtime.')
    stage = destination.parent / ('.media-' + uuid.uuid4().hex)
    stage.mkdir(parents=True)
    try:
        with zipfile.ZipFile(archive) as package:
            for name, expected in FILES.items():
                member = next((entry for entry in package.infolist()
                               if entry.filename.lower().endswith('/bin/' + name)), None)
                if member is None or member.file_size > 128 * 1024 ** 2:
                    raise ValueError('Gói FFmpeg thiếu công cụ hoặc sai kích thước.')
                output = stage / name
                with package.open(member) as source, output.open('xb') as target:
                    shutil.copyfileobj(source, target, length=1024 * 1024)
                with output.open('rb') as source:
                    if hashlib.file_digest(source, 'sha256').hexdigest() != expected:
                        raise ValueError('Binary FFmpeg không khớp bản đã kiểm thử.')
                check_cancelled()
        destination.mkdir(parents=True, exist_ok=True)
        for name in FILES:
            (stage / name).replace(destination / name)
    finally:
        # Chỉ xóa staging riêng do hàm này tạo, đã xác minh nằm trong thư mục runtime.
        if not stage.resolve().is_relative_to(destination.parent.resolve()) or stage.is_symlink():
            raise ValueError('Không thể dọn staging ngoài thư mục runtime.')
        shutil.rmtree(stage)
    return destination


def ensure_media(home, progress=lambda value: None, archive=None):
    home = Path(home).resolve()
    os.environ['TEMPLATE_STUDIO_HOME'] = str(home)
    if archive is None:
        try:
            binary('ffmpeg')
            binary('ffprobe')
            return
        except FileNotFoundError:
            pass
    destination = home / 'runtime' / 'media' / 'bin'
    if archive:
        install_archive(archive, destination)
        return
    cache = home / 'cache'
    cache.mkdir(parents=True, exist_ok=True)
    if shutil.disk_usage(home).free < 600 * 1024 ** 2:
        raise OSError('Cần ít nhất 600 MiB trống để chuẩn bị FFmpeg.')
    temporary = cache / ('ffmpeg-' + uuid.uuid4().hex + '.zip')
    progress('Lần đầu: đang tải FFmpeg từ GitHub/Gyan (~100 MB)…')
    request = urllib.request.Request(MEDIA_URL, headers={'User-Agent': 'TemplateStudio/1.0', 'Accept': 'application/octet-stream'})
    try:
        with urllib.request.urlopen(request, timeout=30) as response, temporary.open('xb') as output:
            received = 0
            while True:
                check_cancelled()
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                received += len(chunk)
                if received > MAX_ARCHIVE:
                    raise ValueError('Gói FFmpeg vượt giới hạn tải xuống.')
                output.write(chunk)
                progress(f'Đang tải FFmpeg · {received / 1024 ** 2:.0f} MiB')
        progress('Đang xác minh và giải nén FFmpeg…')
        install_archive(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
