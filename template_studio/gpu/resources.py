"""Định vị tài nguyên đóng kèm và cache tùy chọn của người dùng."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def bundled_cache(root=None):
    base = Path(root) / "template_studio" if root is not None else ROOT.parent
    return base / "assets/effects"


def default_cache():
    from offline_studio.config import APP_ROOT
    from template_studio.paths import data_home

    local = data_home(APP_ROOT) / "runtime/capcut-cache"
    return local if local.is_dir() else bundled_cache()


def resources(cache=None):
    cache = Path(cache) if cache is not None else default_cache()
    if (cache / "runtime-manifest.json").is_file():
        return cache / "effect", cache / "tone"
    result = []
    for resource_id in ("7491138615477685505", "7514206177195068689"):
        candidates = sorted((cache / resource_id).glob("*/AmazingFeature"))
        if len(candidates) != 1:
            raise FileNotFoundError(
                "Gói hiệu ứng thiếu tài nguyên. Tải lại app hoặc nhập gói trong Cài đặt."
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
