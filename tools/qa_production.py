"""Kiểm thử GPU local qua Controller thật: batch, snapshot, preview và hủy process."""

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
HOME = ROOT / ".runtime/qa-production-integration"
os.environ["TEMPLATE_STUDIO_HOME"] = str(HOME)
os.environ["PYTHONUTF8"] = "1"
from PySide6.QtWidgets import QApplication  # noqa: E402

from offline_studio.process import binary, probe  # noqa: E402
from template_studio.app import Controller  # noqa: E402
from template_studio.assets_local import import_cache  # noqa: E402


def main():
    HOME.mkdir(parents=True, exist_ok=True)
    app = QApplication.instance() or QApplication([])

    def wait(controller, limit=180):
        deadline = time.monotonic() + limit
        while controller.pool.active and time.monotonic() < deadline:
            app.processEvents()
            time.sleep(0.02)
        if controller.pool.active:
            raise TimeoutError("QA vượt thời gian chờ")
        app.processEvents()

    source = HOME / "sources"
    source.mkdir(exist_ok=True)
    subprocess.run(
        [
            binary("ffmpeg"),
            "-v",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc2=size=160x240:rate=30:duration=0.3",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=600:duration=0.3",
            "-c:v",
            "libx264",
            "-c:a",
            "aac",
            "-shortest",
            str(source / "seed.mp4"),
        ],
        check=True,
    )
    paths = []
    for index in range(20):
        folder = source / str(index)
        folder.mkdir(exist_ok=True)
        path = folder / ("nguồn trùng tên.mp4" if index % 2 else "clip.mp4")
        if index in (6, 15):
            path.write_bytes(b"bad-video")
        else:
            shutil.copy2(source / "seed.mp4", path)
        paths.append(str(path))
    for state in (HOME / "production.json", HOME / "session.json"):
        state.unlink(missing_ok=True)
    import_cache(ROOT / "CapCut_FFmpeg_Codex_Handoff/work/cache", HOME)
    controller = Controller(ROOT, HOME)
    wait(controller)
    p = controller.production
    p.checkRuntime()
    wait(controller)
    assert p.ready, p.runtimeNotice
    p.configure("resolution", 720)
    p._output = str(HOME / "exports")
    p.add_paths(paths)
    wait(controller)
    assert len(p.rows) == 20
    assert sum(r["status"] == "Lỗi" for r in p.rows) == 2
    p.runBatch()
    wait(controller)
    assert sum(r["status"] == "Hoàn tất" for r in p.rows) == 18, [
        r["detail"] for r in p.rows if r["status"] != "Hoàn tất"
    ]
    assert sum(r["status"] == "Lỗi" for r in p.rows) == 2
    destinations = [r["result"] for r in p.rows if r["result"]]
    assert len(set(destinations)) == 18
    for dest in destinations:
        info = probe(dest)
        v = next(s for s in info["streams"] if s["codec_type"] == "video")
        assert (v["width"], v["height"], int(v["nb_frames"])) == (720, 960, 9)
        assert v["sample_aspect_ratio"] == "1:1"
        assert any(s["codec_type"] == "audio" for s in info["streams"])
    saved = [r["config"].copy() for r in p.rows if r["status"] == "Hoàn tất"]
    p.choosePreset("pentagon-9x16")
    assert [r["config"] for r in p.rows if r["status"] == "Hoàn tất"] == saved
    recovered = Controller(ROOT, HOME)
    wait(recovered)
    assert sum(r["status"] == "Hoàn tất" for r in recovered.production.rows) == 18
    # Preview thật ở offset sau intro, cấu hình mute và frame đầu phải khớp worker chung.
    p.choosePreset("reference")
    p.select(0)
    p.preview(0)
    wait(controller)
    assert p.previewUrl and not p.previewStale, controller.notice
    # Hủy giữa quá trình render clip dài; không để partial hoặc process con sót.
    longer = source / "longer.mp4"
    subprocess.run(
        [
            binary("ffmpeg"),
            "-v",
            "error",
            "-y",
            "-stream_loop",
            "100",
            "-i",
            str(source / "seed.mp4"),
            "-t",
            "20",
            "-c",
            "copy",
            str(longer),
        ],
        check=True,
    )
    p.add_paths([str(longer)])
    wait(controller)
    p._selected = {p._rows[-1]["id"]}
    p.runBatch()
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.03)
        if p._rows[-1]["percent"] > 0:
            break
    controller.stop()
    wait(controller)
    assert p._rows[-1]["status"] == "Đã dừng", p._rows[-1]
    assert not list((HOME / "exports").glob("*.partial.mp4"))
    report = dict(
        ok=True,
        batch=20,
        completed=18,
        invalid=2,
        unique_names=True,
        restored=True,
        snapshots=True,
        preview=True,
        cancel=True,
        no_partial=True,
    )
    (HOME / "qa-result.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report))


if __name__ == "__main__":
    main()
