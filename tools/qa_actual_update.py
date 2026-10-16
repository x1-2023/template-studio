"""Thử helper updater với EXE 1.0.0 và gói 1.1.0 thật trong bản sao QA riêng."""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from template_studio.assets_local import import_cache  # noqa: E402
from template_studio.presets import normalize  # noqa: E402
from template_studio.updater import extract_package  # noqa: E402


def main():
    target = ROOT / ".runtime/qa-upgrade-actual/app"
    assert target.resolve().is_relative_to(ROOT / ".runtime/qa-upgrade-actual")
    assert json.loads((target / "release.json").read_text())["version"] == "1.0.0", (
        "QA cần bản sao EXE 1.0.0 chưa dùng để cập nhật"
    )
    old_hash = hashlib.sha256((target / "TemplateStudio.exe").read_bytes()).hexdigest()
    home = target / "data/template-studio"
    home.mkdir(parents=True, exist_ok=True)
    (home / "session.json").write_text(
        json.dumps(dict(settings={}, rows=[], output=str(home / "exports")))
    )
    production = dict(
        schema=1,
        config=normalize({"flip": True}),
        preset="custom-qa",
        custom=[],
        rows=[],
        output=str(home / "exports"),
    )
    (home / "production.json").write_text(json.dumps(production))
    imports = import_cache(ROOT / "CapCut_FFmpeg_Codex_Handoff/work/cache", home)
    media = home / "runtime/media/bin"
    media.mkdir(parents=True, exist_ok=True)
    for name in ("ffmpeg.exe", "ffprobe.exe"):
        shutil.copy2(ROOT / "offline_studio/assets/bin" / name, media / name)
    exports = home / "exports"
    exports.mkdir(exist_ok=True)
    (exports / "keep.txt").write_text("giữ nguyên", encoding="utf-8")
    hashes = {
        str(path.relative_to(home)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in imports.rglob("*")
        if path.is_file()
    }
    token = uuid.uuid4().hex
    job = target / ".updates" / token
    job.mkdir(parents=True)
    archive = ROOT / "release/template-studio/TemplateStudio-windows-x64.zip"
    stage = extract_package(archive, job / "stage", "1.1.0")
    plan = job / "plan.json"
    plan.write_text(
        json.dumps(
            dict(
                target=str(target),
                stage=str(stage),
                job=str(job),
                home=str(home),
                parent_pid=99999999,
                token=token,
                version="1.1.0",
            )
        )
    )
    shell = (
        Path(os.environ.get("SystemRoot", r"C:\Windows"))
        / "System32/WindowsPowerShell/v1.0/powershell.exe"
    )
    result = subprocess.run(
        [
            str(shell),
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(ROOT / "template_studio/apply_update.ps1"),
            "-PlanPath",
            str(plan),
        ],
        capture_output=True,
        check=False,
        timeout=100,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    try:
        assert result.returncode == 0, (
            result.stderr.decode(errors="replace"),
            (job / "result.txt").read_text(encoding="utf-8-sig"),
        )
        assert json.loads((target / "release.json").read_text())["version"] == "1.1.0"
        assert (
            hashlib.sha256((job / "backup/TemplateStudio.exe").read_bytes()).hexdigest()
            == old_hash
        )
        saved = json.loads((home / "production.json").read_text())
        assert saved["config"]["flip"] and saved["output"] == production["output"]
        assert (exports / "keep.txt").read_text(encoding="utf-8") == "giữ nguyên"
        assert all(
            hashlib.sha256((home / path).read_bytes()).hexdigest() == digest
            for path, digest in hashes.items()
        )
        assert json.loads((job / "healthy.json").read_text())["version"] == "1.1.0"
        report = dict(
            ok=True,
            fromVersion="1.0.0",
            toVersion="1.1.0",
            realExe=True,
            backup=True,
            presets=True,
            queue=True,
            assets=True,
            exports=True,
        )
        (ROOT / ".runtime/qa-upgrade-actual/result.json").write_text(
            json.dumps(report, indent=2)
        )
        print(json.dumps(report))
    finally:
        # Chỉ đóng cửa sổ của bản sao QA vừa mở, không chạm app người dùng.
        command = (
            "$items=Get-CimInstance Win32_Process | Where-Object { $_.ExecutablePath -eq '"
            + str(target / "TemplateStudio.exe").replace("'", "''")
            + "' }; foreach($item in $items) { $p=Get-Process -Id $item.ProcessId; [void]$p.CloseMainWindow() }"
        )
        subprocess.run(
            [str(shell), "-NoProfile", "-Command", command],
            capture_output=True,
            check=False,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )


if __name__ == "__main__":
    main()
