"""Kiểm tra cấu hình mã hóa có giới hạn bitrate và cấu hình chất lượng cũ."""

import unittest

from render import video_encoder_args


class EncodingTests(unittest.TestCase):
    def test_nvenc_budget_uses_bitrate_without_quality_override(self):
        args = video_encoder_args("h264_nvenc", 9.65)
        self.assertEqual(args[args.index("-b:v") + 1], "9650000")
        self.assertEqual(args[args.index("-maxrate") + 1], "14475000")
        self.assertNotIn("-cq", args)

    def test_quality_mode_remains_available(self):
        args = video_encoder_args("h264_nvenc")
        self.assertEqual(args[args.index("-cq") + 1], "18")
        self.assertEqual(args[args.index("-b:v") + 1], "0")

    def test_cpu_encoder_accepts_budget(self):
        args = video_encoder_args("libx264", 9.65)
        self.assertIn("9650000", args)
        self.assertNotIn("-crf", args)

    def test_invalid_bitrates_fail(self):
        for bitrate in (-1, 0, float("nan"), float("inf"), 201):
            with self.assertRaises(ValueError):
                video_encoder_args("h264_nvenc", bitrate)


if __name__ == "__main__":
    unittest.main(verbosity=2)
