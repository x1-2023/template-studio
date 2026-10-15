"""Thử giả thuyết hữu hạn; lưu điểm số và tham số, không thay ảnh đích."""

import json
import subprocess
from itertools import product

import numpy as np
from align import MEDIA, ROOT, frames
from evaluate import TIMES, metrics
from gpu import Renderer
from PIL import Image, ImageDraw
from render import load_preset


def main():
    cfg = load_preset("capcut-pentagon")
    cfg.update(width=540, height=720)
    cmd = [
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
    ]
    src = np.frombuffer(
        subprocess.run(cmd, capture_output=True, check=True).stdout, np.uint8
    ).reshape(-1, 756, 426, 3)
    ref = frames(MEDIA / "capcut_export_test.mp4", 540, 720, 2.1)
    gpu = Renderer((426, 756), (540, 720), cfg)
    records = []
    for stage, size, blur, skin in product(
        ("before", "after"), (0.5, 0.6, 0.7, 0.8), (1.0, 0.5), ("none", "chroma")
    ):
        gpu.preset = {
            **cfg,
            "filter_stage": stage,
            "bokeh_size": size,
            "preblur_scale": blur,
        }
        gpu.skin = skin
        scores = []
        for t in TIMES:
            im = gpu.process(src[round(t * 30)], t)
            scores.append(metrics(ref[round(t * 30)], im))
        row = {
            "filter_stage": stage,
            "bokeh_size": size,
            "preblur_scale": blur,
            "skin": skin,
            "ssim": float(np.mean([r["ssim_rgb"] for r in scores])),
            "early_ssim": float(np.mean([r["ssim_rgb"] for r in scores[:5]])),
            "psnr": float(np.mean([r["psnr_rgb_db"] for r in scores])),
        }
        records.append(row)
    records.sort(key=lambda x: x["ssim"], reverse=True)
    print(json.dumps(records[:10], indent=2), flush=True)
    (ROOT / "artifacts/tuning.json").write_text(json.dumps(records, indent=2))
    configs = [{"name": "Cache", **cfg}, {"name": "Best", **cfg, **records[0]}]
    sheet = Image.new("RGB", (240 * 9, 348 * 3), "#161616")
    draw = ImageDraw.Draw(sheet)
    for j, config in enumerate([{"name": "CapCut"}] + configs):
        for i, t in enumerate(TIMES):
            if j == 0:
                im = ref[round(t * 30)]
            else:
                gpu.preset = config
                gpu.skin = config.get("skin", "none")
                im = gpu.process(src[round(t * 30)], t)
            sheet.paste(Image.fromarray(im).resize((240, 320)), (i * 240, j * 348 + 28))
            draw.text(
                (i * 240 + 5, j * 348 + 5), f"{config['name']} {t:.2f}s", fill="white"
            )
    sheet.save(ROOT / "artifacts/tuning.jpg", quality=95)
    gpu.close()


if __name__ == "__main__":
    main()
