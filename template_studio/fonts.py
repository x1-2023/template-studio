"""Font có sẵn, font riêng và đường dẫn ASCII cho libass."""

import hashlib
import shutil
from pathlib import Path

from PIL import ImageFont

MAX_FONT_BYTES = 20 * 1024**2
TREND_FILE = Path(__file__).with_name("assets") / "fonts/ZYTrend.ttf"
TREND_SHA256 = "e6b721d49a34786e34a4d198a1734b73f2ffff3b8b23461efc827e7dedc1b3db"


def bundled_font():
    """Đọc tài nguyên cạnh module, dùng được cả source và EXE đã giải nén."""
    if not TREND_FILE.is_file() or hashlib.sha256(TREND_FILE.read_bytes()).hexdigest() != TREND_SHA256:
        raise ValueError("Font ZY Trend trong app bị thiếu hoặc hỏng. Hãy cài lại bản cập nhật.")
    return TREND_FILE


def resolve_font(config):
    if config.get("subtitle_font_file"):
        return Path(config["subtitle_font_file"])
    if config.get("subtitle_font_builtin") == "zy-trend":
        return bundled_font()
    return None


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
