"""Thư mục xuất gọn và di chuyển đúng các file kỹ thuật đã nhận diện."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from template_studio.output_files import archive_output_artifacts, reports_directory


class OutputFilesTests(unittest.TestCase):
    def test_archives_known_sidecars_and_batch_reports_without_touching_user_files(self):
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder)
            output = home / "exports"
            output.mkdir()
            video = output / "Vídeo español !!!.mp4"
            video.write_bytes(b"video-goc")
            artifacts = {
                video.with_suffix(".render.json"): json.dumps(dict(output=str(video), gpu="RTX", frames=90, ffmpeg_encode=["ffmpeg"])),
                video.with_suffix(".decode.log"): "",
                video.with_suffix(".encode.log"): "nhat-ky",
                output / "bao-cao-20261016-224347-035441.json": json.dumps(dict(version="1.2.0", results=[])),
                output / "bao-cao-20261016-224347-035441.csv": "source,status\n",
            }
            untouched = {
                output / "ghi-chu.json": '{"version":"1.2.0","results":[]}',
                output / "tu-ghi.render.json": "{}",
                output / "tu-ghi.encode.log": "nhat-ky-rieng",
                output / "hong.render.json": json.dumps(dict(output="\u0000", gpu="RTX", frames=90, ffmpeg_encode=[])),
                output / "bao-cao-20261016-224347-ffffff.json": "{}",
            }
            for path, value in {**artifacts, **untouched}.items():
                path.write_text(value, encoding="utf-8")
            self.assertEqual(archive_output_artifacts(output, home), len(artifacts))
            self.assertEqual(video.read_bytes(), b"video-goc")
            for path, value in untouched.items():
                self.assertEqual(path.read_text(encoding="utf-8"), value)
            archived = home / "cache/workers/archived-exports"
            for path, value in artifacts.items():
                self.assertFalse(path.exists())
                self.assertEqual(next(archived.glob("*/" + path.name)).read_text(encoding="utf-8"), value)
            self.assertEqual(archive_output_artifacts(output, home), 0)

    def test_failed_job_logs_are_recognized_from_request_and_locked_files_stay(self):
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder)
            output = home / "exports"
            output.mkdir()
            video = output / "bi-loi.mp4"
            log = video.with_suffix(".encode.log")
            log.write_text("loi")
            job = home / "cache/workers/123"
            job.mkdir(parents=True)
            (job / "request.json").write_text(json.dumps(dict(action="render", output=str(video))))
            with patch("template_studio.output_files.shutil.move", side_effect=PermissionError("Đang mở log")):
                self.assertEqual(archive_output_artifacts(output, home), 0)
            self.assertEqual(log.read_text(), "loi")
            self.assertEqual(archive_output_artifacts(output, home), 1)
            self.assertFalse(log.exists())
            self.assertEqual(reports_directory(home), home / "cache/workers/batches")
            self.assertTrue(reports_directory(home).is_dir())
