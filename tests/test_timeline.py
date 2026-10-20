"""Kiểm tra cắt nguồn, bỏ quảng cáo, thời gian phụ đề và FFmpeg thật qua mối nối."""

import math
import subprocess
import tempfile
import unittest
import wave
from pathlib import Path

import numpy as np

from offline_studio.process import NO_WINDOW, binary, probe
from template_studio.gpu.pipeline import decoded_frames
from template_studio.gpu.timing import edited_audio_window, video_windows
from template_studio.parts import plan_parts
from template_studio.presets import normalize
from template_studio.timeline import SourceTimeline, format_time, parse_time


class TimelineTests(unittest.TestCase):
    def test_time_fields_accept_clock_and_seconds_but_reject_ambiguous_values(self):
        for text, seconds in (("10:00", 600), ("01:02:03.5", 3723.5), ("90", 90), (" 0:09.125 ", 9.125)):
            self.assertEqual(parse_time(text), seconds)
            self.assertEqual(parse_time(format_time(seconds)), seconds)
        for text in ("1:60", "1:90:00", "-2", "nan", "inf", "1.5:20", "", "1:2:3:4", "24:00:01"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                parse_time(text)

    def test_first_ten_minutes_of_twenty_split_into_three_without_using_tail(self):
        config = normalize(dict(source_end=600, part_count=3))
        self.assertEqual(plan_parts(1200, config),
                         [dict(start=0, seconds=200), dict(start=200, seconds=200), dict(start=400, seconds=200)])
        config.update(source_offset=60, source_end=600, playback_rate=1.5)
        self.assertAlmostEqual(sum(p["seconds"] for p in plan_parts(1200, config)), 360)

    def test_removals_merge_clip_and_map_words_without_advertisement_words(self):
        config = normalize(dict(source_offset=10, source_end=80,
                                source_skip=[[40, 45], [30, 42], [0, 12], [90, 95]], playback_rate=2))
        self.assertEqual(config["source_skip"], [[0, 12], [30, 45], [90, 95]])
        timeline = SourceTimeline(100, config)
        self.assertAlmostEqual(timeline.duration, 26.5)
        self.assertEqual(timeline.source_at(0), 12)
        self.assertEqual(timeline.source_at(9), 45)
        words = timeline.map_words([dict(text="CŨ", start=0, end=10), dict(text="ĐẦU", start=12, end=14),
                                    dict(text="QUẢNG CÁO", start=31, end=43), dict(text="SAU", start=46, end=48)])
        self.assertEqual(words, [dict(text="ĐẦU", start=0, end=1), dict(text="SAU", start=9.5, end=10.5)])

    def test_auto_parts_find_pause_after_edits_and_preserve_every_kept_second(self):
        config = normalize(dict(source_offset=10, source_end=120, source_skip=[[30, 40]],
                                part_count=0, part_seconds=30, playback_rate=1.5))
        words = [dict(text="END.", start=64, end=68), dict(text="NEXT", start=70, end=72)]
        parts = plan_parts(200, config, words)
        self.assertAlmostEqual(parts[1]["start"], 32)
        self.assertAlmostEqual(sum(part["seconds"] for part in parts), 100/1.5)

    def test_empty_or_invalid_ranges_are_rejected_and_shorter_source_is_clamped(self):
        for value in (dict(source_offset=10, source_end=5), dict(source_skip=[[4, 4]]),
                      dict(source_skip=[[0, float("inf")]]), dict(source_skip="0-10"),
                      dict(source_skip=[[0, 1]]*21), dict(source_end=float("nan"))):
            with self.subTest(value=value), self.assertRaises(ValueError):
                normalize(value)
        for value in (dict(source_offset=20), dict(source_skip=[[0, 20]])):
            with self.assertRaises(ValueError):
                SourceTimeline(10, normalize(value))
        self.assertEqual(SourceTimeline(10, normalize(dict(source_end=600))).duration, 10)

    def test_many_cuts_share_frame_grid_and_preview_does_not_reset_phase(self):
        timeline = SourceTimeline(20, normalize(dict(source_offset=.17, source_end=15.63,
            source_skip=[[2.12, 3.7], [4.49, 8.11], [10.33, 10.41]], playback_rate=1.02931464386368)))
        for start in (0, 1, 3.8, 5.5):
            seconds = min(3, timeline.duration-start)
            windows = video_windows(timeline, start, seconds, 30)
            self.assertEqual(sum(item["frames"] for item in windows), math.ceil(seconds*30-1e-6))
            self.assertAlmostEqual(windows[0]["source"], timeline.source_at(start))


class EditedMediaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            cls.ffmpeg = binary("ffmpeg")
        except FileNotFoundError:
            raise unittest.SkipTest("Chưa chuẩn bị FFmpeg.")
        cls.temp = tempfile.TemporaryDirectory()
        cls.folder = Path(cls.temp.name)
        cls.source = cls.folder/"nguồn có quảng cáo.mkv"
        samples = np.arange(8*48000)/48000
        frequencies = 200*(np.floor(samples)+1)
        signal = (.6*np.sin(2*np.pi*frequencies*samples)*32767).astype("<i2")
        audio = cls.folder/"audio.wav"
        with wave.open(str(audio), "wb") as stream:
            stream.setnchannels(1)
            stream.setsampwidth(2)
            stream.setframerate(48000)
            stream.writeframes(signal.tobytes())
        frames = np.zeros((24*8, 32, 32, 3), np.uint8)
        frames[:, :, :, 0] = np.arange(len(frames))[:, None, None]
        subprocess.run([cls.ffmpeg, "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "32x32",
            "-r", "24", "-i", "pipe:0", "-i", str(audio), "-c:v", "ffv1", "-c:a", "pcm_s16le", str(cls.source)],
            input=frames.tobytes(), check=True, creationflags=NO_WINDOW)
        cls.info = probe(cls.source)
        cls.video = next(s for s in cls.info["streams"] if s["codec_type"] == "video")

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_decode_keeps_selected_frames_and_seek_matches_across_cut(self):
        timeline = SourceTimeline(8, normalize(dict(source_offset=.3, source_end=7.5,
            source_skip=[[2.13, 3.76], [5.2, 5.91]], playback_rate=1.02931464386368)))

        def decode(start, seconds):
            commands = []
            with (self.folder/"decode.log").open("wb") as log:
                return np.stack(list(decoded_frames(self.source, self.video, self.info["format"],
                    video_windows(timeline, start, seconds, 30), timeline.rate, 30, 32, 32, log, commands)))

        full = decode(0, timeline.duration)
        preview = decode(1, 3)
        np.testing.assert_array_equal(preview, full[30:120])
        values = full[:, 0, 0, 0]
        self.assertEqual(len(full), math.ceil(timeline.duration*30-1e-6))
        self.assertTrue(np.all((values < math.ceil(2.13*24)) | (values >= math.floor(3.76*24))))
        self.assertLessEqual(abs(int(values[-1])-7.5*24), 2)

    def test_audio_joins_kept_speech_and_delay_is_not_repeated_at_each_join(self):
        timeline = SourceTimeline(8, normalize(dict(source_offset=2, source_end=7,
                                                   source_skip=[[3, 4], [5, 6]])))
        seek, filters = edited_audio_window(timeline, 0, 3, 50)
        raw = subprocess.check_output([self.ffmpeg, "-v", "error", "-f", "lavfi", "-i", "color=s=32x32",
            "-ss", str(seek), "-i", str(self.source), "-filter_complex", filters, "-map", "[audio]",
            "-t", "3", "-ar", "48000", "-ac", "1", "-f", "f32le", "pipe:1"], creationflags=NO_WINDOW)
        samples = np.frombuffer(raw, "<f4")
        self.assertEqual(len(samples), 3*48000)
        self.assertLess(np.max(np.abs(samples[:2000])), .001)
        for position, expected in ((.3, 600), (1.3, 1000), (2.3, 1400)):
            section = samples[round(position*48000):round((position+.2)*48000)]
            frequency = np.argmax(np.abs(np.fft.rfft(section)))*48000/len(section)
            self.assertAlmostEqual(frequency, expected, delta=5)
        seek, filters = edited_audio_window(timeline, .8, 1.5, 50)
        self.assertAlmostEqual(seek, 2.75)
        self.assertNotIn("adelay", filters)
        self.assertEqual(filters.count("concat="), 1)
        self.assertEqual(filters.count("atempo="), 1)

    def test_short_window_with_delay_and_negative_delay_stays_within_selected_source(self):
        timeline = SourceTimeline(8, normalize(dict(source_offset=2, source_end=4, playback_rate=1.5)))
        for position, seconds, delay in ((0, .02, 50), (.5, .5, -50), (.5, .5, 50)):
            with self.subTest(position=position, delay=delay):
                seek, filters = edited_audio_window(timeline, position, seconds, delay)
                raw = subprocess.check_output([self.ffmpeg, "-v", "error", "-f", "lavfi", "-i", "color=s=32x32",
                    "-ss", str(seek), "-i", str(self.source), "-filter_complex", filters, "-map", "[audio]",
                    "-t", str(seconds), "-ar", "48000", "-ac", "1", "-f", "f32le", "pipe:1"],
                    creationflags=NO_WINDOW, timeout=15)
                self.assertAlmostEqual(len(raw)/4/48000, seconds, delta=1/48000)
                if seconds < .05:
                    self.assertLess(np.max(np.abs(np.frombuffer(raw, "<f4"))), .001)
