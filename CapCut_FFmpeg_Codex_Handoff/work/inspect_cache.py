"""Kiểm kê cache, giữ nguyên nguồn shader và bằng chứng liên kết tài nguyên."""

import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def resources(cache=ROOT / "cache"):
    result = []
    for resource_id in ("7491138615477685505", "7514206177195068689"):
        paths = list((cache / resource_id).glob("*/AmazingFeature"))
        if len(paths) != 1:
            raise FileNotFoundError(
                f"Cần đúng một AmazingFeature cho {resource_id} trong {cache}; chạy prepare_cache.py"
            )
        result.append(paths[0])
    return tuple(result)


def strings(path):
    return [
        v.decode("ascii") for v in re.findall(rb"[\x20-\x7e]{4,}", path.read_bytes())
    ]


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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    effect, _tone = resources()
    result = {
        "shaders": {k: str(v.relative_to(ROOT)) for k, v in shader_map(effect).items()},
        "files": [],
    }
    for path in sorted((ROOT / "cache").rglob("*")):
        if path.is_file():
            row = {
                "path": str(path.relative_to(ROOT)),
                "bytes": path.stat().st_size,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
            if path.suffix in (".scene", ".material", ".rt", ".dat"):
                row["strings"] = strings(path)
            result["files"].append(row)
    out = ROOT / "artifacts/cache_inventory.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "files": len(result["files"]),
                "shader_variants": len(result["shaders"]),
                "inventory": str(out),
            }
        )
    )
    if args.verbose:
        print(json.dumps(result["shaders"], indent=2))
        for path in (effect / "main.scene", effect / "graph.dat"):
            print(path.name, json.dumps(strings(path), ensure_ascii=False))


if __name__ == "__main__":
    main()
