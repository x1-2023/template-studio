"""Chạy effect v7 trên layout/thời gian đã đo để so sánh công bằng với GPU."""

import argparse
import json
import subprocess
import sys
import time

import numpy as np
from align import MEDIA, ROOT
from gpu import Renderer
from render import load_preset, read_exact

sys.path.insert(0, str(ROOT.parent / "03_CURRENT_V7"))
from reference_bokeh import effect_frame


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--width", type=int, default=540)
    parser.add_argument("--height", type=int, default=720)
    a = parser.parse_args()
    w, h = a.width, a.height
    dw, dh = (1080, 1920) if w >= 1080 else (426, 756)
    config = load_preset("capcut-pentagon")
    config.update(width=w, height=h)
    gpu = Renderer((dw, dh), (w, h), config)
    output = ROOT / f"artifacts/baseline_v7_aligned_{w}_3s.mp4"
    cmd = [
        "ffmpeg",
        "-v",
        "error",
        "-i",
        str(MEDIA / "source_original_compre_juguetes.mp4"),
        "-t",
        "3",
        "-vf",
        f"setpts=(PTS-STARTPTS)/{config['playback_rate']},fps=30:round=up,scale={dw}:{dh}",
        "-an",
        "-pix_fmt",
        "rgb24",
        "-f",
        "rawvideo",
        "pipe:1",
    ]
    decode = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    encode = subprocess.Popen(
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgb24",
            "-s",
            f"{w}x{h}",
            "-r",
            "30",
            "-i",
            "pipe:0",
            "-an",
            "-c:v",
            "h264_nvenc",
            "-cq",
            "18",
            "-b:v",
            "0",
            "-pix_fmt",
            "yuv420p",
            str(output),
        ],
        stdin=subprocess.PIPE,
    )
    started = time.perf_counter()
    count = 0
    try:
        for i in range(90):
            raw = read_exact(decode.stdout, dw * dh * 3)
            if len(raw) != dw * dh * 3:
                raise RuntimeError("Thiếu frame baseline")
            base = gpu.process(
                np.frombuffer(raw, np.uint8).reshape(dh, dw, 3),
                i / 30,
                effect=False,
                tone=False,
            )
            result = effect_frame(
                base[:, :, ::-1].copy(), i / 30, sides=5, intensity=1.0
            )[:, :, ::-1]
            encode.stdin.write(np.ascontiguousarray(result).tobytes())
            count += 1
        decode.stdout.close()
        encode.stdin.close()
        if decode.wait() or encode.wait():
            raise RuntimeError("FFmpeg baseline thất bại")
    finally:
        for proc in (decode, encode):
            if proc.poll() is None:
                proc.kill()
                proc.wait()
        gpu.close()
    seconds = time.perf_counter() - started
    (ROOT / f"artifacts/baseline_aligned_{w}.json").write_text(
        json.dumps(
            {
                "frames": count,
                "wall_seconds": seconds,
                "fps": count / seconds,
                "method": "Effect v7 nguyên bản; canvas GPU cùng preset; không LUT; không dùng timing/layout cũ",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Baseline đã căn: {count} frames / {seconds:.2f}s", flush=True)


if __name__ == "__main__":
    main()
