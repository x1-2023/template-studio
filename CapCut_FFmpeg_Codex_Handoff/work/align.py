"""Đo lật ngang, thời gian và affine bằng đặc trưng ở đoạn đã hết bokeh."""

import json
import subprocess
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent
MEDIA = ROOT.parent / "02_REFERENCE_MEDIA"


def frames(path, width, height, seconds, fps=30):
    cmd = [
        "ffmpeg",
        "-v",
        "error",
        "-i",
        str(path),
        "-t",
        str(seconds),
        "-vf",
        f"fps={fps},scale={width}:{height}",
        "-an",
        "-pix_fmt",
        "rgb24",
        "-f",
        "rawvideo",
        "pipe:1",
    ]
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, height, width, 3)


def main():
    src = frames(MEDIA / "source_original_compre_juguetes.mp4", 240, 426, 5, 30)
    ref = frames(MEDIA / "capcut_export_test.mp4", 360, 480, 4.2, 30)
    sift = cv2.SIFT_create(nfeatures=1300)
    clahe = cv2.createCLAHE(2.0, (8, 8))

    def features(im):
        return sift.detectAndCompute(
            clahe.apply(cv2.cvtColor(im, cv2.COLOR_RGB2GRAY)), None
        )

    matcher = cv2.BFMatcher()
    rows = []
    for flip in (False, True):
        feats = [
            features(np.ascontiguousarray(im[:, ::-1]) if flip else im) for im in src
        ]
        for t in (1.5, 2, 2.5, 3, 4):
            kr, dr = features(ref[round(t * 30)])
            candidates = []
            for i, (ks, ds) in enumerate(feats):
                pairs = matcher.knnMatch(ds, dr, k=2)
                good = [a for a, b in pairs if a.distance < 0.68 * b.distance]
                if len(good) < 8:
                    continue
                xy = np.float32([ks[m.queryIdx].pt for m in good])
                uv = np.float32([kr[m.trainIdx].pt for m in good])
                matrix, inliers = cv2.estimateAffinePartial2D(
                    xy, uv, method=cv2.RANSAC, ransacReprojThreshold=1.6
                )
                if matrix is None:
                    continue
                scale = float(np.hypot(matrix[0, 0], matrix[1, 0]))
                if not 0.9 < scale < 1.4 or abs(matrix[1, 0]) > 0.04:
                    continue
                n = int(inliers.sum())
                residual = np.linalg.norm(
                    xy @ matrix[:, :2].T + matrix[:, 2] - uv, axis=1
                )[inliers.ravel() != 0]
                candidates.append(
                    {
                        "reference_time": t,
                        "source_time": i / 30,
                        "flip": flip,
                        "inliers": n,
                        "median_error_px": float(np.median(residual)),
                        "matrix_source240_to_ref360": matrix.tolist(),
                    }
                )
            best = sorted(candidates, key=lambda r: r["inliers"], reverse=True)[:3]
            rows.extend(best)
            print(json.dumps(best[:1]), flush=True)
    (ROOT / "artifacts/alignment_candidates.json").write_text(
        json.dumps(rows, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
