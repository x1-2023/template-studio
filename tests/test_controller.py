"""Kiểm tra thao tác xem thử, áp dụng filter và lưu cấu hình của người dùng."""
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from PySide6.QtWidgets import QApplication
from template_studio.app import Controller


class ControllerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])

    def wait(self, controller):
        deadline = time.monotonic() + 10
        while controller.pool.active and time.monotonic() < deadline:
            self.application.processEvents()
            time.sleep(.01)
        self.assertFalse(controller.pool.active)

    def test_preview_draft_applies_atomically_and_persists(self):
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            with patch.dict(os.environ, {'TEMPLATE_STUDIO_HOME': str(home)}):
                controller = Controller(Path.cwd(), home)
                self.wait(controller)
                controller._rows = [dict(path='old.mp4', name='old.mp4', status='Hoàn tất', percent=100, result='previous-output.mp4')]
                controller.inspectEffect('rgb_split')
                controller.configureCandidate('effectIntensity', 42)
                controller.configureCandidate('effectDuration', 3)
                self.assertEqual(controller.settings['effect'], 'none')
                self.assertEqual(controller.settings['effectIntensity'], 65)
                controller.applyEffect()
                self.assertEqual(controller.settings['effect'], 'rgb_split')
                self.assertEqual(controller.settings['effectIntensity'], 42)
                self.assertEqual(controller.settings['effectDuration'], 3)
                self.assertEqual(controller.rows[0]['status'], 'Chờ xử lý')
                self.assertEqual(controller.rows[0]['result'], 'previous-output.mp4')
                loaded = Controller(Path.cwd(), home)
                self.wait(loaded)
                self.assertEqual(loaded.settings['effect'], 'rgb_split')
                self.assertEqual(loaded.settings['effectIntensity'], 42)
                self.assertEqual(loaded.settings['effectDuration'], 3)
