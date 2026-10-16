"""Wrapper tương thích; engine GPU dùng chung với GUI."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parents[1]))
from template_studio.gpu.renderer import Renderer as BaseRenderer, animation, bezier, desktop_fragment  # noqa: F401,E402
class Renderer(BaseRenderer):
    def __init__(self, input_size, output_size, preset, skin="none", cache=ROOT / "cache"):
        super().__init__(input_size, output_size, preset, skin, cache)
