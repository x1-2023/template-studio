"""Kiểm tra tài nguyên đóng kèm và nhập cache tùy chọn."""

import hashlib
import json
import os
import shutil
import subprocess
import uuid
from pathlib import Path, PurePosixPath, PureWindowsPath

from offline_studio.cancellation import check_cancelled, managed_process
from offline_studio.process import NO_WINDOW

from .gpu.resources import bundled_cache, resources, shader_map

RAR_SHA256 = "0ab5b75f72ada6132f7e6dd3812b950934e1608bb724dc98e764978c0503cf47"
IDS = ("7491138615477685505", "7514206177195068689")


def validate(cache):
    cache = Path(cache)
    manifest = cache / "runtime-manifest.json"
    if manifest.is_file():
        if manifest.stat().st_size > 64 * 1024:
            raise ValueError("Manifest gói hiệu ứng quá lớn.")
        data = json.loads(manifest.read_text(encoding="utf-8"))
        if (
            not isinstance(data, dict)
            or data.get("schema") != 1
            or data.get("layout") != "bundled-v1"
            or not isinstance(data.get("files"), dict)
            or len(data["files"]) != 22
        ):
            raise ValueError("Manifest gói hiệu ứng không hợp lệ.")
        for name, expected in data["files"].items():
            if (
                not isinstance(name, str)
                or not isinstance(expected, str)
                or len(expected) != 64
            ):
                raise ValueError("Checksum tài nguyên không hợp lệ.")
            relative = PurePosixPath(name)
            path = cache / relative
            if (
                not relative.parts
                or relative.parts[0] not in {"effect", "tone"}
                or relative.is_absolute()
                or ".." in relative.parts
                or name != relative.as_posix()
                or "\\" in name
                or ":" in name
                or not path.resolve().is_relative_to(cache.resolve())
            ):
                raise ValueError("Đường dẫn tài nguyên hiệu ứng không hợp lệ.")
            if (
                not path.is_file()
                or path.stat().st_size > 8 * 1024**2
                or hashlib.sha256(path.read_bytes()).hexdigest() != expected
            ):
                raise ValueError("Gói hiệu ứng thiếu hoặc hỏng: " + name)
    effect, tone = resources(cache)
    shaders = shader_map(effect)
    required = [
        "LumiBokehBlur/" + v for v in ("gaussBlur0", "gaussBlur1", "polygon", "in2out")
    ] + [
        "LumiLayer/layer",
        "LumiRadialBlur/radialBlurZoom",
        "LumiOpticsCompensation/opticsCompensation",
        "LumiOpticsCompensation/antiAliasing",
    ]
    if any(key not in shaders or not shaders[key].is_file() for key in required):
        raise ValueError("Cache thiếu shader cần dùng.")
    for path in [
        tone / "xshader/pass0.frag",
        tone / "xshader/filter.frag",
        tone / "image/filter_bg.png",
        tone / "image/filter_skin.png",
        effect / "effects/LumiBokehBlur/image/darkFilter.png",
        effect / "effects/LumiBokehBlur/image/noise.png",
    ]:
        if not path.is_file():
            raise ValueError("Cache thiếu LUT hoặc texture: " + path.name)
    return True


def discover(root, home):
    candidates = [
        home / "runtime/capcut-cache",
        bundled_cache(root),
        root / "CapCut_FFmpeg_Codex_Handoff/work/cache",
    ]
    if os.environ.get("TEMPLATE_STUDIO_CAPCUT_CACHE"):
        candidates.insert(0, Path(os.environ["TEMPLATE_STUDIO_CAPCUT_CACHE"]))
    for path in candidates:
        try:
            validate(path)
            return path
        except (OSError, ValueError, StopIteration):
            pass
    return None


def import_cache(source, home):
    source, base = Path(source).resolve(), (Path(home) / "runtime").resolve()
    base.mkdir(parents=True, exist_ok=True)
    target = base / "capcut-cache"
    if source == target:
        validate(source)
        return target
    stage = base / (".asset-" + uuid.uuid4().hex)
    stage.mkdir()
    try:
        if source.is_file():
            if (
                source.stat().st_size > 16 * 1024**2
                or hashlib.sha256(source.read_bytes()).hexdigest() != RAR_SHA256
            ):
                raise ValueError(
                    "RAR không khớp gói cache đã kiểm định; có thể chọn thư mục cache đã giải nén."
                )
            tar = shutil.which("tar")
            if not tar:
                raise ValueError(
                    "Chưa có tar.exe; giải nén RAR rồi chọn thư mục cache."
                )
            with managed_process(
                [tar, "-tf", str(source)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=NO_WINDOW,
            ) as p:
                out, err = p.communicate(timeout=30)
                if p.returncode:
                    raise ValueError(err.decode(errors="replace"))
            for entry in out.decode("utf-8").splitlines():
                name = entry.replace("\\", "/")
                parts = PurePosixPath(name)
                if (
                    parts.is_absolute()
                    or ".." in parts.parts
                    or PureWindowsPath(name).drive
                ):
                    raise ValueError("Đường dẫn RAR không an toàn.")
            with managed_process(
                [tar, "-xf", str(source), "-C", str(stage)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                creationflags=NO_WINDOW,
            ) as p:
                _, err = p.communicate(timeout=30)
                if p.returncode:
                    raise ValueError(err.decode(errors="replace"))
        else:
            validate(source)
            total = 0
            for resource_id in IDS:
                for item in (source / resource_id).rglob("*"):
                    check_cancelled()
                    if (
                        item.is_symlink()
                        or getattr(item, "is_junction", lambda: False)()
                        or not item.resolve().is_relative_to(source)
                    ):
                        raise ValueError("Cache có liên kết ngoài thư mục.")
                    dest = stage / item.relative_to(source)
                    if item.is_dir():
                        dest.mkdir(parents=True, exist_ok=True)
                    elif item.is_file():
                        total += item.stat().st_size
                        if total > 64 * 1024**2:
                            raise ValueError("Cache vượt 64 MiB.")
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(item, dest)
        validate(stage)
        check_cancelled()
        if target.exists():
            backup = base / ("capcut-cache-backup-" + uuid.uuid4().hex[:8])
            target.rename(backup)
            try:
                stage.rename(target)
            except OSError:
                backup.rename(target)
                raise
        else:
            stage.rename(target)
        return target
    finally:
        if (
            stage.exists()
            and stage.resolve().is_relative_to(base)
            and not stage.is_symlink()
        ):
            shutil.rmtree(stage)
