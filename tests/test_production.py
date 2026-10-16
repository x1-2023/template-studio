"""Kiểm tra preset, snapshot và phục hồi hàng đợi mà không cần cache/GPU trong CI."""

import copy
import tempfile
import unittest
from pathlib import Path

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication

from template_studio.presets import catalog, normalize
from template_studio.production import Production, fingerprint


class Host(QObject):
    changed = Signal()

    def __init__(self, home):
        super().__init__()
        self.root = Path.cwd()
        self.home = home
        self.pool = None
        self._rows = []
        self.output = str(home / "exports")
        self.busy = False

    def message(self, text):
        self.notice = text


class PresetTests(unittest.TestCase):
    def test_production_defaults_are_not_reference_speed(self):
        items = catalog()
        self.assertFalse(items[0]["config"]["flip"])
        self.assertEqual(items[0]["config"]["playback_rate"], 1)
        self.assertEqual(items[-1]["config"]["playback_rate"], 1.02)

    def test_rejects_unknown_fields_code_and_nonfinite(self):
        for config in (
            {"command": "powershell"},
            {"bokeh_size": float("nan")},
            {"skin": "model"},
            {"offset": [float("inf"), 0]},
            {"width": 720},
        ):
            with self.subTest(config=config), self.assertRaises(ValueError):
                normalize(config)

    def test_system_presets_are_independent(self):
        a = catalog()
        a[0]["config"]["offset"][0] = 0.2
        self.assertEqual(catalog()[0]["config"]["offset"][0], 0)


class QueueTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_changes_only_update_pending_and_completed_survive_restart(self):
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder)
            source = home / "nguồn.mp4"
            source.write_bytes(b"source")
            host = Host(home)
            p = Production(host)
            config = copy.deepcopy(p.config)
            p._rows = [
                dict(
                    id="done",
                    path=str(source),
                    name=source.name,
                    status="Hoàn tất",
                    percent=100,
                    detail="",
                    result="old.mp4",
                    duration=3,
                    meta="",
                    config=config,
                    presetName="Mẫu cũ",
                ),
                dict(
                    id="pending",
                    path=str(source),
                    name=source.name,
                    status="Chờ xử lý",
                    percent=0,
                    detail="",
                    result="",
                    duration=3,
                    meta="",
                    config=copy.deepcopy(config),
                    presetName="Mẫu cũ",
                ),
            ]
            p.choosePreset("pentagon-9x16")
            self.assertEqual(p._rows[0]["config"]["height"], 1440)
            self.assertEqual(p._rows[1]["config"]["height"], 1920)
            p._rows[1]["status"] = "Đang xuất"
            p.save()
            recovered = Production(Host(home))
            self.assertEqual(recovered._rows[0]["status"], "Hoàn tất")
            self.assertEqual(recovered._rows[1]["status"], "Đã dừng")
            self.assertEqual(recovered._rows[0]["result"], "old.mp4")

    def test_migrates_legacy_without_overwriting_source_session(self):
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder)
            original = '{"settings":{}}'
            (home / "session.json").write_text(original)
            host = Host(home)
            host._rows = [
                dict(path="x.mp4", name="x.mp4", status="Hoàn tất", result="done.mp4")
            ]
            p = Production(host)
            self.assertEqual(p._rows[0]["status"], "Hoàn tất")
            self.assertEqual((home / "session-before-1.1.json").read_text(), original)
            self.assertEqual((home / "session.json").read_text(), original)

    def test_fingerprint_detects_config_or_source_change(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "source.mp4"
            source.write_bytes(b"abc")
            first = fingerprint(source, normalize({}))
            self.assertNotEqual(first, fingerprint(source, normalize({"flip": True})))
            source.write_bytes(b"changed")
            self.assertNotEqual(first, fingerprint(source, normalize({})))
