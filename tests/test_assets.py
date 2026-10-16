"""Máy mới phải có hiệu ứng sẵn; file thiếu/hỏng phải được phát hiện."""

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from template_studio.assets_local import discover, validate
from template_studio.gpu.resources import bundled_cache

ROOT = Path(__file__).resolve().parents[1]


class BundledAssetsTests(unittest.TestCase):
    def test_clean_home_discovers_bundled_effects_without_import(self):
        with (
            tempfile.TemporaryDirectory() as folder,
            patch.dict(os.environ, {"TEMPLATE_STUDIO_CAPCUT_CACHE": ""}),
        ):
            home = Path(folder)
            self.assertEqual(discover(ROOT, home), bundled_cache(ROOT))
            self.assertTrue(validate(bundled_cache(ROOT)))
            self.assertFalse((home / "runtime/capcut-cache").exists())

    def test_corrupt_or_missing_file_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            cache = Path(folder) / "effects"
            shutil.copytree(bundled_cache(ROOT), cache)
            manifest = json.loads((cache / "runtime-manifest.json").read_text())
            path = cache / next(iter(manifest["files"]))
            path.write_bytes(b"corrupt")
            with self.assertRaises(ValueError):
                validate(cache)
            path.unlink()
            with self.assertRaises(ValueError):
                validate(cache)

    def test_manifest_cannot_reference_files_outside_bundle(self):
        with tempfile.TemporaryDirectory() as folder:
            cache = Path(folder) / "effects"
            shutil.copytree(bundled_cache(ROOT), cache)
            path = cache / "runtime-manifest.json"
            manifest = json.loads(path.read_text())
            key = next(iter(manifest["files"]))
            manifest["files"]["../outside.frag"] = manifest["files"].pop(key)
            path.write_text(json.dumps(manifest))
            with self.assertRaises(ValueError):
                validate(cache)
