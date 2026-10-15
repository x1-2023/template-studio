"""Đối chiếu cadence 59.94→30 fps ở độ phân giải thấp, không warp đầu ra."""

import json
import subprocess

import cv2
import numpy as np
from align import MEDIA, ROOT, frames


def main():
    raw = subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-i",
            str(MEDIA / "source_original_compre_juguetes.mp4"),
            "-t",
            "8",
            "-vf",
            "scale=240:426",
            "-fps_mode",
            "passthrough",
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
    source = np.frombuffer(raw, np.uint8).reshape(-1, 426, 240, 3)
    ref = frames(MEDIA / "capcut_export_test.mp4", 360, 480, 7.1)
    sift = cv2.SIFT_create(nfeatures=1600)
    matcher = cv2.BFMatcher()
    clahe = cv2.createCLAHE(2.0, (8, 8))
    memo = {}

    def features(frame):
        return sift.detectAndCompute(
            clahe.apply(cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)), None
        )

    rows = []
    for t in (0.8, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 7.0):
        kr, dr = features(ref[round(t * 30)])
        candidates = []
        center = round(t * 1.02 * 60000 / 1001)
        for i in range(max(0, center - 5), min(len(source), center + 6)):
            if i not in memo:
                memo[i] = features(np.ascontiguousarray(source[i, :, ::-1]))
            ks, ds = memo[i]
            pairs = matcher.knnMatch(ds, dr, k=2)
            good = [a for a, b in pairs if a.distance < 0.7 * b.distance]
            if len(good) < 8:
                continue
            xy = np.float32([ks[m.queryIdx].pt for m in good])
            uv = np.float32([kr[m.trainIdx].pt for m in good])
            mat, inliers = cv2.estimateAffinePartial2D(
                xy, uv, method=cv2.RANSAC, ransacReprojThreshold=1.6
            )
            if mat is None or not 1.1 < np.hypot(mat[0, 0], mat[1, 0]) < 1.25:
                continue
            residual = np.linalg.norm(xy @ mat[:, :2].T + mat[:, 2] - uv, axis=1)[
                inliers.ravel() != 0
            ]
            candidates.append(
                {
                    "t": t,
                    "source_frame": i,
                    "source_time": i * 1001 / 60000,
                    "inliers": int(inliers.sum()),
                    "error": float(np.median(residual)),
                    "matrix": mat.tolist(),
                }
            )
        candidates.sort(key=lambda r: r["inliers"], reverse=True)
        rows.append(candidates[:3])
        print(json.dumps(candidates[:1]), flush=True)
    best = [r[0] for r in rows]
    matrix = np.array([[r["t"], 1] for r in best])
    values = np.array([r["source_time"] for r in best])
    fit = np.linalg.lstsq(matrix, values, rcond=None)[0]
    result = {
        "fps_source": 60000 / 1001,
        "candidates": rows,
        "linear_fit_rate_offset": fit.tolist(),
    }
    (ROOT / "artifacts/refined_alignment.json").write_text(json.dumps(result, indent=2))
    print(json.dumps({"linear_fit_rate_offset": fit.tolist()}), flush=True)


if __name__ == "__main__":
    main()
