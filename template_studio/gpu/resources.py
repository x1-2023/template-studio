"""Định vị shader local; không phân phối asset CapCut trong bản EXE."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def default_cache():
    from offline_studio.config import APP_ROOT
    from template_studio.paths import data_home

    return data_home(APP_ROOT) / "runtime/capcut-cache"


def resources(cache=None):
    cache = Path(cache) if cache is not None else default_cache()
    result = []
    for resource_id in ("7491138615477685505", "7514206177195068689"):
        candidates = sorted((cache / resource_id).glob("*/AmazingFeature"))
        if len(candidates) != 1:
            raise FileNotFoundError(
                "Chưa có đủ tài nguyên effect. Mở Thiết lập → Nhập cache effect."
            )
        result.append(candidates[0])
    return tuple(result)


def shader_map(effect):
    result = {}
    for path in effect.rglob("*.xshader"):
        refs = re.findall(
            rb"shaderLib/shaderGLES/([a-f0-9]{32})\.frag", path.read_bytes()
        )
        if refs:
            result[f"{path.parent.parent.name}/{path.stem}"] = (
                path.parent / "shaderLib/shaderGLES" / (refs[0].decode() + ".frag")
            )
    return result
