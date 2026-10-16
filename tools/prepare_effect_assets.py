"""Lấy đúng shader/LUT renderer sử dụng; không đóng scene, Lua, model hay video."""

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from template_studio.assets_local import validate  # noqa: E402
from template_studio.gpu.resources import resources, shader_map  # noqa: E402


def prepare(cache, destination):
    cache, destination = Path(cache).resolve(), Path(destination).resolve()
    validate(cache)
    effect, tone = resources(cache)
    selected = set()
    mapping = shader_map(effect)
    keys = {
        "LumiBokehBlur/gaussBlur0",
        "LumiBokehBlur/gaussBlur1",
        "LumiBokehBlur/polygon",
        "LumiBokehBlur/in2out",
        "LumiLayer/layer",
        "LumiRadialBlur/radialBlurZoom",
        "LumiOpticsCompensation/opticsCompensation",
        "LumiOpticsCompensation/antiAliasing",
    }
    for path in effect.rglob("*.xshader"):
        key = f"{path.parent.parent.name}/{path.stem}"
        if key in keys:
            selected.add((path, Path("effect") / path.relative_to(effect)))
            shader = mapping[key]
            selected.add((shader, Path("effect") / shader.relative_to(effect)))
    for name in ("darkFilter.png", "noise.png"):
        path = effect / "effects/LumiBokehBlur/image" / name
        selected.add((path, Path("effect") / path.relative_to(effect)))
    for relative in (
        "xshader/pass0.frag",
        "xshader/filter.frag",
        "image/filter_bg.png",
        "image/filter_skin.png",
    ):
        selected.add((tone / relative, Path("tone") / relative))
    if len(selected) != 22:
        raise ValueError("Danh sách tài nguyên không đủ 22 file đã xác định.")
    destination.mkdir(parents=True, exist_ok=False)
    files = {}
    for source, relative in sorted(selected, key=lambda item: item[1].as_posix()):
        if source.is_symlink() or not source.resolve().is_relative_to(cache):
            raise ValueError("Tài nguyên nằm ngoài cache đã chọn.")
        output = destination / relative
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, output)
        files[relative.as_posix()] = hashlib.sha256(output.read_bytes()).hexdigest()
    (destination / "runtime-manifest.json").write_text(
        json.dumps(
            dict(
                schema=1,
                layout="bundled-v1",
                resource_ids=["7491138615477685505", "7514206177195068689"],
                files=files,
            ),
            indent=2,
        ),
        encoding="utf-8",
    )
    validate(destination)
    print(f"Đã chuẩn bị {len(files)} tài nguyên tại {destination}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument(
        "--output", type=Path, default=ROOT / "template_studio/assets/effects"
    )
    args = parser.parse_args()
    prepare(args.cache, args.output)
