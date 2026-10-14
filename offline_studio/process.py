"""Chạy công cụ local có hủy, timeout và log giới hạn."""
import json
import os
import queue
import shutil
import subprocess
import threading
import time
from collections import deque
from pathlib import Path
from .config import ROOT, ASSETS, APP_ROOT
from .cancellation import managed_process, check_cancelled

NO_WINDOW = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0


def binary(name):
    home = Path(os.environ['TEMPLATE_STUDIO_HOME']) if os.environ.get('TEMPLATE_STUDIO_HOME') else APP_ROOT / 'data/template-studio'
    for directory in (home / 'runtime/media/bin', APP_ROOT / 'runtime/media/bin', ASSETS / 'bin', ROOT / 'desktop/bin', ROOT / '.runtime/ffmpeg/bin'):
        path = directory / (name + ('.exe' if os.name == 'nt' else ''))
        if path.is_file():
            return str(path)
    found = shutil.which(name)
    if not found:
        raise FileNotFoundError(f'Thiếu công cụ local {name}. Chuẩn bị gói offline trước khi chạy.')
    return found


def run(arguments, cwd=None, timeout=3600, progress=None, duration=0):
    errors = deque(maxlen=100)
    lines = queue.Queue(maxsize=2048)
    with managed_process(arguments, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         text=True, encoding='utf-8', errors='replace', creationflags=NO_WINDOW) as process:
        def read_output():
            for line in process.stdout:
                try:
                    lines.put_nowait(line)
                except queue.Full:
                    pass
        def read_error():
            for line in process.stderr:
                errors.append(line.rstrip())
        readers = [threading.Thread(target=f, daemon=True) for f in (read_output, read_error)]
        for reader in readers:
            reader.start()
        began = time.monotonic()
        while process.poll() is None:
            check_cancelled()
            if time.monotonic() - began > timeout:
                raise TimeoutError('Công cụ local vượt thời gian chờ; tác vụ đã dừng.')
            try:
                line = lines.get(timeout=.1).strip()
            except queue.Empty:
                continue
            if progress and duration and line.startswith('out_time_us='):
                try:
                    progress(min(99, float(line.split('=', 1)[1]) / 1e6 / duration * 100))
                except ValueError:
                    pass
        for reader in readers:
            reader.join(timeout=3)
        check_cancelled()
        if process.returncode:
            raise RuntimeError('\n'.join(errors)[-8000:] or f'Công cụ local kết thúc với mã {process.returncode}.')


def probe(path):
    check_cancelled()
    with managed_process([binary('ffprobe'), '-v', 'error', '-protocol_whitelist', 'file,pipe', '-show_format', '-show_streams', '-of', 'json', str(path)],
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=NO_WINDOW) as process:
        try:
            output, error = process.communicate(timeout=30)
        except subprocess.TimeoutExpired as exc:
            raise TimeoutError('Không đọc được metadata trong 30 giây.') from exc
        check_cancelled()
        if process.returncode:
            raise ValueError(error.decode('utf-8', errors='replace'))
    return json.loads(output)
