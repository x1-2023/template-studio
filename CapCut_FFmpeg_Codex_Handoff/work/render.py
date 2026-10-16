"""CLI tương thích dùng engine chung của Template Studio."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parents[1]))
from template_studio.gpu import pipeline  # noqa: E402
pipeline.ROOT = ROOT
from template_studio.gpu.pipeline import probe, read_exact, load_preset, render, video_encoder_args  # noqa: F401,E402
if __name__ == "__main__":
    raise SystemExit(pipeline.main())
