"""Kiểm tra tốc độ bằng đường bao audio; không suy ra từ slider effect."""

import json
import subprocess

import numpy as np
from align import MEDIA, ROOT


def envelope(path):
    raw = subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-i",
            str(path),
            "-t",
            "18",
            "-vn",
            "-ac",
            "1",
            "-ar",
            "8000",
            "-f",
            "f32le",
            "pipe:1",
        ],
        capture_output=True,
        check=True,
    ).stdout
    samples = np.frombuffer(raw, "f4")
    return np.sqrt(
        np.mean(samples[: len(samples) // 80 * 80].reshape(-1, 80) ** 2, axis=1)
    )


def main():
    src = envelope(MEDIA / "source_original_compre_juguetes.mp4")
    ref = envelope(MEDIA / "capcut_export_test.mp4")[:1600]
    tx = np.arange(len(ref)) / 100
    records = []
    for rate in np.arange(1.0, 1.04001, 0.0001):
        for offset in np.arange(-0.05, 0.0501, 0.005):
            warped = np.interp(tx * rate + offset, np.arange(len(src)) / 100, src)
            score = float(np.corrcoef(warped, ref)[0, 1])
            records.append(
                {
                    "rate": float(rate),
                    "source_offset": float(offset),
                    "envelope_correlation": score,
                }
            )
    records.sort(key=lambda r: r["envelope_correlation"], reverse=True)
    (ROOT / "artifacts/audio_timing.json").write_text(
        json.dumps(records[:20], indent=2)
    )
    print(json.dumps(records[:3], indent=2))


if __name__ == "__main__":
    main()
