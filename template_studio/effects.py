"""Adapter Video-FX: catalog, ảnh xem trước và render tuần tự, không giữ cả clip trong RAM."""
import hashlib
import math
import subprocess
import threading
from collections import deque
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from video_fx.catalog.loader import load_catalog
from video_fx.config import VideoEffectConfig
from video_fx.resolver import resolve_engine

from offline_studio.cancellation import check_cancelled, managed_process
from offline_studio.process import binary, NO_WINDOW

CATEGORIES = {
    'glitch_digital': 'Glitch / kỹ thuật số', 'vhs_analog': 'VHS / băng cũ',
    'cinematic_color': 'Màu điện ảnh', 'camera_lens': 'Camera / ống kính',
    'light_particle_weather': 'Ánh sáng / hạt / thời tiết',
    'stylization_artistic': 'Nghệ thuật',
}


@lru_cache(maxsize=1)
def catalog():
    return [{'id': 'none', 'name': 'Không dùng filter', 'category': 'Tất cả', 'thumbnail': ''}] + [
        dict(id=slug, name=entry['name'], category=CATEGORIES[entry['categories'][0]], thumbnail='')
        for slug, entry in load_catalog().items()]


def effect_name(slug):
    return next((entry['name'] for entry in catalog() if entry['id'] == slug), 'Không dùng filter')


class FrameProcessor:
    def __init__(self, slug, intensity):
        self.slug, self.last = slug, None
        self.config = VideoEffectConfig(effect=slug, intensity=intensity, seed=2026)
        self.engine, self.params = resolve_engine(slug) if slug != 'none' else (None, {})

    def process(self, frame, index, total):
        if self.engine is None or self.config.intensity <= 0:
            return frame
        if self.engine.engine_key == 'frame_drop':
            # Các engine thời gian của thư viện dùng list toàn bộ clip; giữ một frame thay thế.
            if self.last is None:
                self.last = frame.copy()
            if self.params.get('ghost_mode'):
                result = (frame.astype(np.float32) * .7 + self.last.astype(np.float32) * .3).astype(np.uint8)
                self.last = frame.copy()
                return result
            hold = max(2, int(2 + self.config.intensity * (self.params.get('hold_frames', 4) + 8)))
            if index % hold == 0:
                self.last = frame.copy()
            return self.last.copy()
        result = self.engine.process_frame(frame, self.config, self.params, index, total)
        if result.shape != frame.shape or result.dtype != np.uint8:
            raise ValueError('Engine hiệu ứng trả frame sai kích thước hoặc kiểu dữ liệu.')
        return result


def thumbnails(home, source=None):
    stamp = 'demo-v1'
    if source:
        source = Path(source)
        info = source.stat()
        stamp = f'{source.resolve()}:{info.st_size}:{info.st_mtime_ns}'
    folder = Path(home) / 'cache' / 'effect-thumbnails' / hashlib.sha256(stamp.encode()).hexdigest()[:20]
    folder.mkdir(parents=True, exist_ok=True)
    if source:
        with managed_process([binary('ffmpeg'), '-v', 'error', '-nostdin', '-ss', '0', '-i', str(source),
                              '-vf', 'scale=180:320:force_original_aspect_ratio=increase,crop=180:320',
                              '-frames:v', '1', '-f', 'rawvideo', '-pix_fmt', 'rgba', 'pipe:1'],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=NO_WINDOW) as process:
            raw, error = process.communicate(timeout=30)
            if process.returncode or len(raw) != 180 * 320 * 4:
                raise ValueError('Không đọc được frame làm thumbnail: ' + error.decode('utf-8', errors='replace')[-600:])
        frame = np.frombuffer(raw, dtype=np.uint8).reshape(320, 180, 4).copy()
    else:
        image = Image.new('RGBA', (180, 320), (25, 65, 125, 255))
        draw = ImageDraw.Draw(image)
        for y in range(320):
            draw.line([(0, y), (180, y)], fill=(int(40+y*.6), int(110+y*.2), int(200-y*.3), 255))
        draw.ellipse((20, 55, 145, 185), fill=(240, 173, 63, 255))
        draw.polygon([(0, 320), (60, 145), (125, 320)], fill=(45, 185, 146, 255))
        draw.rectangle((105, 195, 160, 290), fill=(218, 80, 120, 255))
        frame = np.asarray(image).copy()
    entries = []
    for entry in catalog():
        check_cancelled()
        destination = folder / (entry['id'] + '.jpg')
        if not destination.exists():
            processor = FrameProcessor(entry['id'], .65)
            output = processor.process(frame.copy(), 15, 90)
            Image.fromarray(output[:, :, :3]).save(destination, quality=85)
        entries.append({**entry, 'thumbnail': destination.resolve().as_uri()})
    return entries


def stream_effect(input_args, output_args, width, height, duration, settings, progress, offset, total_duration):
    """FFmpeg giải mã RGBA → xử lý từng frame → FFmpeg mã hóa; RAM theo kích thước frame."""
    processor = FrameProcessor(settings['effect'], settings['effectIntensity'] / 100)
    frame_bytes = width * height * 4
    total = max(1, math.ceil(total_duration * 30))
    start_frame = round(offset * 30)
    logs = [deque(maxlen=80), deque(maxlen=80)]
    done, timed_out = threading.Event(), threading.Event()
    with managed_process(input_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=NO_WINDOW) as decoder:
        with managed_process(output_args, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
                             stderr=subprocess.PIPE, creationflags=NO_WINDOW) as encoder:
            def drain(process, log):
                for line in iter(process.stderr.readline, b''):
                    log.append(line.decode('utf-8', errors='replace').rstrip())
            readers = [threading.Thread(target=drain, args=(process, log), daemon=True)
                       for process, log in zip((decoder, encoder), logs)]
            for reader in readers:
                reader.start()
            def watchdog():
                if not done.wait(max(600, duration * 100)):
                    timed_out.set()
                    for process in (decoder, encoder):
                        if process.poll() is None:
                            process.kill()
            watcher = threading.Thread(target=watchdog, daemon=True)
            watcher.start()
            count = 0
            try:
                while True:
                    check_cancelled()
                    raw = decoder.stdout.read(frame_bytes)
                    if not raw:
                        break
                    if len(raw) != frame_bytes:
                        raise ValueError('FFmpeg trả frame RGBA không đầy đủ.')
                    frame = np.frombuffer(raw, dtype=np.uint8).reshape(height, width, 4).copy()
                    absolute = start_frame + count
                    active = settings['effectDuration'] == 0 or absolute / 30 < settings['effectDuration']
                    output = processor.process(frame, absolute, total) if active else frame
                    encoder.stdin.write(output.tobytes())
                    count += 1
                    if count % 5 == 0:
                        progress(min(99, count / max(1, duration * 30) * 100))
                encoder.stdin.close()
                decoder.wait(timeout=30)
                encoder.wait(timeout=60)
            except (BrokenPipeError, OSError) as error:
                check_cancelled()
                raise RuntimeError('\n'.join(line for log in logs for line in log)[-8000:] or str(error)) from error
            finally:
                done.set()
                watcher.join(timeout=1)
                for reader in readers:
                    reader.join(timeout=1)
            check_cancelled()
            if timed_out.is_set():
                raise TimeoutError('Render hiệu ứng vượt thời gian chờ.')
            if decoder.returncode or encoder.returncode or not count:
                raise RuntimeError('\n'.join(line for log in logs for line in log)[-8000:] or 'Không xuất được frame hiệu ứng.')
