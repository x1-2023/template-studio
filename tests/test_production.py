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

    def test_part_count_and_colors_are_validated_and_old_configs_get_defaults(self):
        config=normalize(dict(part_count=17,subtitle_color="#12abEF",subtitle_red="eF3412"))
        self.assertEqual(config["subtitle_color"],"12ABEF")
        self.assertEqual(config["subtitle_red"],"EF3412")
        self.assertEqual(normalize({})["title_background"],"A20033")
        self.assertIs(type(normalize(dict(part_count=5.0))["part_count"]),int)
        for value in (-1,101,2.5,True):
            with self.subTest(count=value),self.assertRaises(ValueError):
                normalize(dict(part_count=value))
        for key in ("subtitle_red","subtitle_color","subtitle_outline","title_color","title_background","part_color","part_background"):
            with self.subTest(key=key),self.assertRaises(ValueError):
                normalize({key:"#GG0000"})

    def test_old_shared_colors_migrate_and_part_can_be_changed_independently(self):
        old=normalize(dict(title_color="#12ab34",title_background="#324abc"))
        self.assertEqual(old['part_color'],'12AB34')
        self.assertEqual(old['part_background'],'324ABC')
        separate=normalize(dict(old,part_color='FF0000',part_background='FFFF00'))
        self.assertEqual(separate['title_color'],'12AB34')
        self.assertEqual(separate['title_background'],'324ABC')
        self.assertEqual(separate['part_color'],'FF0000')
        self.assertEqual(separate['part_background'],'FFFF00')

    def test_optional_seconds_per_fixed_part_defaults_to_equal_split_and_validates(self):
        self.assertEqual(normalize({})['part_fixed_seconds'], 0)
        self.assertEqual(normalize(dict(part_count=3,part_fixed_seconds=180))['part_fixed_seconds'], 180)
        for seconds in (-1, .5, 1801, float('nan'), float('inf')):
            with self.subTest(seconds=seconds), self.assertRaises(ValueError):
                normalize(dict(part_fixed_seconds=seconds))
        with self.assertRaises(ValueError):
            normalize(dict(part_remainder='unknown'))


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

    def test_source_ranges_parse_save_per_video_and_survive_preset_changes_and_restart(self):
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder)
            source = home/"nguồn.mp4"
            source.write_bytes(b"video")
            host = Host(home)
            p = Production(host)
            p._rows = [dict(id=str(i), path=str(source), name=source.name, duration=1200, status="Chờ xử lý",
                percent=0, detail="", result="", config=copy.deepcopy(p.config), presetName=p.presetName) for i in range(2)]
            p._index = 0
            value = p.parseSourceRange("01:00", "10:00", "02:00 - 02:30\n02:20 - 02:40")
            self.assertEqual(value, dict(source_offset=60, source_end=600, source_skip=[[120, 160]]))
            self.assertIn("error", p.parseSourceRange("1:99", "", ""))
            self.assertIn("error", p.parseSourceRange("0", "", "2:00"))
            self.assertTrue(p.applySourceRange(0, value, True))
            self.assertAlmostEqual(p.previewDuration, 500)
            signature = p.preview_signature()
            p.choosePreset("karaoke-1012")
            self.assertEqual(p._rows[0]["config"]["source_end"], 600)
            self.assertEqual(p._rows[1]["config"]["source_end"], 0)
            self.assertNotEqual(signature, p.preview_signature())
            host.busy = True
            self.assertFalse(p.applySourceRange(0, {}, False))
            host.busy = False
            self.assertFalse(p.applySourceRange(0, dict(source_offset=1300, source_end=0, source_skip=[]), True))
            restored = Production(Host(home))
            self.assertTrue(restored._rows[0]["sourceRangeCustom"])
            self.assertEqual(restored._rows[0]["config"]["source_skip"], [[120, 160]])
            restored._rows[0]["status"] = "Lỗi"
            restored.retrySelected()
            self.assertEqual(restored._rows[0]["config"]["source_end"], 600)
            self.assertTrue(restored.applySourceRange(0, {}, False))
            self.assertFalse(restored._rows[0]["sourceRangeCustom"])
            self.assertEqual(restored._rows[0]["config"]["source_end"], 0)

    def test_preview_uses_video_specific_range_and_rejects_outside_before_transcribing(self):
        from unittest.mock import Mock
        with tempfile.TemporaryDirectory() as folder:
            host = Host(Path(folder))
            host.mediaReady, host._nvenc = True, True
            p = Production(host)
            p._ready, p._cache = True, "cache"
            selected = normalize(dict(source_offset=60, source_end=600, source_skip=[[120, 160]], part_count=1))
            p._rows = [dict(path="video.mp4", duration=1200, config=selected)]
            p._index = 0
            p.pool = Mock()
            p.pool.submit.side_effect = lambda work, **kwargs: work(lambda event: None)
            with patch("template_studio.production.run_worker", return_value=dict(output="x.mp4")) as worker:
                p.preview(65)
                self.assertEqual(worker.call_args.args[2]["config"], selected)
                self.assertEqual(worker.call_args.args[2]["offset"], 65)
            host.busy = False
            with patch("template_studio.production.prepare_captions") as transcribe, self.assertRaises(ValueError):
                p.preview(501)
            transcribe.assert_not_called()

    def test_fixed_seconds_caps_preview_and_estimate_and_describes_both_remainder_options(self):
        from unittest.mock import Mock
        with tempfile.TemporaryDirectory() as folder:
            host = Host(Path(folder))
            host.mediaReady,host._nvenc = True,True
            p = Production(host)
            p._ready,p._cache = True,'cache'
            config = normalize(dict(source_end=600,part_count=3,part_fixed_seconds=180))
            p._rows = [dict(path='video.mp4',duration=1200,config=config,status='Chờ xử lý')]
            p._index=0
            self.assertEqual(p.previewDuration,540)
            self.assertIn('03:00 / 03:00 / 03:00',p.partSummary(config,1200))
            self.assertIn('Không xuất 01:00',p.partSummary(config,1200))
            cropped_estimate=p.estimate
            config['part_remainder']='last'
            self.assertEqual(p.previewDuration,600)
            self.assertIn('03:00 / 03:00 / 04:00',p.partSummary(config,1200))
            self.assertNotEqual(p.estimate,cropped_estimate)
            config['part_remainder']='drop'
            p.pool=Mock()
            p.pool.submit.side_effect=lambda work,**kwargs:work(lambda event:None)
            with patch('template_studio.production.prepare_captions') as transcribe,self.assertRaisesRegex(ValueError,'sẽ xuất'):
                p.preview(550)
            transcribe.assert_not_called()

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

    def test_short_source_in_parts_mode_completes_when_only_one_part_fits(self):
        from unittest.mock import Mock
        with tempfile.TemporaryDirectory() as folder:
            home=Path(folder)
            source=home/'nguồn.mp4'
            source.write_bytes(b'source')
            host=Host(home)
            host.mediaReady,host._nvenc,host._closing=True,True,False
            p=Production(host)
            p._ready,p._cache=True,'cache'
            p._rows=[dict(id='row',path=str(source),name=source.name,status='Chờ xử lý',percent=0,
                detail='',result='',duration=55,meta='',presetName='Mẫu',
                config=normalize(dict(part_count=3,part_fixed_seconds=180)))]
            p.pool=Mock()
            def submit(work,result,error,event,finished):
                result(work(event))
                finished()
            p.pool.submit.side_effect=submit
            def render_parts(root,home,row_id,src,config,output,request,progress,completed):
                target=output/'nguồn_part1.mp4'
                target.write_bytes(b'video')
                return dict(output=str(target),parts=[str(target)],wall_seconds=1)
            with patch('template_studio.production.render_parts',side_effect=render_parts):
                p.runBatch()
            self.assertEqual(p._rows[0]['status'],'Hoàn tất')
            self.assertEqual(Path(p._rows[0]['result']).name,'nguồn_part1.mp4')

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
            p._rows = [dict(path="video.mp4",duration=9,config=copy.deepcopy(p._config))]
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
            p._rows = [dict(path="video.mp4",duration=400,config=copy.deepcopy(p._config))]
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
