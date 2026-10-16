"""Chạy helper PowerShell thật với EXE thử nghiệm để kiểm tra cài mới và phục hồi."""
import json
import os
import shutil
import subprocess
import tempfile
import time
import unittest
import uuid
from pathlib import Path

CSC = Path(os.environ.get('SystemRoot', r'C:\Windows')) / 'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
POWERSHELL = Path(os.environ.get('SystemRoot', r'C:\Windows')) / 'System32/WindowsPowerShell/v1.0/powershell.exe'
HELPER = Path(__file__).resolve().parents[1] / 'template_studio/apply_update.ps1'


@unittest.skipUnless(os.name == 'nt' and CSC.is_file(), 'Cần Windows và compiler .NET Framework')
class TransactionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temporary.name)
        bodies = {
            'old': 'File.WriteAllText(Path.Combine(home, "old-started.txt"), "restored");',
            'good': r'''File.WriteAllText(Path.Combine(home, "cache", "updates", args[1], "healthy.json"), "{\"version\":\"2.0.0\"}"); System.Threading.Thread.Sleep(800);''',
            'bad': 'Environment.Exit(9);',
        }
        for name, body in bodies.items():
            source = cls.root / (name + '.cs')
            source.write_text('using System; using System.IO; class Entry { static void Main(string[] args) { '
                              'string home = Environment.GetEnvironmentVariable("TEMPLATE_STUDIO_HOME"); '
                              + body + ' } }', encoding='utf-8')
            subprocess.run([str(CSC), '/nologo', '/target:winexe', '/out:' + str(cls.root / (name + '.exe')), str(source)],
                           check=True, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def scenario(self, kind):
        folder = self.root / uuid.uuid4().hex
        target, home = folder / 'app', folder / 'app/data/template-studio'
        target.mkdir(parents=True)
        home.mkdir(parents=True)
        (home / 'session.json').write_text('cấu hình giữ nguyên', encoding='utf-8')
        (home / 'production.json').write_text('preset và hàng đợi mới', encoding='utf-8')
        (home / 'runtime/capcut-cache').mkdir(parents=True)
        (home / 'runtime/capcut-cache/marker.txt').write_text('cache local giữ nguyên',encoding='utf-8')
        (target / 'exports').mkdir()
        (target / 'exports/video.mp4').write_bytes(b'original-export')
        (target / 'runtime').mkdir()
        (target / 'runtime/ffmpeg.exe').write_bytes(b'original-media')
        token = uuid.uuid4().hex
        job = home / 'cache/updates' / token
        stage = job / 'stage/TemplateStudio'
        stage.mkdir(parents=True)
        shutil.copy2(self.root / 'old.exe', target / 'TemplateStudio.exe')
        shutil.copy2(self.root / (kind + '.exe'), stage / 'TemplateStudio.exe')
        for directory, version in ((target, '1.0.0'), (stage, '2.0.0')):
            (directory / '_internal').mkdir()
            (directory / '_internal/marker.txt').write_text(version)
            (directory / 'release.json').write_text(json.dumps(dict(version=version, platform='windows-x64')))
        parent = subprocess.Popen([str(POWERSHELL), '-NoProfile', '-Command', 'Start-Sleep -Milliseconds 300'],
                                  creationflags=subprocess.CREATE_NO_WINDOW)
        plan = job / 'plan.json'
        plan.write_text(json.dumps(dict(target=str(target), stage=str(stage), job=str(job), home=str(home),
                                        parent_pid=parent.pid, token=token, version='2.0.0')), encoding='utf-8')
        result = subprocess.run([str(POWERSHELL), '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass',
                                 '-File', str(HELPER), '-PlanPath', str(plan)], capture_output=True, timeout=25,
                                creationflags=subprocess.CREATE_NO_WINDOW)
        parent.wait(timeout=5)
        self.assertEqual((home / 'session.json').read_text(encoding='utf-8'), 'cấu hình giữ nguyên')
        self.assertEqual((home / 'production.json').read_text(encoding='utf-8'), 'preset và hàng đợi mới')
        self.assertEqual((home / 'runtime/capcut-cache/marker.txt').read_text(encoding='utf-8'), 'cache local giữ nguyên')
        self.assertEqual((target / 'exports/video.mp4').read_bytes(), b'original-export')
        self.assertEqual((target / 'runtime/ffmpeg.exe').read_bytes(), b'original-media')
        return result, target, home, job

    def test_success_preserves_data_and_keeps_backup(self):
        result, target, home, job = self.scenario('good')
        self.assertEqual(result.returncode, 0, result.stderr.decode(errors='replace'))
        self.assertEqual((target / '_internal/marker.txt').read_text(), '2.0.0')
        self.assertEqual((job / 'backup/_internal/marker.txt').read_text(), '1.0.0')
        self.assertTrue((job / 'healthy.json').is_file())
        time.sleep(1)

    def test_failed_start_restores_previous_application(self):
        result, target, home, job = self.scenario('bad')
        self.assertEqual(result.returncode, 1, result.stderr.decode(errors='replace'))
        self.assertEqual((target / '_internal/marker.txt').read_text(), '1.0.0')
        self.assertEqual(json.loads((target / 'release.json').read_text())['version'], '1.0.0')
        self.assertIn('Cap nhat that bai', (job / 'result.txt').read_text(encoding='utf-8-sig'))
        deadline = time.monotonic() + 5
        while not (home / 'old-started.txt').exists() and time.monotonic() < deadline:
            time.sleep(.05)
        self.assertTrue((home / 'old-started.txt').is_file())
