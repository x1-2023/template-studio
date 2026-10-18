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
        self.assertEqual(karaoke["config"]["part_count"], 0)
        self.assertEqual(karaoke["config"]["part_seconds"], 180)
        self.assertEqual(karaoke["config"]["effect_loop_seconds"], 0)
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
        self.assertAlmostEqual(catalog()[0]["config"]["offset"][0], -0.047318612)


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

    def test_preview_uses_correct_part_badge_and_stops_at_part_boundary(self):
        from template_studio.parts import plan_parts
        from unittest.mock import Mock
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder)
            host = Host(home)
            host.mediaReady, host._nvenc = True, True
            p = Production(host)
            p._ready, p._cache = True, "cache"
            p._config = next(item["config"] for item in catalog() if item["id"]=="karaoke-1012")
            p._config.update(part_count=3,playback_rate=1)
            p._rows = [dict(path="video.mp4",duration=9)]
            p._index = 0
            p.pool = Mock()
            p.pool.submit.side_effect = lambda work,**kwargs:work(lambda event:None)
            requests = []
            def worker(root,home,request,progress):
                requests.append(request)
                return dict(output=request["output"])
            with patch("template_studio.production.prepare_captions",side_effect=lambda root,home,src,config,notice:config), patch("template_studio.production.run_worker",side_effect=worker), patch("template_studio.production.plan_source_parts",side_effect=lambda source,config:plan_parts(9,config)):
                p.preview(4)
                p.preview(2.9)
            self.assertEqual(requests[0]["config"]["subtitle_part_label"],"PART 2")
            self.assertEqual(requests[0]["seconds"],2)
            self.assertEqual(requests[0]["effect_offset"],3)
            self.assertEqual(requests[1]["config"]["subtitle_part_label"],"PART 1")
            self.assertAlmostEqual(requests[1]["seconds"],.1)

    def test_auto_preview_resets_intro_at_the_actual_part_start(self):
        from template_studio.parts import plan_parts
        from unittest.mock import Mock
        with tempfile.TemporaryDirectory() as folder:
            host = Host(Path(folder))
            host.mediaReady, host._nvenc = True, True
            p = Production(host)
            p._ready, p._cache = True, "cache"
            p._config = normalize(dict(part_count=0,part_seconds=180))
            p._rows = [dict(path="video.mp4",duration=400)]
            p._index = 0
            p.pool = Mock()
            p.pool.submit.side_effect = lambda work,**kwargs:work(lambda event:None)
            with patch("template_studio.production.run_worker",return_value=dict(output="x.mp4")) as worker, patch("template_studio.production.plan_source_parts",side_effect=lambda source,config:plan_parts(400,config)):
                p.preview(358)
            job = worker.call_args.args[2]
            self.assertEqual(job["config"]["subtitle_part_label"],"PART 2")
            self.assertEqual(job["effect_offset"],180)
            self.assertEqual(job["part_range"],[180,360])
            self.assertEqual(job["seconds"],2)

    def test_real_121_queue_is_migrated_backed_up_and_can_export_without_reselecting_preset(self):
        from unittest.mock import Mock
        legacy = json.loads((Path(__file__).parent/"fixtures/preset-1.2.1.json").read_text(encoding="utf-8"))
        self.assertNotIn("part_count", legacy)
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder).resolve()
            source = home/"nguồn.mp4"
            source.write_bytes(b"source")
            previous = home/"old.mp4"
            previous.write_bytes(b"previous-video")
            saved = dict(schema=1, production_defaults="tiktok", config=legacy, preset="pentagon-9x16",
                         output=str(home/"exports"), custom=[dict(id="custom-old",name="Mẫu riêng",config=legacy)], rows=[
                dict(id=str(i),path=str(source),name=source.name,status=status,percent=100 if i else 0,
                     detail="",result=str(previous) if i else "",duration=3,meta="",config=legacy,presetName="Mẫu cũ")
                for i,status in enumerate(("Chờ xử lý","Hoàn tất"))
            ])
            original = json.dumps(saved,ensure_ascii=False)
            (home/"production.json").write_text(original,encoding="utf-8")
            host = Host(home)
            host.mediaReady, host._nvenc, host._closing = True, True, False
            p = Production(host)
            self.assertEqual((home/"production-before-karaoke.json").read_text(encoding="utf-8"),original)
            for config in [p.config,p._custom[0]["config"],*(row["config"] for row in p._rows)]:
                self.assertEqual(config["part_count"],1)
                self.assertEqual(config["subtitle_mode"],"off")
                self.assertEqual({key:config[key] for key in legacy},legacy)
            p._ready,p._cache = True,"cache"
            p.pool = Mock()
            def submit(work,result,error,event,finished):
                result(work(event))
                finished()
            p.pool.submit.side_effect = submit
            def worker(root,home,request,progress):
                self.assertEqual(request["config"]["part_count"],1)
                self.assertEqual(request["config"]["subtitle_mode"],"off")
                Path(request["output"]).write_bytes(b"new-video")
                return dict(wall_seconds=1)
            with patch("template_studio.production.run_worker",side_effect=worker) as run:
                p.runBatch()
            self.assertEqual(run.call_count,1)
            self.assertTrue(all(row["status"]=="Hoàn tất" for row in p._rows))
            self.assertEqual(previous.read_bytes(),b"previous-video")
            Production(Host(home))
            self.assertEqual((home/"production-before-karaoke.json").read_text(encoding="utf-8"),original)
