"""Nhận diện phần cứng và chọn số luồng theo phép đo local, không thêm dependency."""
import ctypes
import hashlib
import json
import os
import platform
import shutil
import subprocess
import threading
import time
from functools import lru_cache
from .config import DATA, atomic_json
from .process import binary, run, NO_WINDOW
from .cancellation import check_cancelled

_TUNE_LOCK = threading.Lock()


def format_time(seconds):
    seconds = max(0, int(seconds or 0))
    hours, rest = divmod(seconds, 3600)
    minutes, seconds = divmod(rest, 60)
    return f'{hours:02d}:{minutes:02d}:{seconds:02d}'


@lru_cache(maxsize=1)
def detect():
    logical = max(1, getattr(os, 'process_cpu_count', os.cpu_count)() or 1)
    cpu = platform.processor() or 'CPU'
    total = 0
    if os.name == 'nt':
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r'HARDWARE\DESCRIPTION\System\CentralProcessor\0') as key:
                cpu = winreg.QueryValueEx(key, 'ProcessorNameString')[0].strip()
        except OSError:
            pass
        class Memory(ctypes.Structure):
            _fields_ = [('length', ctypes.c_ulong), ('load', ctypes.c_ulong),
                       *[(name, ctypes.c_ulonglong) for name in ('total', 'available', 'page_total', 'page_available', 'virtual_total', 'virtual_available', 'extended')]]
        memory = Memory()
        memory.length = ctypes.sizeof(memory)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(memory)):
            total = round(memory.total / 1024**3, 1)
    gpus = []
    smi = shutil.which('nvidia-smi')
    if smi:
        try:
            output = subprocess.run([smi, '--query-gpu=name,memory.total,driver_version', '--format=csv,noheader,nounits'],
                                    capture_output=True, text=True, timeout=5, creationflags=NO_WINDOW)
            if output.returncode == 0:
                for line in output.stdout.splitlines():
                    name, memory, driver = [part.strip() for part in line.split(',')]
                    gpus.append({'name': name, 'vram_mb': int(memory), 'driver': driver})
        except (OSError, ValueError, subprocess.TimeoutExpired):
            pass
    nvenc = False
    try:
        # Encoder có trong FFmpeg chưa chứng minh driver/GPU dùng được: thử encode thật.
        run([binary('ffmpeg'), '-v', 'error', '-nostdin', '-f', 'lavfi', '-i', 'color=s=640x360:r=30',
             '-frames:v', '2', '-c:v', 'h264_nvenc', '-f', 'null', '-'], timeout=15)
        nvenc = True
    except (RuntimeError, TimeoutError, FileNotFoundError):
        pass
    return {'cpu': cpu, 'logical_threads': logical, 'ram_gb': total, 'gpus': gpus, 'nvenc': nvenc}


def describe(info):
    gpu = ' · '.join(f"{g['name']} {g['vram_mb'] / 1024:.0f} GB" for g in info['gpus']) or 'Không có NVIDIA được nhận diện'
    return f"{info['cpu']} · {info['logical_threads']} luồng · RAM {info['ram_gb']:g} GB\n{gpu}\nEncode: {'NVENC' if info['nvenc'] else 'CPU'} · tự đo cấu hình nhanh"


def candidates(info):
    maximum = info['logical_threads']
    return sorted({min(maximum, n) for n in (4, 8, 16, maximum)})


def tune(profile, measure, progress):
    """Đo tuần tự 15 giây đầu, cache 7 ngày theo máy và đặc điểm graph."""
    info = detect()
    identity = {'version': 2, 'hardware': info, 'profile': profile,
                'ffmpeg_mtime': os.stat(binary('ffmpeg')).st_mtime_ns}
    key = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    path = DATA / 'performance' / (key + '.json')
    while not _TUNE_LOCK.acquire(timeout=.2):
        check_cancelled()
    try:
        try:
            cached = json.loads(path.read_text(encoding='utf-8'))
            if 0 <= time.time() - cached['saved_at'] < 7 * 86400 and cached['threads'] in candidates(info):
                return cached
        except (OSError, ValueError, KeyError, TypeError):
            pass
        rows = []
        for threads in candidates(info):
            progress(9, f'Đang đo hiệu năng phần cứng: {threads} luồng')
            began = time.monotonic()
            try:
                measure(threads)
            except (RuntimeError, TimeoutError) as error:
                if any(marker in str(error).lower() for marker in ('cuda', 'nvenc', 'nvidia', 'no capable devices')):
                    raise
                rows.append({'threads': threads, 'error': str(error)[-1000:]})
            else:
                rows.append({'threads': threads, 'seconds': time.monotonic() - began})
        successful = [row for row in rows if 'seconds' in row]
        if not successful:
            raise RuntimeError('Không đo được cấu hình render: ' + str(rows))
        fastest = min(row['seconds'] for row in successful)
        # Sai khác rất nhỏ có thể là nhiễu; chọn nhiều luồng hơn để đủ dư địa cho cảnh phức tạp.
        best = max((row for row in successful if row['seconds'] <= fastest * 1.03), key=lambda row: row['threads'])
        result = {'threads': best['threads'], 'saved_at': time.time(), 'samples': rows, 'hardware': info}
        atomic_json(path, result)
        return result
    finally:
        _TUNE_LOCK.release()
