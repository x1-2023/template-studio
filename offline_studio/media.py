"""FFmpeg nền; cache preview và thay file gốc chỉ sau khi kiểm tra đầu ra."""
import hashlib
import json
import math
import os
import sqlite3
import subprocess
import tempfile
import threading
import time
from collections import deque
from contextlib import closing
from pathlib import Path

from .services import NO_WINDOW, ROOT, APP_ROOT
from .cancellation import check_cancelled, managed_process


def command(tool):
    for directory in [APP_ROOT / 'runtime/media/bin', ROOT / 'offline_studio/assets/bin', ROOT / '.runtime/ffmpeg/bin', ROOT / 'desktop/bin']:
        local = directory / (tool + ('.exe' if os.name == 'nt' else ''))
        if local.is_file():
            return str(local)
    return tool


def run(tool, args, timeout=120, cancel=None):
    check_cancelled()
    if cancel is None:
        cancel = threading.Event()
    with managed_process([command(tool), *map(str, args)], stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, creationflags=NO_WINDOW) as process:
        deadline = time.monotonic() + timeout
        while True:
            if cancel.is_set() or time.monotonic() >= deadline:
                process.kill()
                process.communicate()
                check_cancelled()
                if cancel.is_set():
                    return b''
                raise subprocess.TimeoutExpired(tool, timeout)
            try:
                output, errors = process.communicate(timeout=.2)
                check_cancelled()
                if process.returncode:
                    raise RuntimeError(errors.decode('utf-8', errors='replace')[-4000:])
                return output
            except subprocess.TimeoutExpired:
                continue


def scan(paths, only_mp4=False):
    found = {}
    extensions = {'.mp4'} if only_mp4 else {'.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv'}
    for raw in paths:
        check_cancelled()
        path = Path(raw).resolve()
        if not path.exists():
            raise FileNotFoundError(f'Không tìm thấy: {path}')
        for candidate in path.iterdir() if path.is_dir() else [path]:
            check_cancelled()
            if candidate.is_file() and candidate.suffix.lower() in extensions:
                candidate = candidate.resolve()
                stamp = candidate.stat()
                found[str(candidate).casefold()] = {'path': str(candidate), 'name': candidate.name,
                                                    'size': stamp.st_size, 'modified': stamp.st_mtime}
    return sorted(found.values(), key=lambda item: item['name'].casefold())


def probe(path):
    data = json.loads(run('ffprobe', ['-v', 'error', '-show_entries',
        'format=duration:stream=codec_type,codec_name,width,height,avg_frame_rate', '-of', 'json', '-i', path]))
    video = next((s for s in data.get('streams', []) if s.get('codec_type') == 'video'), None)
    duration = float(data.get('format', {}).get('duration', 0))
    if not video or not math.isfinite(duration) or duration <= 0:
        raise ValueError('Không đọc được video hoặc thời lượng.')
    a, b = video.get('avg_frame_rate', '0/1').split('/')
    return {'duration': duration, 'width': video['width'], 'height': video['height'],
            'fps': float(a) / float(b) if float(b) else 0, 'videoCodec': video['codec_name'],
            'hasAudio': any(s.get('codec_type') == 'audio' for s in data['streams'])}


def normalize_ranges(ranges, duration):
    if not ranges:
        raise ValueError('Video chưa có đoạn cần bỏ.')
    merged = []
    for item in sorted(ranges, key=lambda r: r['start']):
        start, end = float(item['start']), float(item['end'])
        if not all(map(math.isfinite, [start, end])) or start < 0 or end > duration + .001 or end - start < .05:
            raise ValueError('Khoảng cắt nằm ngoài video hoặc ngắn hơn 0,05 giây.')
        if merged and start <= merged[-1]['end'] + .001:
            merged[-1]['end'] = max(merged[-1]['end'], end)
        else:
            merged.append({'start': start, 'end': end})
    if len(merged) == 1 and merged[0]['start'] <= .001 and merged[0]['end'] >= duration - .05:
        raise ValueError('Không thể bỏ toàn bộ video.')
    return merged


def kept_ranges(ranges, duration):
    result, cursor = [], 0
    for r in ranges:
        if r['start'] - cursor > .01:
            result.append({'start': cursor, 'end': r['start']})
        cursor = r['end']
    if duration - cursor > .01:
        result.append({'start': cursor, 'end': duration})
    return result


class CutStore:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.path)) as connection, connection:
            connection.execute('CREATE TABLE IF NOT EXISTS cuts (path TEXT PRIMARY KEY, size INTEGER, modified INTEGER, data TEXT)')

    def get(self, path):
        path = Path(path).resolve()
        stamp = path.stat()
        with closing(sqlite3.connect(self.path)) as connection, connection:
            row = connection.execute('SELECT data FROM cuts WHERE path=? AND size=? AND modified=?',
                                     (str(path), stamp.st_size, stamp.st_mtime_ns)).fetchone()
        return json.loads(row[0]) if row else []

    def save(self, path, ranges):
        path = Path(path).resolve()
        stamp = path.stat()
        with closing(sqlite3.connect(self.path)) as connection, connection:
            connection.execute('INSERT OR REPLACE INTO cuts VALUES (?,?,?,?)',
                               (str(path), stamp.st_size, stamp.st_mtime_ns, json.dumps(ranges)))


def previews(path, start, span, cache, cancel, wave_color="0x25d9f2", wave_scale="lin"):
    stamp = Path(path).stat()
    key = hashlib.sha256(f'{path}:{stamp.st_size}:{stamp.st_mtime_ns}:{start:.3f}:{span:.3f}'.encode()).hexdigest()[:24]
    folder = Path(cache) / key
    folder.mkdir(parents=True, exist_ok=True)
    def generate(args, target, timeout=120):
        # Không đánh dấu file cache hoàn tất nếu tác vụ bị hủy giữa chừng.
        with tempfile.NamedTemporaryFile(dir=folder, suffix=target.suffix, delete=False) as handle:
            pending = Path(handle.name)
        try:
            run('ffmpeg', [*args, '-y', pending], timeout=timeout, cancel=cancel)
            if not cancel.is_set() and pending.stat().st_size:
                os.replace(pending, target)
        finally:
            pending.unlink(missing_ok=True)
    images = []
    for i in range(12):
        if cancel.is_set():
            return [], None
        target = folder / f'{i}.jpg'
        if not target.exists():
            generate(['-hide_banner', '-loglevel', 'error', '-ss', f'{start + span * (i + .5) / 12:.3f}',
                '-i', path, '-frames:v', '1', '-vf', 'scale=160:-2', '-q:v', '5'], target)
        if cancel.is_set():
            return [], None
        images.append(str(target))
    wave = folder / f'wave-{wave_color}-{wave_scale}.png'
    if not cancel.is_set() and not wave.exists():
        try:
            generate(['-hide_banner', '-loglevel', 'error', '-ss', f'{start:.3f}', '-i', path,
                '-t', f'{span:.3f}', '-filter_complex',
                f'aresample=1000,aformat=channel_layouts=mono,showwavespic=s=1200x60:colors={wave_color}:scale={wave_scale}',
                '-frames:v', '1'], wave, timeout=600)
        except (RuntimeError, subprocess.TimeoutExpired):
            pass
    return images, str(wave) if wave.exists() else None


def run_progress(args, expected, report):
    with managed_process([command('ffmpeg'), '-hide_banner', '-loglevel', 'error', *map(str, args),
                           '-progress', 'pipe:1', '-nostats'], stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='replace',
                          creationflags=NO_WINDOW) as process:
        errors = deque(maxlen=60)
        reader = threading.Thread(target=lambda: errors.extend(process.stderr), daemon=True)
        reader.start()
        for line in process.stdout:
            if line.startswith('out_time_us='):
                try:
                    report(min(.99, max(0, int(line.split('=')[1]) / 1e6 / expected)))
                except ValueError:
                    pass
        code = process.wait()
        reader.join()
        check_cancelled()
        if code:
            raise RuntimeError(''.join(errors)[-4000:])
    report(1.0)


def snap_ranges(path, keep, duration):
    snapped = []
    for r in keep:
        points = []
        for t in (r['start'], r['end']):
            if t < .001 or abs(t - duration) < .001:
                points.append(t)
                continue
            rows = run('ffprobe', ['-v', 'error', '-select_streams', 'v:0', '-skip_frame', 'nokey',
                '-read_intervals', f'{max(0, t - 5):.3f}%+12', '-show_entries',
                'frame=best_effort_timestamp_time', '-of', 'csv=p=0', '-i', path]).decode().splitlines()
            values = []
            for row in rows:
                try:
                    values.append(float(row.strip().rstrip(',')))
                except ValueError:
                    pass
            nearest = min(values, key=lambda n: abs(n - t), default=None)
            if nearest is None or abs(nearest - t) > .5:
                return None
            points.append(nearest)
        if points[1] - points[0] <= .01:
            return None
        snapped.append({'start': points[0], 'end': points[1]})
    return snapped


def cut_file(path, ranges, report=lambda value: None, policy="auto", codec="h264", quality="high"):
    if policy not in ("auto", "exact", "fast"):
        raise ValueError("Chế độ xuất Cutter không hợp lệ.")
    if codec not in ('h264', 'hevc') or quality not in ('compact', 'balanced', 'high'):
        raise ValueError('Định dạng hoặc chất lượng Cutter không hợp lệ.')
    path = Path(path).resolve()
    stamp = path.stat()
    info = probe(path)
    ranges = normalize_ranges(ranges, info['duration'])
    keep = kept_ranges(ranges, info['duration'])
    expected = sum(r['end'] - r['start'] for r in keep)
    with tempfile.TemporaryDirectory(prefix='.capcut-qt-cut-', dir=path.parent) as directory:
        work = Path(directory)
        output = work / 'output.mp4'
        snapped = snap_ranges(path, keep, info['duration']) if policy != 'exact' else None
        if policy == 'fast' and not snapped:
            raise ValueError('Không tìm được keyframe gần mốc; chọn Đúng mốc để encode.')
        mode = ''
        if snapped:
            try:
                for i, r in enumerate(snapped):
                    run_progress(['-ss', r['start'], '-i', path, '-t', r['end'] - r['start'],
                        '-map', '0:v:0', '-map', '0:a?', '-c', 'copy', '-avoid_negative_ts', 'make_zero',
                        '-y', work / f'part_{i}.mkv'], r['end'] - r['start'],
                        lambda p, index=i: report((index + p) / len(snapped) * .8))
                (work / 'concat.txt').write_text(''.join(f"file 'part_{i}.mkv'\n" for i in range(len(snapped))), encoding='utf-8')
                snap_duration = sum(r['end'] - r['start'] for r in snapped)
                run_progress(['-f', 'concat', '-safe', '0', '-i', work / 'concat.txt', '-map', '0:v:0', '-map', '0:a?',
                              '-c', 'copy', '-movflags', '+faststart', '-y', output], snap_duration, lambda p: report(.8 + p * .19))
                if abs(probe(output)['duration'] - snap_duration) > .5:
                    raise ValueError('Thời lượng bản Fast Copy lệch quá giới hạn.')
                mode, expected = 'Fast Copy', snap_duration
            except (RuntimeError, ValueError):
                if policy == 'fast':
                    raise
                mode = ''
        if not mode:
            parts = []
            for i, r in enumerate(keep):
                parts.append(f"[0:v:0]trim=start={r['start']:.6f}:end={r['end']:.6f},setpts=PTS-STARTPTS[v{i}]")
                if info['hasAudio']:
                    parts.append(f"[0:a:0]atrim=start={r['start']:.6f}:end={r['end']:.6f},asetpts=PTS-STARTPTS[a{i}]")
            inputs = ''.join(f'[v{i}]' + (f'[a{i}]' if info['hasAudio'] else '') for i in range(len(keep)))
            parts.append(f"{inputs}concat=n={len(keep)}:v=1:a={int(info['hasAudio'])}[vout]" + ('[aout]' if info['hasAudio'] else ''))
            filters = ';'.join(parts)
            if len(keep) == 1:
                # Accurate seek khi encode: bỏ giải mã phần trước đoạn cần giữ.
                span = keep[0]
                args = ['-ss', span['start'], '-i', path, '-t', span['end'] - span['start'], '-map', '0:v:0']
                if info['hasAudio']:
                    args += ['-map', '0:a:0', '-c:a', 'aac', '-b:a', '128k']
            else:
                args = ['-i', path, '-filter_complex', filters, '-map', '[vout]']
                if info['hasAudio']:
                    args += ['-map', '[aout]', '-c:a', 'aac', '-b:a', '128k']
            expected = sum(r['end'] - r['start'] for r in keep)
            cq, crf = {'compact': (29, 27), 'balanced': (24, 23), 'high': (19, 18)}[quality]
            encoders = [(codec + '_nvenc' if codec == 'hevc' else 'h264_nvenc', ['-preset', 'p1', '-rc', 'vbr', '-cq', str(cq), '-b:v', '0'], 'NVENC'),
                        ('libx265' if codec == 'hevc' else 'libx264', ['-preset', 'veryfast', '-crf', str(crf)], 'CPU')]
            if codec == 'hevc':
                args += ['-tag:v', 'hvc1']
            for encoder, options, label in encoders:
                try:
                    run_progress([*args, '-c:v', encoder, *options, '-pix_fmt', 'yuv420p', '-movflags', '+faststart', '-y', output],
                                 expected, lambda p: report(p * .99))
                    mode = label
                    break
                except RuntimeError:
                    if label == 'CPU':
                        raise
        verified = probe(output)
        if output.stat().st_size < 1024 or abs(verified['duration'] - expected) > .5 or (info['hasAudio'] and not verified['hasAudio']):
            raise RuntimeError('Video tạm không đạt kiểm tra thời lượng/âm thanh; giữ nguyên file gốc.')
        current = path.stat()
        if (current.st_size, current.st_mtime_ns) != (stamp.st_size, stamp.st_mtime_ns):
            raise RuntimeError('File gốc đã thay đổi trong lúc cắt; không ghi đè.')
        check_cancelled()
        os.replace(output, path)
        report(1.0)
        return {'mode': mode, 'duration': verified['duration'], 'removed': info['duration'] - expected}
