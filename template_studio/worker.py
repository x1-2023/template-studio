"""Worker không GUI, dùng cùng EXE để render và kiểm tra GPU."""

import argparse
import json
import sys
import traceback
from pathlib import Path
from types import SimpleNamespace

from offline_studio.config import atomic_json


class ProgressWriter:
    """Tiến độ chỉ để hiển thị; lỗi ghi tạm thời không được hủy video."""

    def __init__(self, folder):
        self.path = Path(folder) / "progress.json"
        self.warned = False

    def __call__(self, event):
        try:
            atomic_json(self.path, event)
            self.warned = False
        except OSError as error:
            if not self.warned:
                print(f"Chưa ghi được tiến độ; render vẫn tiếp tục: {error}", flush=True)
                self.warned = True


def execute(request, emit, diagnostics=None):
    if request["action"] == "transcribe":
        import os
        from .paths import data_home
        from .speech import transcribe
        app_root = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parents[1]
        home = data_home(app_root)
        os.environ["TEMPLATE_STUDIO_HOME"] = str(home)
        return transcribe(request["source"], home, diagnostics, emit)
    if request["action"] == "health":
        import glcontext  # noqa: F401
        import moderngl

        from .gpu.renderer import Renderer  # noqa: F401

        if request.get("structural"):
            return dict(ok=True, structural=True)
        context = moderngl.create_standalone_context(require=330)
        try:
            return dict(ok=True, gpu=context.info["GL_RENDERER"])
        finally:
            context.release()
    from .gpu.pipeline import render
    from .presets import normalize

    config = normalize(request["config"])
    if request.get("preview"):
        ratio = config["height"] / config["width"]
        config.update(width=540, height=round(540 * ratio / 2) * 2)
    args = SimpleNamespace(
        seconds=request.get("seconds"),
        overwrite=False,
        encoder=request["encoder"],
        video_bitrate=request.get("bitrate"),
        skin=config["skin"],
        skin_mask=None,
        proxy=bool(request.get("preview")),
        cache=Path(request["cache"]),
        no_effect=not config["intro_enabled"],
        no_filter=not config["filter_enabled"],
        mute=config["mute"],
        timeline_offset=request.get("offset", 0),
        effect_offset=request.get("effect_offset", 0),
        diagnostics=diagnostics,
    )
    args.temporary = request.get("temporary")
    return render(request["source"], request["output"], config, args, progress=emit)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", type=Path, required=True)
    args = parser.parse_args()
    folder = args.request.resolve().parent
    with (folder / "worker.log").open("w", encoding="utf-8", buffering=1) as log:
        sys.stdout = sys.stderr = log
        try:
            request = json.loads(args.request.read_text(encoding="utf-8-sig"))
            result = execute(
                request, ProgressWriter(folder), diagnostics=folder
            )
            atomic_json(folder / "result.json", dict(ok=True, result=result))
            return 0
        except Exception as error:
            traceback.print_exc()
            atomic_json(folder / "result.json", dict(ok=False, error=str(error)))
            return 1


if __name__ == "__main__":
    raise SystemExit(main())
