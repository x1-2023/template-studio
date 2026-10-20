"""Đo pixel thật của pass chỉnh màu; giữ đường render cũ khi tất cả mức bằng 0."""

import unittest

import moderngl
import numpy as np

from template_studio.gpu.renderer import Renderer
from template_studio.presets import normalize


class AdjustmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            context = moderngl.create_standalone_context(require=330)
        except Exception as error:
            raise unittest.SkipTest(f"Không có OpenGL 3.3: {error}")
        context.release()

    def render(self, **changes):
        config = normalize(dict(scale=1, **changes))
        renderer = Renderer((32, 32), (32, 32), config)
        self.addCleanup(renderer.close)
        frame = np.full((32, 32, 3), [80, 120, 160], dtype=np.uint8)
        return renderer.process(frame, 3, effect=False, tone=False)[16, 16].astype(float)

    def test_neutral_is_identity_and_brightness_increases_channels(self):
        np.testing.assert_array_equal(self.render(), [80, 120, 160])
        np.testing.assert_allclose(self.render(brightness=.1), [106, 146, 186], atol=1)

    def test_saturation_contrast_and_hue_change_video_independently(self):
        gray = self.render(saturation=-1)
        self.assertLessEqual(np.ptp(gray), 1)
        np.testing.assert_allclose(self.render(contrast=-1), [128]*3, atol=1)
        self.assertGreater(np.max(np.abs(self.render(hue=90)-self.render())), 25)
