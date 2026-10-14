"""Một công thức FFmpeg dùng chung preview và bản xuất; không sửa file nguồn."""
import math
import random
import shutil
import time
import uuid
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter
from offline_studio.process import binary, probe, run
from offline_studio.cancellation import check_cancelled
from .effects import catalog, stream_effect


DEFAULTS = dict(scale=85, blur=22, intro=3.0, strength=55, speed=1.0,
                resolution=1080, codec='h264', mute=False,
                effect='none', effectIntensity=65, effectDuration=0)


def normalize(value):
    result = {**DEFAULTS, **value}
    for key, low, high in [('scale', 30, 100), ('blur', 0, 60), ('intro', 0, 600),
                           ('strength', 0, 100), ('speed', .5, 3),
                           ('effectIntensity', 0, 100), ('effectDuration', 0, 600)]:
        number = float(result[key])
        if not math.isfinite(number):
            raise ValueError('Thông số phải là số hữu hạn.')
        result[key] = max(low, min(high, number))
    result['resolution'] = 720 if int(result['resolution']) == 720 else 1080
    result['codec'] = 'hevc' if result['codec'] == 'hevc' else 'h264'
    result['mute'] = bool(result['mute'])
    if result['effect'] not in {entry['id'] for entry in catalog()}:
        raise ValueError('Filter không thuộc thư viện đã tích hợp.')
    return result


def metadata(source):
    data = probe(source)
    video = next((s for s in data['streams'] if s['codec_type'] == 'video'), None)
    if not video:
        raise ValueError('File không có hình ảnh video.')
    duration = float(data['format'].get('duration', video.get('duration', 0)))
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError('Không đọc được thời lượng video.')
    return dict(duration=duration, width=video['width'], height=video['height'],
                audio=any(s['codec_type'] == 'audio' for s in data['streams']))


def texture(path, width, height, strength):
    randomizer = random.Random(2026)
    image = Image.new('RGBA', (width, height))
    draw = ImageDraw.Draw(image)
    colors = [(255, 130, 219), (157, 237, 255), (255, 241, 157), (174, 177, 255)]
    for index in range(32):
        x, y = randomizer.randrange(width), randomizer.randrange(height)
        radius = randomizer.randint(max(12, width // 30), width // 7)
        points = [(x + radius * math.cos(j * math.pi / 3),
                   y + radius * math.sin(j * math.pi / 3)) for j in range(7)]
        color = colors[index % len(colors)]
        draw.polygon(points, fill=(*color, int(strength * .28)))
        draw.line(points, fill=(*color, int(strength * 1.5)), width=max(2, width // 180))
    image.filter(ImageFilter.GaussianBlur(width / 450)).save(path)


def graph(settings, width, height, intro, has_audio, offset=0):
    s = settings
    fw = int(width * s['scale'] / 100) // 2 * 2
    fh = int(height * s['scale'] / 100) // 2 * 2
    filters = [f'[0:v]setpts=(PTS-STARTPTS)/{s["speed"]},fps=30,split=2[bg0][fg0]',
               f'[bg0]scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},setsar=1,gblur=sigma={s["blur"]}[bg]',
               f'[fg0]scale={fw}:{fh}:force_original_aspect_ratio=decrease:force_divisible_by=2,setsar=1[fg]',
               '[bg][fg]overlay=(W-w)/2:(H-h)/2:shortest=1[base]']
    if intro > 0 and s['strength'] > 0:
        fade = min(.7, intro)
        filters += [f'[base]gblur=sigma={s["strength"] / 18:.3f}:enable=\'lt(t,{intro})\'[soft]',
                    f'[1:v]format=rgba,fade=t=out:st={max(0, intro-fade):.4f}:d={fade:.4f}:alpha=1[glass]',
                    '[soft][glass]overlay=0:0:eof_action=pass:repeatlast=0[v]']
    else:
        filters += ['[base]null[v]']
    if has_audio and not s['mute']:
        speed = s['speed']
        tempos = []
        while speed > 2:
            tempos.append('atempo=2')
            speed /= 2
        tempos.append(f'atempo={speed}')
        filters += ['[0:a]asetpts=PTS-STARTPTS,' + ','.join(tempos) + '[a]']
    return ';'.join(filters)


def render(source, destination, settings, nvenc=False, progress=lambda p: None,
           preview=False, offset=0):
    source, destination = Path(source).resolve(), Path(destination).resolve()
    if source == destination:
        raise ValueError('Không được ghi đè video nguồn.')
    s = normalize(settings)
    meta = metadata(source)
    stamp = (source.stat().st_size, source.stat().st_mtime_ns)
    duration = meta['duration'] / s['speed']
    offset = max(0, min(float(offset), max(0, duration - .1)))
    duration -= offset
    if preview:
        duration = min(8, duration)
    width = 360 if preview else s['resolution']
    height = width * 16 // 9
    intro = max(0, min(s['intro'] - offset, duration))
    destination.parent.mkdir(parents=True, exist_ok=True)
    if shutil.disk_usage(destination.parent).free < max(256 * 1024**2, duration * 1_000_000):
        raise OSError('Không đủ dung lượng trống cho video đầu ra.')
    token = uuid.uuid4().hex
    partial = destination.with_name(destination.stem + '.' + token + '.part.mp4')
    pattern = destination.with_name('.glass-' + token + '.png')
    began = time.monotonic()
    try:
        args = [binary('ffmpeg'), '-hide_banner', '-nostdin', '-y', '-filter_complex_threads', '4']
        if offset:
            args += ['-ss', str(offset * s['speed'])]
        args += ['-i', str(source)]
        if intro > 0 and s['strength'] > 0:
            texture(pattern, width, height, s['strength'])
            args += ['-loop', '1', '-framerate', '30', '-t', str(intro), '-i', str(pattern)]
        use_effect = s['effect'] != 'none' and s['effectIntensity'] > 0
        input_args = list(args)
        if use_effect:
            input_args += ['-filter_complex', graph(s, width, height, intro, False), '-map', '[v]',
                           '-an', '-t', str(duration), '-pix_fmt', 'rgba', '-f', 'rawvideo', 'pipe:1']
            args = [binary('ffmpeg'), '-v', 'error', '-nostdin', '-y', '-f', 'rawvideo',
                    '-pixel_format', 'rgba', '-video_size', f'{width}x{height}', '-framerate', '30', '-i', 'pipe:0']
            if meta['audio'] and not s['mute']:
                args += ['-ss', str(offset * s['speed']), '-i', str(source), '-map', '0:v:0', '-map', '1:a:0']
                tempos, speed = [], s['speed']
                while speed > 2:
                    tempos.append('atempo=2')
                    speed /= 2
                tempos.append(f'atempo={speed}')
                args += ['-af', 'asetpts=PTS-STARTPTS,' + ','.join(tempos), '-c:a', 'aac', '-b:a', '128k']
            else:
                args += ['-map', '0:v:0', '-an']
        else:
            args += ['-filter_complex', graph(s, width, height, intro, meta['audio']), '-map', '[v]']
            if meta['audio'] and not s['mute']:
                args += ['-map', '[a]', '-c:a', 'aac', '-b:a', '128k']
        if nvenc:
            args += ['-c:v', 'hevc_nvenc' if s['codec'] == 'hevc' else 'h264_nvenc',
                     '-preset', 'p1', '-rc', 'vbr', '-cq', '27', '-b:v', '0']
        else:
            args += ['-c:v', 'libx265' if s['codec'] == 'hevc' else 'libx264',
                     '-preset', 'veryfast', '-crf', '26', '-threads', '0']
        if s['codec'] == 'hevc':
            args += ['-tag:v', 'hvc1']
        args += ['-pix_fmt', 'yuv420p', '-t', str(duration), '-movflags', '+faststart']
        if not use_effect:
            args += ['-progress', 'pipe:1', '-nostats']
        args += [str(partial)]
        if use_effect:
            # Decoder xử lý template trước filter; âm thanh lấy từ nguồn, không qua OpenCV.
            stream_effect(input_args, args, width, height, duration, s, progress, offset, meta['duration'] / s['speed'])
        else:
            run(args, timeout=max(600, duration * 100), progress=progress, duration=duration)
        check_cancelled()
        output = metadata(partial)
        if abs(output['duration'] - duration) > max(.3, duration * .005) or (output['width'], output['height']) != (width, height):
            raise ValueError('Video đầu ra không đúng thời lượng/kích thước; chưa xuất bản.')
        if output['audio'] != (meta['audio'] and not s['mute']):
            raise ValueError('Âm thanh đầu ra không đúng cấu hình.')
        if stamp != (source.stat().st_size, source.stat().st_mtime_ns):
            raise ValueError('Nguồn đã thay đổi khi render.')
        if destination.exists():
            raise FileExistsError('Tên đầu ra đã tồn tại; không ghi đè.')
        partial.rename(destination)
        return dict(path=str(destination), elapsed=time.monotonic()-began, duration=duration)
    finally:
        partial.unlink(missing_ok=True)
        pattern.unlink(missing_ok=True)
