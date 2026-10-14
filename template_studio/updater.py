"""Cập nhật portable từ GitHub Releases, kiểm tra hash và ZIP trước khi cài."""
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid
import zipfile
from pathlib import Path, PurePosixPath

from offline_studio.cancellation import check_cancelled
from offline_studio.config import atomic_json
from .version import VERSION, REPOSITORY, ASSET_NAME

MAX_DOWNLOAD = 1024 ** 3
MAX_EXTRACTED = 3 * 1024 ** 3
MANAGED = {'TemplateStudio.exe', '_internal', 'LICENSE', 'THIRD_PARTY_NOTICES.md',
           'README.md', 'release.json'}
REQUIRED = {'TemplateStudio.exe', '_internal', 'release.json'}


def version_tuple(value):
    if not isinstance(value, str) or not re.fullmatch(r'v?\d+\.\d+\.\d+', value):
        raise ValueError('Phiên bản phải có dạng v1.2.3, chỉ nhận bản ổn định.')
    return tuple(map(int, value.lstrip('v').split('.')))


def _open(url):
    request = urllib.request.Request(url, headers={
        'User-Agent': 'TemplateStudio/' + VERSION,
        'Accept': 'application/vnd.github+json' if url.startswith('https://api.github.com/') else 'application/octet-stream',
        'X-GitHub-Api-Version': '2022-11-28',
    })
    response = urllib.request.urlopen(request, timeout=20)
    final = urllib.parse.urlsplit(response.geturl())
    if final.scheme != 'https' or final.hostname not in {
        'api.github.com', 'github.com', 'release-assets.githubusercontent.com',
        'objects.githubusercontent.com'}:
        response.close()
        raise ValueError('Máy chủ tải xuống không thuộc GitHub.')
    return response


def parse_release(release, current=VERSION):
    if release.get('draft') or release.get('prerelease'):
        return None
    tag = release.get('tag_name', '')
    if version_tuple(tag) <= version_tuple(current):
        return None
    asset = next((item for item in release.get('assets', []) if item.get('name') == ASSET_NAME), None)
    if not asset:
        raise ValueError('Bản phát hành chưa có gói Windows x64.')
    expected_url = f'https://github.com/{REPOSITORY}/releases/download/{tag}/{ASSET_NAME}'
    digest = asset.get('digest') or ''
    if asset.get('browser_download_url') != expected_url:
        raise ValueError('Gói cập nhật không thuộc repository đã cấu hình.')
    if not re.fullmatch(r'sha256:[a-fA-F0-9]{64}', digest):
        raise ValueError('GitHub chưa cung cấp SHA-256; từ chối cập nhật chưa xác minh.')
    size = asset.get('size', 0)
    if not isinstance(size, int) or not 0 < size <= MAX_DOWNLOAD or asset.get('state') != 'uploaded':
        raise ValueError('Kích thước hoặc trạng thái gói cập nhật không hợp lệ.')
    return dict(version=tag.lstrip('v'), url=expected_url, size=size,
                sha256=digest.split(':', 1)[1].lower(),
                page=f'https://github.com/{REPOSITORY}/releases/tag/{tag}')


def check_update():
    try:
        with _open(f'https://api.github.com/repos/{REPOSITORY}/releases/latest') as response:
            payload = response.read(2 * 1024 ** 2 + 1)
        if len(payload) > 2 * 1024 ** 2:
            raise ValueError('Thông tin phát hành vượt giới hạn.')
        return parse_release(json.loads(payload))
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return None
        raise RuntimeError(f'GitHub trả mã {error.code}; thử kiểm tra lại sau.') from error
    except (urllib.error.URLError, TimeoutError) as error:
        raise RuntimeError('Không kết nối được GitHub; vẫn có thể dùng app offline.') from error


def extract_package(archive, destination, version):
    """Kiểm tra toàn bộ danh sách trước khi giải nén; chặn đường dẫn thoát và liên kết."""
    destination = Path(destination)
    with zipfile.ZipFile(archive) as package:
        entries = package.infolist()
        if len(entries) > 40000 or sum(item.file_size for item in entries) > MAX_EXTRACTED:
            raise ValueError('Gói giải nén vượt giới hạn.')
        seen, tops = set(), set()
        for item in entries:
            name = item.orig_filename
            if name != item.filename:
                raise ValueError('Đường dẫn ZIP bị chuẩn hóa hoặc cắt ngắn khi đọc.')
            parts = PurePosixPath(name).parts
            if not parts or parts[0] != 'TemplateStudio' or '\\' in name or name.startswith('/'):
                raise ValueError('Gói ZIP phải chứa thư mục TemplateStudio.')
            if name.rstrip('/') != PurePosixPath(name).as_posix() or any(character in name for character in '<>"|?*'):
                raise ValueError('Đường dẫn ZIP mơ hồ hoặc chứa ký tự cấm trên Windows.')
            if any(part in {'.', '..'} or ':' in part or part.rstrip(' .') != part
                   or re.fullmatch(r'(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?', part, re.I)
                   for part in parts):
                raise ValueError('Đường dẫn ZIP không an toàn.')
            if any(ord(character) < 32 for character in name):
                raise ValueError('Đường dẫn ZIP chứa ký tự điều khiển.')
            mode = item.external_attr >> 16
            if stat.S_ISLNK(mode) or (stat.S_IFMT(mode) not in {0, stat.S_IFREG, stat.S_IFDIR}):
                raise ValueError('Không nhận liên kết hoặc file đặc biệt trong ZIP.')
            identity = name.rstrip('/').casefold()
            if identity in seen:
                raise ValueError('Gói ZIP có đường dẫn trùng nhau.')
            seen.add(identity)
            if len(parts) > 1:
                if parts[1] not in MANAGED:
                    raise ValueError('Gói cập nhật chứa dữ liệu ngoài ứng dụng.')
                tops.add(parts[1])
        if not REQUIRED.issubset(tops):
            raise ValueError('Gói cập nhật thiếu EXE, runtime Qt hoặc manifest.')
        destination.mkdir(parents=True, exist_ok=True)
        if shutil.disk_usage(destination).free < sum(item.file_size for item in entries) + 256 * 1024 ** 2:
            raise OSError('Không đủ dung lượng để giải nén cập nhật.')
        for item in entries:
            check_cancelled()
            package.extract(item, destination)
    stage = destination / 'TemplateStudio'
    manifest = json.loads((stage / 'release.json').read_text(encoding='utf-8'))
    if manifest != {'version': version, 'platform': 'windows-x64'}:
        raise ValueError('Manifest không khớp phiên bản hoặc kiến trúc.')
    with (stage / 'TemplateStudio.exe').open('rb') as executable:
        signature = executable.read(2)
    if not (stage / '_internal').is_dir() or signature != b'MZ':
        raise ValueError('Gói cập nhật không phải ứng dụng Windows hợp lệ.')
    return stage


def prepare_update(release, home, progress=lambda value: None):
    if os.name != 'nt' or not getattr(sys, 'frozen', False):
        raise RuntimeError('Chỉ cài cập nhật trong bản EXE portable Windows.')
    target = Path(sys.executable).resolve().parent
    if sys.executable and Path(sys.executable).name != 'TemplateStudio.exe':
        raise ValueError('Không xác định được thư mục ứng dụng.')
    # Mỗi lần cập nhật có staging riêng; không tái sử dụng file cũ chưa xác minh.
    token = uuid.uuid4().hex
    # Staging và backup cùng ổ với EXE để đổi thư mục nguyên tử, kể cả khi dữ liệu nằm trên ổ khác.
    job = target / '.updates' / token
    job.mkdir(parents=True)
    archive = job / ASSET_NAME
    if shutil.disk_usage(job).free < release['size'] * 4 + 256 * 1024 ** 2:
        raise OSError('Không đủ dung lượng cho cập nhật và bản sao phục hồi.')
    digest, received = hashlib.sha256(), 0
    with _open(release['url']) as response, archive.open('xb') as output:
        while True:
            check_cancelled()
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            received += len(chunk)
            if received > release['size'] or received > MAX_DOWNLOAD:
                raise ValueError('Gói tải xuống vượt kích thước công bố.')
            digest.update(chunk)
            output.write(chunk)
            progress(received / release['size'] * 90)
    if received != release['size'] or digest.hexdigest() != release['sha256']:
        archive.unlink(missing_ok=True)
        raise ValueError('SHA-256 hoặc kích thước không khớp; đã từ chối gói cập nhật.')
    stage = extract_package(archive, job / 'stage', release['version'])
    plan = job / 'plan.json'
    atomic_json(plan, dict(target=str(target), stage=str(stage), job=str(job), home=str(Path(home).resolve()),
                           parent_pid=os.getpid(), token=token, version=release['version']))
    shutil.copy2(Path(__file__).with_name('apply_update.ps1'), job / 'apply_update.ps1')
    progress(100)
    return plan


def launch_update(plan):
    powershell = Path(os.environ.get('SystemRoot', r'C:\Windows')) / 'System32/WindowsPowerShell/v1.0/powershell.exe'
    subprocess.Popen([str(powershell), '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass',
                      '-File', str(Path(plan).with_name('apply_update.ps1')), '-PlanPath', str(plan)],
                     cwd=str(Path(plan).parent), creationflags=subprocess.CREATE_NO_WINDOW,
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
