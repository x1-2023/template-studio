"""Chia ba phần theo ranh giới khung hình, ghi sổ để tiếp tục sau khi lỗi/dừng."""

import hashlib
import json
import math
import time
import uuid
from pathlib import Path

from offline_studio.cancellation import check_cancelled
from offline_studio.config import atomic_json
from offline_studio.process import probe

from .presets import safe_name
from .worker_client import run_worker
from .version import VERSION


def plan_parts(duration, config):
    duration = (duration - config["source_offset"]) / config["playback_rate"]
    fps, count = config["fps"], config["part_count"]
    frames = math.ceil(duration * fps - 1e-6)
    if frames < count:
        raise ValueError("Video quá ngắn để chia thành các phần đã chọn.")
    return [dict(
        start=(frames * i // count) / fps,
        seconds=min(duration, (frames * (i + 1) // count) / fps) - (frames * i // count) / fps,
    ) for i in range(count)]


def _valid_part(item, config, audio):
    path = Path(item["output"])
    if not path.is_file():
        return False
    try:
        info = probe(path)
        video = next(s for s in info["streams"] if s["codec_type"] == "video")
        a, b = map(float, video.get("r_frame_rate", "0/1").split("/"))
        return (
            video["codec_name"] == "h264" and (video["width"], video["height"]) == (config["width"], config["height"])
            and b > 0 and abs(a / b - config["fps"]) < .001
            and abs(float(video.get("duration", info["format"]["duration"])) - item["seconds"]) < .15
            and any(s["codec_type"] == "audio" for s in info["streams"]) == audio
        )
    except (OSError, ValueError, KeyError, StopIteration, RuntimeError, ZeroDivisionError):
        return False


def render_parts(root, home, row_id, source, config, output, request, progress, completed):
    source, output = Path(source).resolve(), Path(output).resolve()
    stamp = [source.stat().st_size, source.stat().st_mtime_ns]
    caption = Path(config["subtitle_file"]) if config.get("subtitle_mode") == "file" else None
    caption_stamp = [caption.stat().st_size, caption.stat().st_mtime_ns] if caption else None
    identity = dict(version=VERSION, row=row_id, source=str(source), stamp=stamp, config=config, caption_stamp=caption_stamp, output=str(output))
    key = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    journal = Path(home) / "cache/parts" / (key + ".json")
    metadata = probe(source)
    video = next(s for s in metadata["streams"] if s["codec_type"] == "video")
    intervals = plan_parts(float(video.get("duration", metadata["format"]["duration"])), config)
    audio = not config["mute"] and any(s["codec_type"] == "audio" for s in metadata["streams"])
    try:
        manifest = json.loads(journal.read_text(encoding="utf-8"))
        if manifest["identity"] != identity or len(manifest["parts"]) != len(intervals):
            raise ValueError("Sổ chia phần không còn phù hợp.")
        for item in manifest["parts"]:
            if Path(item["output"]).resolve().parent != output:
                raise ValueError("Đường dẫn phần xuất không hợp lệ.")
    except (OSError, ValueError, KeyError, TypeError):
        prefix = safe_name(source.stem)[:60] + "_" + uuid.uuid4().hex[:8]
        manifest = dict(identity=identity, parts=[dict(
            **interval, output=str(output / f"{prefix}_part{i+1}.mp4"), status="pending",
        ) for i, interval in enumerate(intervals)])
        atomic_json(journal, manifest)
    began, outputs = time.monotonic(), []
    for i, item in enumerate(manifest["parts"]):
        check_cancelled()
        if stamp != [source.stat().st_size, source.stat().st_mtime_ns]:
            raise ValueError("Video nguồn thay đổi trong khi xuất các phần.")
        target = Path(item["output"])
        if not _valid_part(item, config, audio):
            # Giữ file chưa hợp lệ để đối chiếu; tên mới tránh ghi đè file đang có.
            if target.exists():
                target = target.with_name(target.stem + "_" + uuid.uuid4().hex[:6] + ".mp4")
                item["output"] = str(target)
            item["status"] = "rendering"
            atomic_json(journal, manifest)
            part_config = {**config, "subtitle_part_label": f"PART {i+1}"}
            job = request(str(source), target, part_config, offset=item["start"])
            job["seconds"] = item["seconds"]
            run_worker(root, home, job, lambda event, index=i: progress({
                **event, "percent": (index + event["percent"] / 100) / len(intervals) * 100,
            }))
            if not _valid_part(item, config, audio):
                raise ValueError(f"Phần {i+1} chưa đạt kiểm tra thời lượng/âm thanh.")
        item["status"] = "done"
        atomic_json(journal, manifest)
        outputs.append(str(target))
        completed(outputs.copy())
        progress(dict(percent=(i + 1) / len(intervals) * 100))
    return dict(output=outputs[0], parts=outputs, wall_seconds=time.monotonic() - began)
