"""Kiểm tra cường độ LUT và thứ tự filter trên cùng cặp frame đã căn thời gian."""

import json
import subprocess

import numpy as np
from align import MEDIA, ROOT, frames
from evaluate import TIMES, metrics
from gpu import Renderer
from PIL import Image, ImageDraw
from render import load_preset


def main():
    cfg = load_preset("capcut-pentagon")
    cfg.update(width=540, height=720)
    raw = subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-i",
            str(MEDIA / "source_original_compre_juguetes.mp4"),
            "-t",
            "2.1",
            "-vf",
            "setpts=(PTS-STARTPTS)/1.02,fps=30,scale=426:756",
            "-an",
            "-pix_fmt",
            "rgb24",
            "-f",
            "rawvideo",
            "pipe:1",
        ],
        capture_output=True,
        check=True,
    ).stdout
    src = np.frombuffer(raw, np.uint8).reshape(-1, 756, 426, 3)
    ref = frames(MEDIA / "capcut_export_test.mp4", 540, 720, 2.1)
    gpu = Renderer((426, 756), (540, 720), cfg)
    rows = []
    for stage in ("before", "after"):
        for strength in (0, 0.25, 0.5, 0.75, 1):
            for skin in ("none", "chroma"):
                gpu.preset = {
                    **cfg,
                    "filter_stage": stage,
                    "filter_intensity": strength,
                }
                gpu.skin = skin
                scores = [
                    metrics(ref[round(t * 30)], gpu.process(src[round(t * 30)], t))
                    for t in TIMES
                ]
                rows.append(
                    {
                        "filter_stage": stage,
                        "filter_intensity": strength,
                        "skin": skin,
                        "ssim": float(np.mean([r["ssim_rgb"] for r in scores])),
                        "early": float(np.mean([r["ssim_rgb"] for r in scores[:5]])),
                        "late": float(np.mean([r["ssim_rgb"] for r in scores[5:]])),
                        "psnr": float(np.mean([r["psnr_rgb_db"] for r in scores])),
                    }
                )
    rows.sort(key=lambda r: r["ssim"], reverse=True)
    (ROOT / "artifacts/color_tuning.json").write_text(json.dumps(rows, indent=2))
    print(json.dumps(rows[:8], indent=2), flush=True)
    sheet = Image.new("RGB", (240 * 9, 348 * 4), "#161616")
    draw = ImageDraw.Draw(sheet)
    variants = [
        {"name": "CapCut"},
        {"name": "Cache", **cfg},
        {"name": "Best", **cfg, **rows[0]},
        {"name": "After1", **cfg, "filter_stage": "after"},
    ]
    for j, config in enumerate(variants):
        gpu.preset = config
        gpu.skin = config.get("skin", "none")
        for i, t in enumerate(TIMES):
            im = ref[round(t * 30)] if j == 0 else gpu.process(src[round(t * 30)], t)
            sheet.paste(Image.fromarray(im).resize((240, 320)), (i * 240, j * 348 + 28))
            draw.text(
                (i * 240 + 5, j * 348 + 5), f"{config['name']} {t:.2f}s", fill="white"
            )
    sheet.save(ROOT / "artifacts/color_tuning.jpg", quality=94)
    gpu.close()


if __name__ == "__main__":
    main()
