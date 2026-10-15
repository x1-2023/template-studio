"""Chấm SSIM/PSNR theo timestamp, không đăng ký ảnh riêng từng frame để giấu sai lệch."""

import argparse
import json
import subprocess

import cv2
import numpy as np
from align import MEDIA, ROOT
from PIL import Image, ImageDraw

TIMES = (0, 0.1, 0.2, 0.3, 0.5, 0.8, 1.0, 1.5, 2.0)


def samples(path, width, height):
    expression = "+".join(f"eq(n\\,{round(t * 30)})" for t in TIMES)
    cmd = [
        "ffmpeg",
        "-v",
        "error",
        "-i",
        str(path),
        "-t",
        "2.1",
        "-vf",
        f"fps=30,select='{expression}',scale={width}:{height}",
        "-fps_mode",
        "passthrough",
        "-an",
        "-pix_fmt",
        "rgb24",
        "-f",
        "rawvideo",
        "pipe:1",
    ]
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    result = np.frombuffer(raw, np.uint8).reshape(-1, height, width, 3)
    if len(result) != len(TIMES):
        raise ValueError(f"Thiếu frame tại mốc chấm điểm: {path}")
    return result


def metrics(a, b):
    a, b = a.astype(np.float64), b.astype(np.float64)
    mse = float(np.mean((a - b) ** 2))

    def ssim(x, y):
        mx = cv2.GaussianBlur(x, (11, 11), 1.5)
        my = cv2.GaussianBlur(y, (11, 11), 1.5)
        vx = cv2.GaussianBlur(x * x, (11, 11), 1.5) - mx * mx
        vy = cv2.GaussianBlur(y * y, (11, 11), 1.5) - my * my
        cov = cv2.GaussianBlur(x * y, (11, 11), 1.5) - mx * my
        z = ((2 * mx * my + 6.5025) * (2 * cov + 58.5225)) / (
            (mx * mx + my * my + 6.5025) * (vx + vy + 58.5225)
        )
        return float(z[5:-5, 5:-5].mean())

    weights = np.array([0.299, 0.587, 0.114])
    return {
        "ssim_rgb": ssim(a, b),
        "ssim_y": ssim(a @ weights, b @ weights),
        "psnr_rgb_db": 10 * np.log10(255**2 / max(1e-12, mse)),
        "mae_rgb": float(np.mean(np.abs(a - b))),
        "white_pixel_ratio": float(np.mean(np.all(b >= 250, axis=2))),
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("videos", nargs="+", help="LABEL=FILE")
    p.add_argument("--width", type=int, default=540)
    p.add_argument("--height", type=int, default=720)
    p.add_argument("--prefix", default="comparison")
    a = p.parse_args()
    ref = samples(MEDIA / "capcut_export_test.mp4", a.width, a.height)
    rows = {"CapCut": ref}
    for pair in a.videos:
        label, path = pair.split("=", 1)
        rows[label] = samples(path, a.width, a.height)
    report = {
        "resolution": [a.width, a.height],
        "method": "RGB SSIM Gaussian 11x11 sigma1.5, crop5; PSNR RGB; không warp frame",
        "timestamps": list(TIMES),
        "results": {},
    }
    cw, ch = 240, 320
    sheet = Image.new("RGB", (len(TIMES) * cw, len(rows) * (ch + 28)), "#161616")
    draw = ImageDraw.Draw(sheet)
    for j, (label, video) in enumerate(rows.items()):
        scores = []
        for i, t in enumerate(TIMES):
            index = i
            im = video[index]
            sheet.paste(
                Image.fromarray(im).resize((cw, ch)), (i * cw, j * (ch + 28) + 28)
            )
            draw.text(
                (i * cw + 5, j * (ch + 28) + 5), f"{label} {t:.2f}s", fill="white"
            )
            if label != "CapCut":
                row = {"t": t, **metrics(ref[index], im)}
                left, right = round(a.width * 0.12), round(a.width * 0.88)
                roi = metrics(ref[index, :, left:right], im[:, left:right])
                row["foreground_ssim_rgb"] = roi["ssim_rgb"]
                row["foreground_psnr_rgb_db"] = roi["psnr_rgb_db"]
                scores.append(row)
        if scores:
            report["results"][label] = {
                "frames": scores,
                "mean": {
                    k: float(np.mean([r[k] for r in scores]))
                    for k in scores[0]
                    if k != "t"
                },
            }
    sheet.save(ROOT / f"artifacts/{a.prefix}.jpg", quality=94)
    (ROOT / f"artifacts/{a.prefix}.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({k: v["mean"] for k, v in report["results"].items()}, indent=2))


if __name__ == "__main__":
    main()
