"""Kiểm tra preset, snapshot và phục hồi hàng đợi mà không cần cache/GPU trong CI."""

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication

from template_studio.presets import DEFAULT_PRESET_ID, catalog, main_catalog, normalize
from template_studio.production import Production, fingerprint
from template_studio.worker_client import WorkerError


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
        items = main_catalog()
        self.assertEqual(items[0]["id"], DEFAULT_PRESET_ID)
        for item in items[:3]:
            self.assertEqual((item["config"]["width"], item["config"]["height"]), (1080, 1920))
        karaoke = next(item for item in items if item["id"] == "karaoke-1012")
        self.assertEqual(karaoke["config"]["height"], 1440)
        self.assertEqual(karaoke["config"]["subtitle_mode"], "auto")
        self.assertEqual(karaoke["config"]["part_count"], 3)
        self.assertTrue(items[0]["config"]["intro_enabled"])
        self.assertTrue(items[0]["config"]["filter_enabled"])
        self.assertFalse(items[0]["config"]["flip"])
        self.assertEqual(items[0]["config"]["playback_rate"], 1)
        self.assertEqual(catalog()[-1]["config"]["playback_rate"], 1.02)

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
            config = normalize({})
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

    def test_tiktok_migration_preserves_settings_custom_presets_and_completed_jobs(self):
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder)
            source = home / "nguồn.mp4"
            source.write_bytes(b"source")
            old = normalize(dict(flip=True, playback_rate=1.02, sharpness=0.35, mute=True))
            pending = normalize({**old, "playback_rate": 1.15, "offset": [0.12, 0]})
            p = Production(Host(home))
            p._preset = "reference"
            p._config = copy.deepcopy(old)
            p._custom = [dict(id="custom-test", name="Mẫu riêng", description="", custom=True, config=copy.deepcopy(old))]
            p._rows = [
                dict(id=slug, path=str(source), name=source.name, status=status,
                     percent=100 if status=="Hoàn tất" else 0, detail="", result="old.mp4" if status=="Hoàn tất" else "",
                     duration=3, meta="", config=copy.deepcopy(config), presetName="Theo video mẫu CapCut · 3:4")
                for slug, status, config in (("done", "Hoàn tất", old), ("pending", "Chờ xử lý", pending))
            ]
            p._rows[0]["path"] = str(home / "nguồn đã dời.mp4")
            p.save()
            saved = json.loads(p._state.read_text(encoding="utf-8"))
            saved.pop("production_defaults")
            original = json.dumps(saved, ensure_ascii=False)
            p._state.write_text(original, encoding="utf-8")
            migrated = Production(Host(home))
            self.assertEqual(migrated.presetId, DEFAULT_PRESET_ID)
            self.assertEqual(migrated.config, {**old, "height": 1920})
            self.assertEqual(migrated._rows[0]["config"], old)
            self.assertEqual(migrated._rows[0]["status"], "Hoàn tất")
            self.assertEqual(migrated._rows[0]["result"], "old.mp4")
            self.assertEqual(migrated._rows[1]["config"], {**pending, "height": 1920})
            self.assertEqual(migrated._custom[0]["config"], old)
            self.assertEqual((home / "production-before-tiktok.json").read_text(encoding="utf-8"), original)
            # Sau khi chuyển một lần, vẫn mở lại được cấu hình đối chiếu 3:4 do người dùng chọn.
            migrated.choosePreset("reference")
            restored = Production(Host(home))
            self.assertEqual(restored.presetId, "reference")
            self.assertEqual(restored.config["height"], 1440)

    def test_fingerprint_detects_config_or_source_change(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "source.mp4"
            source.write_bytes(b"abc")
            first = fingerprint(source, normalize({}))
            self.assertNotEqual(first, fingerprint(source, normalize({"flip": True})))
            source.write_bytes(b"changed")
            self.assertNotEqual(first, fingerprint(source, normalize({})))

    def test_batch_continues_after_error_and_keeps_reports_outside_exports(self):
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder)
            source = home / "nguồn.mp4"
            source.write_bytes(b"source")
            host = Host(home)
            host.mediaReady, host._nvenc, host._closing = True, True, False
            p = Production(host)
            p._ready, p._cache = True, "cache"
            p._rows = [dict(
                id=str(n), path=str(source), name=source.name, status="Chờ xử lý",
                percent=0, detail="", result="", duration=3, meta="",
                config=normalize({}), presetName="Mẫu",
            ) for n in range(2)]
            p._index = 0
            log = home / "cache/workers/first/worker.log"
            log.parent.mkdir(parents=True)
            log.write_text("traceback")
            calls = []

            def worker(root, home, request, progress):
                calls.append(request)
                if len(calls) == 1:
                    raise WorkerError("Lỗi gốc\nChi tiết dài", log.parent)
                Path(request["output"]).write_bytes(b"video")
                return dict(wall_seconds=1)

            def submit(work, result, error, event, finished):
                result(work(event))
                finished()

            from unittest.mock import Mock
            p.pool = Mock()
            p.pool.submit.side_effect = submit
            with patch("template_studio.production.run_worker", side_effect=worker):
                p.runBatch()
            self.assertEqual(len(calls), 2)
            self.assertEqual([r["status"] for r in p._rows], ["Lỗi", "Hoàn tất"])
            self.assertEqual(p._rows[0]["detail"], "Lỗi gốc")
            self.assertEqual(p._rows[0]["errorLog"], str(log))
            self.assertEqual([file.suffix for file in (home / "exports").iterdir()], [".mp4"])
            self.assertEqual(len(list((home / "cache/workers/batches").glob("*.json"))), 1)
            self.assertEqual(len(list((home / "cache/workers/batches").glob("*.csv"))), 1)
            with patch("template_studio.production.QDesktopServices.openUrl") as opened:
                p.openErrorLog()
            self.assertEqual(opened.call_args.args[0].toLocalFile(), str(log).replace("\\", "/"))
