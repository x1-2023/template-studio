"""Nhập font vào dữ liệu riêng và chuẩn bị đường dẫn ASCII cho libass."""

import hashlib
import shutil
from pathlib import Path

from PIL import ImageFont

MAX_FONT_BYTES = 20 * 1024**2


def inspect_font(source):
    path = Path(source)
    if path.suffix.lower() not in (".ttf", ".otf", ".ttc") or not path.is_file():
        raise ValueError("Chọn file font TTF, OTF hoặc TTC.")
    if not 0 < path.stat().st_size <= MAX_FONT_BYTES:
        raise ValueError("Font rỗng hoặc vượt 20 MiB.")
    try:
        family = ImageFont.truetype(str(path), 32).getname()[0]
    except (OSError, ValueError) as error:
        raise ValueError("Không đọc được font đã chọn.") from error
    if not family or len(family) > 120 or any(c in family for c in ",\r\n{}"):
        raise ValueError("Tên font không dùng được cho phụ đề.")
    return family


def import_font(source, home):
    family = inspect_font(source)
    path = Path(source)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    target = Path(home) / "runtime/fonts" / digest / ("font" + path.suffix.lower())
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        shutil.copy2(path, target)
    return dict(name=family, path=str(target.resolve()))


def stage_font(source, folder, directory="fonts"):
    """Chỉ copy font được chọn, không quét cả thư mục ngoài của người dùng."""
    family = inspect_font(source)
    target = Path(folder) / directory
    target.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target / ("caption" + Path(source).suffix.lower()))
    return family
