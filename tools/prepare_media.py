"""Cài runtime cho bản source hoặc môi trường kiểm thử, có thể dùng ZIP đã tải."""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from template_studio.media_setup import ensure_media  # noqa: E402


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    parser = argparse.ArgumentParser(description='Chuẩn bị FFmpeg đã ghim checksum')
    parser.add_argument('--home', type=Path, default=ROOT / 'data/template-studio')
    parser.add_argument('--archive', type=Path)
    args = parser.parse_args()
    ensure_media(args.home, progress=print, archive=args.archive)
    print('FFmpeg sẵn sàng.')
