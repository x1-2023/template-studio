"""Hồi quy lỗi khóa JSON trên Windows và lỗi dọn pipe che traceback."""

import ctypes
import json
import os
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import Mock, patch

from offline_studio.cancellation import managed_process
from offline_studio.config import atomic_json
from template_studio.worker import ProgressWriter


class AtomicJsonTests(unittest.TestCase):
    def test_retries_replace_and_cleans_pending_on_failure(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "progress.json"
            atomic_json(target, {"frames": 30})
            replace = os.replace
            calls = []

            def locked_once(source, destination):
                calls.append(source)
                if len(calls) == 1:
                    raise PermissionError("File đang được đọc")
                replace(source, destination)

            with patch("offline_studio.config.os.replace", side_effect=locked_once):
                atomic_json(target, {"frames": 60})
            self.assertEqual(len(calls), 2)
            self.assertEqual(json.loads(target.read_text())["frames"], 60)
            with patch("offline_studio.config.os.replace", side_effect=PermissionError("Khóa lâu")), patch("offline_studio.config.time.sleep"):
                with self.assertRaises(PermissionError):
                    atomic_json(target, {"frames": 90})
            self.assertEqual(json.loads(target.read_text())["frames"], 60)
            self.assertEqual(list(Path(folder).iterdir()), [target])

    def test_concurrent_writers_do_not_share_pending_files(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "progress.json"
            with ThreadPoolExecutor(max_workers=4) as pool:
                list(pool.map(lambda n: atomic_json(target, {"frames": n}), range(20)))
            self.assertIn(json.loads(target.read_text())["frames"], range(20))
            self.assertEqual(list(Path(folder).iterdir()), [target])

    @unittest.skipUnless(os.name == "nt", "Cần handle chia sẻ file của Windows")
    def test_real_windows_read_handle_temporarily_blocks_replace(self):
        from ctypes import wintypes

        api = ctypes.WinDLL("kernel32", use_last_error=True)
        api.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
        api.CreateFileW.restype = wintypes.HANDLE
        api.CloseHandle.argtypes = [wintypes.HANDLE]
        api.CloseHandle.restype = wintypes.BOOL
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "progress.json"
            atomic_json(target, {"frames": 30})
            handle = api.CreateFileW(str(target), 0x80000000, 1, None, 3, 0, None)
            self.assertNotEqual(handle, ctypes.c_void_p(-1).value)
            replace = os.replace
            blocked = []

            def replace_and_release(source, destination):
                try:
                    replace(source, destination)
                except PermissionError:
                    blocked.append(True)
                    api.CloseHandle(handle)
                    raise

            try:
                with patch("offline_studio.config.os.replace", side_effect=replace_and_release):
                    atomic_json(target, {"frames": 60})
            finally:
                if not blocked:
                    api.CloseHandle(handle)
            self.assertTrue(blocked)
            self.assertEqual(json.loads(target.read_text())["frames"], 60)


class RenderIoTests(unittest.TestCase):
    def test_progress_write_failure_does_not_abort_and_recovers(self):
        with tempfile.TemporaryDirectory() as folder:
            reporter = ProgressWriter(folder)
            with patch("template_studio.worker.atomic_json", side_effect=PermissionError("Đang khóa")), patch("builtins.print") as log:
                reporter({"frames": 540})
                reporter({"frames": 570})
                log.assert_called_once()
            reporter({"frames": 600})
            self.assertEqual(json.loads(reporter.path.read_text())["frames"], 600)
            self.assertFalse(reporter.warned)

    def test_pipe_cleanup_preserves_original_error(self):
        process = Mock()
        process.poll.return_value = 0
        process.stdin.close.side_effect = OSError(22, "Invalid argument")
        process.stdout = process.stderr = None
        original = PermissionError("Không ghi được tiến độ")
        with patch("offline_studio.cancellation.subprocess.Popen", return_value=process), patch("offline_studio.cancellation._WindowsJob"):
            with self.assertRaises(PermissionError) as caught:
                with managed_process(["worker"]):
                    raise original
        self.assertIs(caught.exception, original)
        process.wait.assert_called_once()

    def test_cancel_still_stops_process_when_stream_close_fails(self):
        process = Mock()
        process.poll.return_value = None
        process.stdin.close.side_effect = OSError(22, "Invalid argument")
        process.stdout = process.stderr = None
        with patch("offline_studio.cancellation.subprocess.Popen", return_value=process), patch("offline_studio.cancellation._WindowsJob"), patch("offline_studio.cancellation._stop_process_tree") as stop:
            with managed_process(["worker"]):
                pass
        stop.assert_called_once()
        process.wait.assert_called_once()
