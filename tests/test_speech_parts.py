"""Kiểm tra tải ASR, cache nguồn và sổ chia phần khi phải thử lại."""

import hashlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from template_studio.parts import plan_parts, render_parts
from template_studio.presets import catalog, normalize
from template_studio.speech import _download, parse_whisper, prepare_captions


class SpeechTests(unittest.TestCase):
    def test_download_checks_hash_before_replacing_existing_runtime(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder)/"model.bin"
            target.write_bytes(b"old")
            with patch("urllib.request.urlopen", return_value=io.BytesIO(b"new")):
                with self.assertRaisesRegex(ValueError, "Checksum"):
                    _download("https://example.com/model", target, "invalid", 10, lambda event: None)
            self.assertEqual(target.read_bytes(), b"old")
            self.assertEqual(list(Path(folder).iterdir()), [target])
            with patch("urllib.request.urlopen", return_value=io.BytesIO(b"new")):
                _download("https://example.com/model", target, hashlib.sha256(b"new").hexdigest(), 10, lambda event: None)
            self.assertEqual(target.read_bytes(), b"new")

    def test_auto_caption_cache_is_shared_and_invalidated_when_source_changes(self):
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder)
            source = home/"video.mp4"
            source.write_bytes(b"old")
            config = normalize(dict(subtitle_mode="auto"))
            with patch("template_studio.worker_client.run_worker", return_value=dict(words=[dict(text="CHÀO",start=0,end=1)])) as worker:
                first = prepare_captions(home, home, source, config, lambda text: None)
                self.assertEqual(prepare_captions(home, home, source, config, lambda text: None), first)
                self.assertEqual(worker.call_count, 1)
                source.write_bytes(b"changed")
                second = prepare_captions(home, home, source, config, lambda text: None)
                self.assertEqual(worker.call_count, 2)
                self.assertNotEqual(first["subtitle_file"], second["subtitle_file"])
            self.assertEqual(config["subtitle_mode"], "auto")

    def test_whisper_timestamps_use_milliseconds_and_drop_special_tokens(self):
        words = parse_whisper(dict(transcription=[
            dict(text=" CHÀO", offsets={"from":200,"to":650}),
            dict(text="[_BEG_]", offsets={"from":0,"to":100}),
        ]))
        self.assertEqual(words, [dict(text="CHÀO",start=.2,end=.65)])

    def test_standalone_asr_worker_uses_data_home_without_environment_override(self):
        from template_studio.worker import execute
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ):
            os.environ.pop("TEMPLATE_STUDIO_HOME", None)
            with patch("template_studio.paths.data_home",return_value=Path(folder)), patch("template_studio.speech.transcribe",return_value=dict(words=[])) as transcribe:
                emit = lambda event: None
                self.assertEqual(execute(dict(action="transcribe",source="video.mp4"),emit,Path(folder)),dict(words=[]))
            self.assertEqual(transcribe.call_args.args[1],Path(folder))


class PartTests(unittest.TestCase):
    def test_part_boundaries_share_one_output_timeline_at_nonunit_speed(self):
        config = normalize(dict(part_count=3,playback_rate=1.02,source_offset=1.3))
        parts = plan_parts(10, config)
        self.assertAlmostEqual(sum(p["seconds"] for p in parts), (10-1.3)/1.02)
        for left, right in zip(parts, parts[1:]):
            self.assertAlmostEqual(left["start"]+left["seconds"], right["start"])
        self.assertAlmostEqual(parts[1]["start"]*30, round(parts[1]["start"]*30))

    def test_retry_keeps_verified_parts_and_renders_only_remaining_outputs(self):
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder)
            source = home/"nguồn.mp4"
            source.write_bytes(b"source")
            output = home/"exports"
            output.mkdir()
            config = next(p["config"] for p in catalog() if p["id"]=="karaoke-1012")
            config.update(subtitle_mode="off")
            calls = []

            def metadata(path):
                duration = 9 if Path(path)==source else 3
                return dict(format=dict(duration=str(duration)), streams=[
                    dict(codec_type="video",codec_name="h264",width=1080,height=1440,duration=str(duration),r_frame_rate="30/1"),
                    dict(codec_type="audio"),
                ])

            def request(src, target, settings, offset=0):
                return dict(output=str(target), config=settings, offset=offset)

            def worker(root, home, job, progress):
                calls.append(job)
                if len(calls)==2:
                    raise RuntimeError("Lỗi phần 2")
                Path(job["output"]).write_bytes(b"video")

            with patch("template_studio.parts.probe", side_effect=metadata), patch("template_studio.parts.run_worker", side_effect=worker):
                with self.assertRaisesRegex(RuntimeError, "phần 2"):
                    render_parts(home,home,"row",source,config,output,request,lambda event:None,lambda paths:None)
                first = next(output.glob("*.mp4"))
                stamp = first.stat().st_mtime_ns
                result = render_parts(home,home,"row",source,config,output,request,lambda event:None,lambda paths:None)
            self.assertEqual(len(calls), 4)
            self.assertEqual(len(result["parts"]), 3)
            self.assertEqual(first.stat().st_mtime_ns, stamp)
            self.assertEqual(len(list(output.glob("*.mp4"))), 3)
            self.assertEqual(source.read_bytes(), b"source")
            journal = json.loads(next((home/"cache/parts").glob("*.json")).read_text(encoding="utf-8"))
            self.assertTrue(all(p["status"]=="done" for p in journal["parts"]))
