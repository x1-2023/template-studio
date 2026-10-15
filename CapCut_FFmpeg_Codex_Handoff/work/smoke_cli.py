"""Smoke test CLI: batch tiếp tục sau lỗi, SAR, mask, encoder CPU và bảo vệ nguồn."""

import hashlib
import json
import subprocess
import sys

from PIL import Image
from render import ROOT, probe


def main():
    folder = ROOT / "artifacts/smoke"
    folder.mkdir(parents=True, exist_ok=True)
    source = folder / "sar2.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc2=s=80x80:r=30:d=0.3",
            "-vf",
            "setsar=2",
            "-an",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(source),
        ],
        check=True,
    )
    before = hashlib.sha256(source.read_bytes()).hexdigest()
    jobs = [
        {"input": "sar2.mp4", "output": "batch1.mp4"},
        {"input": "khong-co.mp4", "output": "missing.mp4"},
        {"input": "sar2.mp4", "output": "batch2.mp4"},
    ]
    manifest = folder / "jobs.json"
    manifest.write_text(json.dumps(jobs))
    base = [sys.executable, str(ROOT / "render.py")]
    common = [
        "--width",
        "64",
        "--height",
        "96",
        "--seconds",
        "0.2",
        "--encoder",
        "libx264",
        "--overwrite",
    ]
    batch = subprocess.run(
        base + ["--batch", str(manifest), "--no-effect", "--no-filter"] + common,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert batch.returncode == 1, batch.stderr
    for name in ("batch1.mp4", "batch2.mp4"):
        streams = probe(folder / name)["streams"]
        assert len(streams) == 1 and streams[0]["sample_aspect_ratio"] == "1:1"
        assert int(streams[0]["nb_frames"]) == 6
        stats = json.loads(
            (folder / name).with_suffix(".render.json").read_text(encoding="utf-8")
        )
        assert stats["decode_size"] == [160, 80]
    mask = folder / "mask.png"
    Image.new("L", (64, 96), 255).save(mask)
    masked = subprocess.run(
        base
        + [
            str(source),
            str(folder / "masked.mp4"),
            "--skin",
            "mask",
            "--skin-mask",
            str(mask),
            "--no-effect",
        ]
        + common,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert masked.returncode == 0, masked.stderr
    protected = subprocess.run(
        base + [str(source), str(source)] + common,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert protected.returncode == 1
    assert hashlib.sha256(source.read_bytes()).hexdigest() == before
    existing = folder / "batch1.mp4"
    digest = hashlib.sha256(existing.read_bytes()).hexdigest()
    overwrite = subprocess.run(
        base + [str(source), str(existing), "--seconds", ".2"],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert (
        overwrite.returncode == 1
        and hashlib.sha256(existing.read_bytes()).hexdigest() == digest
    )
    draft = subprocess.run(
        base
        + [
            str(source),
            str(folder / "draft9x16.mp4"),
            "--preset",
            "draft-9x16",
            "--width",
            "180",
            "--height",
            "320",
            "--seconds",
            ".2",
            "--encoder",
            "libx264",
            "--overwrite",
        ],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert draft.returncode == 0, draft.stderr
    assert not list(folder.glob("*.*.partial.mp4"))
    sidecar_source = folder / "sidecar.decode.log"
    sidecar_source.write_bytes(source.read_bytes())
    collision = subprocess.run(
        base + [str(sidecar_source), str(folder / "sidecar.mp4")] + common,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert collision.returncode == 1
    assert hashlib.sha256(sidecar_source.read_bytes()).hexdigest() == before
    partial_source = folder / "legit.partial.mp4"
    partial_source.write_bytes(source.read_bytes())
    suffix_case = subprocess.run(
        base + [str(partial_source), str(folder / "legit.mp4")] + common,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert suffix_case.returncode == 0, suffix_case.stderr
    assert hashlib.sha256(partial_source.read_bytes()).hexdigest() == before
    result = {
        "batch_continues_after_failure": True,
        "no_audio": True,
        "non_square_input_sar": True,
        "external_skin_mask": True,
        "source_protected": True,
        "overwrite_protected": True,
        "synthetic_draft_9x16": True,
        "partial_cleanup": True,
        "sidecar_source_protected": True,
        "partial_suffix_source_protected": True,
    }
    (ROOT / "artifacts/smoke_cli.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
