"""Kiểm tra tải ASR, cache nguồn và sổ chia phần khi phải thử lại."""

import hashlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from template_studio.parts import plan_parts, plan_source_parts, render_parts
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
    def test_auto_parts_use_caption_pause_and_preserve_entire_video(self):
        config = normalize(dict(part_count=0, part_seconds=180, playback_rate=1.02931464386368))
        words = [dict(text="FINISH.", start=184*config["playback_rate"], end=185.9*config["playback_rate"]),
                 dict(text="NEXT", start=186.1*config["playback_rate"], end=187*config["playback_rate"])]
        parts = plan_parts(366.9*config["playback_rate"], config, words)
        self.assertEqual(len(parts), 2)
        self.assertAlmostEqual(parts[1]["start"], 185.9)
        self.assertAlmostEqual(sum(x["seconds"] for x in parts), 366.9)
        self.assertAlmostEqual(parts[0]["start"]+parts[0]["seconds"], parts[1]["start"])

    def test_auto_parts_map_source_offset_and_rate_once(self):
        config = normalize(dict(part_count=0,part_seconds=30,source_offset=2,playback_rate=1.5))
        parts = plan_parts(122,config,[dict(text="END.",start=44,end=48.5),dict(text="NEXT",start=50,end=51)])
        self.assertAlmostEqual(parts[1]["start"],31)
        self.assertAlmostEqual(sum(p["seconds"] for p in parts),80)

    def test_auto_without_words_and_short_video(self):
        config = normalize(dict(part_count=0,part_seconds=180))
        self.assertEqual(len(plan_parts(90,config)),1)
        self.assertEqual([p["start"] for p in plan_parts(509,config)],[0,180,360])
        for duration in (0,float("nan"),float("inf")):
            with self.assertRaises(ValueError):
                plan_parts(duration,config)

    def test_auto_does_not_cut_mid_word_and_avoids_tiny_final_part(self):
        config = normalize(dict(part_count=0,part_seconds=180))
        parts = plan_parts(367,config,[dict(text="LONG",start=179,end=181)])
        self.assertEqual(parts[1]["start"],181)
        self.assertEqual(len(plan_parts(185,config)),1)

    def test_two_equal_parts_remain_available(self):
        self.assertEqual(plan_parts(10,normalize(dict(part_count=2))),
                         [dict(start=0,seconds=5),dict(start=5,seconds=5)])

    def test_sidecar_guides_auto_cuts_using_video_not_audio_duration(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder)/"video.mp4"
            caption = source.with_suffix(".words.json")
            caption.write_text(json.dumps([dict(text="END.",start=178,end=183),dict(text="NEXT",start=184,end=185)]))
            config = normalize(dict(part_count=0,subtitle_mode="sidecar"))
            metadata = dict(format=dict(duration="401"),streams=[dict(codec_type="video",duration="400")])
            parts = plan_source_parts(source,config,metadata)
            self.assertEqual(parts[1]["start"],183)
            self.assertAlmostEqual(sum(p["seconds"] for p in parts),400)

    def test_part_boundaries_share_one_output_timeline_at_nonunit_speed(self):
        config = normalize(dict(part_count=3,playback_rate=1.02,source_offset=1.3))
        parts = plan_parts(10, config)
        self.assertAlmostEqual(sum(p["seconds"] for p in parts), (10-1.3)/1.02)
        for left, right in zip(parts, parts[1:]):
            self.assertAlmostEqual(left["start"]+left["seconds"], right["start"])
        self.assertAlmostEqual(parts[1]["start"]*30, round(parts[1]["start"]*30))

    def test_retry_keeps_verified_parts_and_renders_only_remaining_outputs(self):
        with tempfile.TemporaryDirectory() as folder:
            # TEMP của Windows runner có thể dùng bí danh RUNNER~1.
            home = Path(folder).resolve()
            source = home/"nguồn.mp4"
            source.write_bytes(b"source")
            output = home/"exports"
            output.mkdir()
            config = next(p["config"] for p in catalog() if p["id"]=="karaoke-1012")
            config.update(subtitle_mode="off", part_count=3, playback_rate=1)
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
            self.assertEqual([c["effect_offset"] for c in calls], [0,3,3,6])
            self.assertEqual(len(result["parts"]), 3)
            self.assertEqual(first.stat().st_mtime_ns, stamp)
            self.assertEqual(len(list(output.glob("*.mp4"))), 3)
            self.assertEqual(source.read_bytes(), b"source")
            journal = json.loads(next((home/"cache/parts").glob("*.json")).read_text(encoding="utf-8"))
            self.assertTrue(all(p["status"]=="done" for p in journal["parts"]))
