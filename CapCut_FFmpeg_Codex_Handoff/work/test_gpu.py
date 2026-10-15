"""Kiểm tra số học shader, hướng ảnh và fallback LUT trên GPU thật."""

import unittest

import numpy as np
from gpu import Renderer, animation, bezier
from render import load_preset


def atlas_sample(atlas, rgb):
    def bilinear(uv):
        xy = np.clip(uv * 512 - 0.5, 0, 511)
        lo = np.floor(xy).astype(int)
        hi = np.minimum(lo + 1, 511)
        p = xy - lo
        x, y = lo[..., 0], lo[..., 1]
        xx, yy = hi[..., 0], hi[..., 1]
        a = atlas[y, x] * (1 - p[..., 0, None]) + atlas[y, xx] * p[..., 0, None]
        b = atlas[yy, x] * (1 - p[..., 0, None]) + atlas[yy, xx] * p[..., 0, None]
        return a * (1 - p[..., 1, None]) + b * p[..., 1, None]

    blue = rgb[..., 2] * 63
    slices = [np.floor(blue), np.ceil(blue)]
    values = []
    for z in slices:
        uv = (
            np.stack((np.mod(z, 8), np.floor(z / 8)), axis=-1) / 8
            + 0.5 / 512
            + (1 / 8 - 1 / 512) * rgb[..., :2]
        )
        values.append(bilinear(uv))
    p = blue - np.floor(blue)
    return values[0] * (1 - p[..., None]) + values[1] * p[..., None]


class AnimationTests(unittest.TestCase):
    def test_slider_does_not_change_keyframe_time(self):
        a = animation(0.2, {"effect_slider": 1 / 3})
        b = animation(0.2, {"effect_slider": 1})
        self.assertAlmostEqual(a["sample"], b["sample"])
        self.assertAlmostEqual(a["amount"] * 3, b["amount"])
        self.assertEqual(animation(1.0, {})["sample"], 0)
        self.assertEqual(animation(0, {})["sample"], 80)

    def test_bezier_boundaries(self):
        curve = (0.5, 0, 0.43, 1)
        values = [bezier(t, curve) for t in np.linspace(0, 1, 100)]
        self.assertEqual(values[0], 0)
        self.assertEqual(values[-1], 1)
        self.assertTrue(np.all(np.diff(values) >= 0))


class ShaderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        config = load_preset("capcut-pentagon")
        config.update(flip=False, scale=1.0, filter_stage="after")
        cls.gpu = Renderer((64, 96), (64, 96), config)

    @classmethod
    def tearDownClass(cls):
        cls.gpu.close()

    def test_orientation_and_flip(self):
        rng = np.random.default_rng(31)
        frame = rng.integers(0, 256, (96, 64, 3), dtype=np.uint8)
        self.gpu.preset["flip"] = False
        actual = self.gpu.process(frame, 3, effect=False, tone=False)
        self.assertLessEqual(np.abs(actual.astype(int) - frame.astype(int)).max(), 1)
        self.gpu.preset["flip"] = True
        flipped = self.gpu.process(frame, 3, effect=False, tone=False)
        self.assertLessEqual(
            np.abs(flipped.astype(int) - frame[:, ::-1].astype(int)).max(), 1
        )
        self.gpu.preset["flip"] = False

    def test_sharpness_constant_does_not_blow_out(self):
        data = np.full((96, 64, 4), 128, np.uint8)
        data[..., 3] = 255
        texture = self.gpu.texture((64, 96), 4, data.tobytes())
        self.gpu.run("sharp", "test_sharp", {"u_albedo": texture}, {"u_sharpness": 0.6})
        actual = np.frombuffer(
            self.gpu.targets["test_sharp"][1].read(components=3, alignment=1), np.uint8
        )
        self.assertLessEqual(np.abs(actual.astype(int) - 128).max(), 2)
        texture.release()

    def test_both_lut_atlases_match_cpu_sampler(self):
        rng = np.random.default_rng(53)
        rgb = rng.integers(0, 256, (96, 64, 3), dtype=np.uint8)
        rgba = np.concatenate((rgb, np.full((96, 64, 1), 255, np.uint8)), axis=2)
        texture = self.gpu.texture((64, 96), 4, rgba.tobytes())
        for mask_value, lut in ((0, "bg_lut"), (255, "skin_lut")):
            mask = self.gpu.texture((1, 1), 4, bytes([mask_value] * 4))
            self.gpu.run(
                "tone",
                "test_lut",
                {
                    "inputImageTexture": texture,
                    "inputImageTexture2": self.gpu.images["bg_lut"],
                    "inputImageTexture4": self.gpu.images["skin_lut"],
                    "mask": mask,
                },
                {"intensity": 1.0},
            )
            actual = np.frombuffer(
                self.gpu.targets["test_lut"][1].read(components=3, alignment=1),
                np.uint8,
            ).reshape(96, 64, 3)
            atlas = (
                np.frombuffer(self.gpu.images[lut].read(alignment=1), np.uint8).reshape(
                    512, 512, 4
                )[..., :3]
                / 255
            )
            expected = np.rint(atlas_sample(atlas, rgb / 255) * 255)
            self.assertLessEqual(np.abs(actual.astype(int) - expected).max(), 1)
            mask.release()
        texture.release()

    def test_dark_frame_has_no_generated_polygons(self):
        black = np.zeros((96, 64, 3), np.uint8)
        output = self.gpu.process(black, 0, effect=True, tone=False)
        self.assertLessEqual(int(output.max()), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
