"""Lưu báo cáo riêng và cất file kỹ thuật của bản cũ, giữ nguyên video."""

import json
import re
import shutil
import uuid
from pathlib import Path


def _record(path):
    try:
        if path.is_symlink() or path.stat().st_size > 4 * 1024**2:
            return {}
        value = json.loads(path.read_text(encoding="utf-8-sig"))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def _video_path(value):
    if not isinstance(value, str):
        return None
    try:
        return Path(value).resolve()
    except (OSError, ValueError):
        return None


def archive_output_artifacts(output, home):
    """Chỉ nhận diện file do app tạo; file đang khóa được giữ để thử lần sau."""
    output, home = Path(output).resolve(), Path(home).resolve()
    candidates = set()
    for path in output.glob("*.render.json"):
        record = _record(path)
        if not {"output", "gpu", "frames", "ffmpeg_encode"} <= record.keys():
            continue
        video = path.with_name(path.name.removesuffix(".render.json") + ".mp4")
        if _video_path(record["output"]) != video:
            continue
        candidates.update(video.with_suffix(s) for s in (".render.json", ".decode.log", ".encode.log"))
    # Job thất bại có thể chỉ có log, chưa có bản thống kê render.json.
    for path in (home / "cache/workers").glob("*/request.json"):
        record = _record(path)
        if record.get("action") != "render":
            continue
        video = _video_path(record.get("output"))
        if video and video.parent == output and video.suffix.lower() == ".mp4":
            candidates.update(video.with_suffix(s) for s in (".decode.log", ".encode.log"))
    for path in output.glob("bao-cao-*.json"):
        if not re.fullmatch(r"bao-cao-\d{8}-\d{6}-[0-9a-f]{6}\.json", path.name):
            continue
        record = _record(path)
        if isinstance(record.get("version"), str) and isinstance(record.get("results"), list):
            candidates.update((path, path.with_suffix(".csv")))
    archive = home / "cache/workers/archived-exports" / uuid.uuid4().hex
    moved = 0
    for path in sorted(candidates):
        try:
            if path.is_symlink() or not path.is_file() or path.resolve().parent != output:
                continue
            archive.mkdir(parents=True, exist_ok=True)
            shutil.move(str(path), str(archive / path.name))
            moved += 1
        except OSError:
            continue
    return moved


def reports_directory(home):
    folder = Path(home) / "cache/workers/batches"
    folder.mkdir(parents=True, exist_ok=True)
    return folder
