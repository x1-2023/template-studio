"""Cấu hình và dữ liệu riêng của bản offline."""
import copy
import json
import os
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parents[1]))
ASSETS = ROOT / 'offline_studio' / 'assets'
APP_ROOT = Path(os.environ['STUDIO_HOME']).resolve() if os.environ.get('STUDIO_HOME') else (Path(sys.executable).resolve().parent if getattr(sys, 'frozen', False) else ROOT)
DATA = Path(os.environ.get('STUDIO_OFFLINE_DATA_DIR', str(APP_ROOT / 'data'))).resolve()
LANGUAGES = ['Tự động nhận diện', 'Tiếng Việt', 'Tiếng Anh', 'Tiếng Trung', 'Tiếng Nhật', 'Tiếng Hàn', 'Tiếng Pháp', 'Tiếng Tây Ban Nha', 'Tiếng Đức', 'Tiếng Nga', 'Tiếng Thái', 'Tiếng Indonesia']
LANG_CODES = dict(zip(LANGUAGES, ['auto', 'vi', 'en', 'zh', 'ja', 'ko', 'fr', 'es', 'de', 'ru', 'th', 'id']))
STYLES = ['TikTok Viral (Vàng viền đen)', 'Cổ điển (Trắng viền đen)', 'Nổi bật (Đỏ viền trắng)', 'Cyber Neon (Xanh dạ quang)', 'Hộp tin tức (Nền đen chữ trắng)', 'Vàng hoàng kim (Gold Luxury)']
CAPTION_ANIMATIONS = ['Không có', 'Fade', 'Pop', 'Bounce', 'Zoom', 'Slide']
BLEND_MODES = ['Normal', 'Screen', 'Add']
VIDEO_CODECS = {'h264': 'H.264 · Dễ tương thích', 'hevc': 'H.265 / HEVC · File nhẹ hơn'}
OUTPUT_PROFILES = {'balanced': 'Cân bằng dung lượng', 'fast': 'Ưu tiên tốc độ', 'quality': 'Ưu tiên chất lượng · File lớn'}
DEFAULT_RECIPE = {
    'splitEvery': 0, 'video': {'speed': 1.0, 'scale': 100, 'volume_db': 0},
    'effect': {'name': 'Không có', 'speed': 13, 'air': 35},
    'audio': {'voice_sharpen': False, 'vocal_sep': False, 'vocal_mode': 'Tách tự động local', 'vocal_dir': '', 'bgm_path': '', 'bgm_db': 0},
    'overlay': {'path': '', 'chroma_enabled': True, 'chroma_intensity': 70, 'blend': 'Normal', 'opacity': 100},
    'color': {'temperature': 0, 'tone': 0, 'saturation': 0, 'contrast': 0, 'shadow': 0},
    'captions': {'enabled': False, 'language': LANGUAGES[0], 'style': STYLES[0], 'srt_path': '', 'backend': 'GPU chất lượng cao', 'karaoke': True, 'size': 100, 'position': 'Dưới', 'animation': 'Không có'},
    'output': {'mode': 'offline', 'resolution': '1080p', 'fps': 30, 'encoder': 'auto', 'codec': 'h264', 'profile': 'balanced'},
    'autoChunk': True, 'compressCrf': False, 'autoRetry': True,
}


def normalize_recipe(value, effects=()):
    result = copy.deepcopy(DEFAULT_RECIPE)
    for key, item in value.items():
        if key not in result:
            continue
        if isinstance(result[key], dict) and isinstance(item, dict):
            result[key].update(item)
        else:
            result[key] = item
    audio = value.get('audio', {})
    if value.get('output') and 'profile' not in value['output']:
        result['output']['profile'] = 'quality'
    if 'vocal_mode' not in audio and audio.get('vocal_dir'):
        result['audio']['vocal_mode'] = 'Dùng file đã tách'
    return result


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = None
    try:
        # Mỗi lần ghi có file riêng; GUI/worker không dùng chung một progress.tmp.
        with tempfile.NamedTemporaryFile(
            mode='w', encoding='utf-8', dir=path.parent,
            prefix=f'.{path.name}.', suffix='.tmp', delete=False,
        ) as stream:
            pending = Path(stream.name)
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        for attempt in range(6):
            try:
                os.replace(pending, path)
                break
            except PermissionError:
                # Windows có thể giữ handle lúc GUI/antivirus đang đọc file đích.
                if attempt == 5:
                    raise
                time.sleep(0.01 * (2 ** attempt))
    finally:
        if pending is not None:
            try:
                pending.unlink(missing_ok=True)
            except OSError:
                pass


def effects():
    return json.loads((ROOT / 'offline_studio/effects.json').read_text(encoding='utf-8'))


def presets():
    path = DATA / 'presets.json'
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else {'Trung tính': copy.deepcopy(DEFAULT_RECIPE)}
