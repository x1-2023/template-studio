"""Kiểm tra Windows/GPU: karaoke, đường dẫn Unicode, chia phần và tiếp tục sau hủy."""

import argparse
import hashlib
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from offline_studio.cancellation import TaskCancelled  # noqa: E402
from offline_studio.config import atomic_json  # noqa: E402
from offline_studio.process import binary, probe  # noqa: E402
from template_studio.gpu.resources import bundled_cache  # noqa: E402
from template_studio.parts import render_parts  # noqa: E402
from template_studio.presets import catalog  # noqa: E402
from template_studio.worker_client import run_worker  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home", type=Path)
    args = parser.parse_args()
    home = (args.home or ROOT / ".runtime" / ("qa-karaoke-" + datetime.now().strftime("%Y%m%d-%H%M%S"))).resolve()
    home.mkdir(parents=True, exist_ok=True)
    os.environ["TEMPLATE_STUDIO_HOME"] = str(home)
    folder = home / "Đường dẫn thử O'Brien [1012]"
    folder.mkdir(exist_ok=True)
    source = folder / "video mẫu.mp4"
    subprocess.run([binary("ffmpeg"), "-v", "error", "-y", "-f", "lavfi", "-i",
                    "testsrc2=size=720x1280:rate=30:duration=9", "-f", "lavfi", "-i",
                    "sine=frequency=440:duration=9", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(source)],
                   check=True, creationflags=subprocess.CREATE_NO_WINDOW)
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    words = [dict(text=text, start=i * 1.5 + j * .5 + .1, end=i * 1.5 + j * .5 + .5)
             for i in range(6) for j, text in enumerate(("XIN", "CHÀO", "BẠN"))]
    caption = source.with_suffix(".words.json")
    atomic_json(caption, words)
    config = next(p["config"] for p in catalog() if p["id"] == "karaoke-1012")
    config.update(subtitle_mode="file", subtitle_file=str(caption), subtitle_title="BETA RENDER 1012")

    def request(src, output, settings, preview=False, offset=0):
        return dict(action="render", source=src, output=str(output), config=settings,
                    cache=str(bundled_cache(ROOT)), encoder="h264_nvenc", bitrate=12,
                    seconds=3 if preview else None, preview=preview, offset=offset)

    results = []
    for preview in (True, False):
        output = folder / ("preview/video.mp4" if preview else "single/video.mp4")
        output.parent.mkdir(exist_ok=True)
        result = run_worker(ROOT, home, request(str(source), output, {**config, "part_count": 1}, preview))
        assert result["frames"] == (90 if preview else 270)
        assert list(output.parent.iterdir()) == [output]
        results.append(result)
        print(f"Karaoke {'preview' if preview else '1 video'}: {result['frames']} khung · OK", flush=True)
    exports = folder / "parts"
    exports.mkdir(exist_ok=True)
    completed = []

    def cancel_part_two(event):
        if 35 < event["percent"] < 66:
            raise TaskCancelled("Kiểm tra hủy ở phần 2")

    try:
        render_parts(ROOT, home, "demo", source, config, exports, request, cancel_part_two, lambda parts: completed.extend(parts))
        raise AssertionError("Chưa hủy ở phần 2")
    except TaskCancelled:
        pass
    assert len(completed) == 1 and len(list(exports.glob("*.mp4"))) == 1
    first = Path(completed[0])
    stamp = (first.stat().st_size, first.stat().st_mtime_ns)
    result = render_parts(ROOT, home, "demo", source, config, exports, request, lambda event: None, lambda parts: None)
    assert result["parts"][0] == str(first)
    assert stamp == (first.stat().st_size, first.stat().st_mtime_ns)
    assert len(list(exports.iterdir())) == 3
    for path in result["parts"]:
        info = probe(path)
        video = next(s for s in info["streams"] if s["codec_type"] == "video")
        assert (video["width"], video["height"], video["nb_frames"]) == (1080, 1440, "90")
        assert any(s["codec_type"] == "audio" for s in info["streams"])
    assert digest == hashlib.sha256(source.read_bytes()).hexdigest()
    for i, path in enumerate([results[0]["output"], results[1]["output"], *result["parts"]]):
        subprocess.run([binary("ffmpeg"), "-v", "error", "-y", "-ss", "0.3", "-i", path,
                        "-frames:v", "1", str(home / f"frame-{i}.png")], check=True, creationflags=subprocess.CREATE_NO_WINDOW)
    atomic_json(home / "verified.json", dict(single=results, multipart=result, source_sha256=digest, resumed=True))
    print(f"Chia 3 phần, hủy phần 2 và chạy tiếp: OK. Ảnh và báo cáo: {home}", flush=True)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
