"""Chuẩn bị FFmpeg từ nhà phát hành gốc; không phân phối lại binary trong gói app."""
import hashlib
import os
import shutil
import subprocess
import time
import urllib.request
import uuid
import zipfile
from pathlib import Path

from offline_studio.cancellation import check_cancelled
from offline_studio.process import NO_WINDOW, binary

MEDIA_VERSION = '7.1.1'
MEDIA_URL = 'https://github.com/GyanD/codexffmpeg/releases/download/7.1.1/ffmpeg-7.1.1-essentials_build.zip'
MEDIA_SHA256 = '04861d3339c5ebe38b56c19a15cf2c0cc97f5de4fa8910e4d47e5e6404e4a2d4'
MAX_ARCHIVE = 256 * 1024 ** 2
FILES = {'ffmpeg.exe': 'b90225987bdd042cca09a1efb5e34e9848f2d1dbf5fbcd388753a44145522997',
         'ffprobe.exe': '05e8fa639450f8191635192871ae37a3ec3e4638fa12f3b7d49c6522ba16a8ed'}
_VERIFIED = set()


def media_available(home):
    """Kiểm tra cả hai công cụ, không coi việc nhận GPU là runtime sẵn sàng."""
    home = Path(home).resolve()
    os.environ['TEMPLATE_STUDIO_HOME'] = str(home)
    try:
        paths = [Path(binary(name)) for name in ('ffmpeg', 'ffprobe')]
        stamp = tuple((str(path.resolve()), path.stat().st_size, path.stat().st_mtime_ns) for path in paths)
        if stamp in _VERIFIED:
            return True
        managed = home / 'runtime/media/bin'
        for path in paths:
            check_cancelled()
            if path.resolve().parent == managed:
                with path.open('rb') as stream:
                    if hashlib.file_digest(stream, 'sha256').hexdigest() != FILES[path.name]:
                        return False
            else:
                # Công cụ từ PATH/cache ngoài phải khởi động được, không chỉ tồn tại.
                result = subprocess.run([str(path), '-version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    timeout=10, creationflags=NO_WINDOW)
                expected = (path.stem.lower()+' version').encode('ascii')
                if result.returncode or expected not in result.stdout.lower():
                    return False
        _VERIFIED.add(stamp)
        return True
    except (OSError, subprocess.TimeoutExpired):
        return False


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
    if archive is None and media_available(home):
        return
    destination = home / 'runtime' / 'media' / 'bin'
    if archive:
        install_archive(archive, destination)
        return
    cache = home / 'cache'
    cache.mkdir(parents=True, exist_ok=True)
    cached_archive = cache / ('ffmpeg-' + MEDIA_VERSION + '-verified.zip')
    if cached_archive.is_file():
        progress('Đang sửa FFmpeg/ffprobe từ gói đã tải…')
        try:
            install_archive(cached_archive, destination)
            return
        except (ValueError, zipfile.BadZipFile):
            # Chỉ xóa cache cố định do app tạo khi nội dung không còn đúng checksum.
            cached_archive.unlink()
    if shutil.disk_usage(home).free < 600 * 1024 ** 2:
        raise OSError('Cần ít nhất 600 MiB trống để chuẩn bị FFmpeg.')
    temporary = cache / ('ffmpeg-' + uuid.uuid4().hex + '.zip')
    progress('Thiếu hoặc hỏng FFmpeg/ffprobe. Đang tải bộ công cụ từ GitHub/Gyan (~100 MB)…')
    request = urllib.request.Request(MEDIA_URL, headers={'User-Agent': 'TemplateStudio/1.0', 'Accept': 'application/octet-stream'})
    try:
        for attempt in range(3):
            check_cancelled()
            try:
                with urllib.request.urlopen(request, timeout=30) as response, temporary.open('wb') as output:
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
                break
            except (OSError, EOFError) as error:
                if attempt == 2:
                    raise RuntimeError('Không tải được FFmpeg/ffprobe. Kiểm tra mạng rồi bấm Thử lại FFmpeg. '
                                       'Có thể chọn ZIP FFmpeg đã tải trong Cài đặt. Chi tiết: '+str(error)) from error
                progress(f'Tải FFmpeg bị gián đoạn. Đang thử lại ({attempt+2}/3)…')
                time.sleep(.5)
        progress('Đang xác minh và giải nén FFmpeg…')
        install_archive(temporary, destination)
        temporary.replace(cached_archive)
    finally:
        temporary.unlink(missing_ok=True)
