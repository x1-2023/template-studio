"""Kiểm tra engine thực và đầu ra video có âm thanh, giới hạn thời gian, hủy tác vụ."""
import hashlib
import os
import subprocess
import tempfile
import threading
import unittest
from pathlib import Path

import numpy as np

from offline_studio.cancellation import TaskCancelled, cancellation_scope
from offline_studio.process import binary
from template_studio.effects import FrameProcessor, catalog
from template_studio.render import metadata, normalize, render


class EngineTests(unittest.TestCase):
    def test_all_catalog_entries_produce_valid_frames(self):
        frame = np.random.default_rng(2026).integers(0, 255, (128, 72, 4), dtype=np.uint8)
        frame[:, :, 3] = 255
        self.assertEqual(len(catalog()), 151)
        for entry in catalog():
            with self.subTest(effect=entry['id']):
                processor = FrameProcessor(entry['id'], .65)
                for index in (0, 7, 15):
                    output = processor.process(frame.copy(), index, 90)
                    self.assertEqual(output.shape, frame.shape)
                    self.assertEqual(output.dtype, np.uint8)

    def test_normalize_rejects_unknown_or_nonfinite_parameters(self):
        for settings in ({'effect': 'external-command'}, {'effectIntensity': float('nan')}, {'speed': float('inf')}):
            with self.subTest(settings=settings), self.assertRaises(ValueError):
                normalize(settings)

    def test_zero_intensity_is_identity(self):
        frame = np.random.default_rng(9).integers(0, 255, (48, 32, 4), dtype=np.uint8)
        output = FrameProcessor('rgb_split', 0).process(frame.copy(), 0, 10)
        np.testing.assert_array_equal(frame, output)


class RenderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.folder = Path(cls.temporary.name)
        cls.source = cls.folder / 'video có dấu.mp4'
        subprocess.run([binary('ffmpeg'), '-v', 'error', '-f', 'lavfi', '-i', 'testsrc2=size=180x320:rate=30:duration=2',
                        '-f', 'lavfi', '-i', 'sine=frequency=440:duration=2', '-shortest',
                        '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-c:a', 'aac', str(cls.source)],
                       check=True, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        cls.source_hash = hashlib.sha256(cls.source.read_bytes()).hexdigest()

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def test_filter_video_keeps_audio_duration_and_source(self):
        destination = self.folder / 'filter-speed.mp4'
        result = render(self.source, destination, dict(effect='teal_and_orange', speed=1.5), preview=True)
        info = metadata(destination)
        self.assertTrue(info['audio'])
        self.assertEqual((info['width'], info['height']), (360, 640))
        self.assertAlmostEqual(info['duration'], 2 / 1.5, delta=.1)
        self.assertAlmostEqual(result['duration'], 2 / 1.5, delta=.01)
        self.assertEqual(hashlib.sha256(self.source.read_bytes()).hexdigest(), self.source_hash)

    def test_muted_offset_and_full_resolution(self):
        destination = self.folder / 'filter-muted.mp4'
        render(self.source, destination, dict(effect='rgb_split', mute=True, resolution=720), offset=.5)
        info = metadata(destination)
        self.assertFalse(info['audio'])
        self.assertEqual((info['width'], info['height']), (720, 1280))
        self.assertAlmostEqual(info['duration'], 1.5, delta=.1)

    def test_effect_duration_stops_filter(self):
        control, filtered = self.folder / 'control.mp4', self.folder / 'duration.mp4'
        render(self.source, control, dict(intro=0, strength=0), preview=True)
        render(self.source, filtered, dict(intro=0, strength=0, effect='rgb_split', effectIntensity=100, effectDuration=.5), preview=True)
        def frame(file, offset):
            raw = subprocess.check_output([binary('ffmpeg'), '-v', 'error', '-ss', str(offset), '-i', str(file),
                                           '-frames:v', '1', '-f', 'rawvideo', '-pix_fmt', 'rgb24', 'pipe:1'],
                                          creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            return np.frombuffer(raw, dtype=np.uint8).astype(np.float32)
        early = np.mean(np.abs(frame(filtered, .1) - frame(control, .1)))
        later = np.mean(np.abs(frame(filtered, 1) - frame(control, 1)))
        self.assertGreater(early, 2)
        # Nhánh filter chuyển thêm YUV/RGBA, nên cho phép sai số codec nhỏ.
        self.assertLess(later, 3)
        self.assertLess(later, early / 2)

    def test_cancel_cleans_partial_files(self):
        destination = self.folder / 'cancelled.mp4'
        cancel = threading.Event()
        with cancellation_scope(cancel), self.assertRaises(TaskCancelled):
            render(self.source, destination, dict(effect='film_grain'), preview=True,
                   progress=lambda percent: cancel.set())
        self.assertFalse(destination.exists())
        self.assertFalse(list(self.folder.glob('*.part.mp4')))
        self.assertFalse(list(self.folder.glob('.glass-*.png')))
