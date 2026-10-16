"""Chạy worker riêng có hủy cây tiến trình và IPC JSON nguyên tử."""

import json
import os
import sys
import time
import uuid
from pathlib import Path

from offline_studio.cancellation import check_cancelled, managed_process
from offline_studio.config import atomic_json
from offline_studio.process import NO_WINDOW


def run_worker(root, home, request, progress=lambda event: None):
    folder = Path(home) / "cache/workers" / uuid.uuid4().hex
    folder.mkdir(parents=True)
    if request.get("action") == "render":
        output = Path(request["output"]).resolve()
        request = {
            **request,
            "temporary": str(
                output.with_name(output.stem + "." + folder.name + ".partial.mp4")
            ),
        }
    atomic_json(folder / "request.json", request)
    command = (
        [sys.executable, "--render-worker"]
        if getattr(sys, "frozen", False)
        else [sys.executable, "-m", "template_studio.worker"]
    )
    command += ["--request", str(folder / "request.json")]
    env = os.environ.copy()
    env["TEMPLATE_STUDIO_HOME"] = str(home)
    env["PYTHONUTF8"] = "1"
    # Process con phải nạp DLL từ chính gói app, không tái dùng môi trường bootloader cha.
    if getattr(sys, "frozen", False):
        env["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
    began = time.monotonic()
    last = None
    try:
        with (folder / "launcher.log").open("wb") as log:
            with managed_process(
                command,
                cwd=str(root),
                env=env,
                stdout=log,
                stderr=log,
                creationflags=NO_WINDOW,
            ) as process:
                while process.poll() is None:
                    check_cancelled()
                    if time.monotonic() - began > max(
                        120, request.get("timeout", 7200)
                    ):
                        raise TimeoutError(
                            "Worker vượt thời gian chờ; xem "
                            + str(folder / "worker.log")
                        )
                    try:
                        data = (folder / "progress.json").read_text(encoding="utf-8")
                        if data != last:
                            progress(json.loads(data))
                            last = data
                    except FileNotFoundError:
                        pass
                    time.sleep(0.1)
                check_cancelled()
                try:
                    result = json.loads(
                        (folder / "result.json").read_text(encoding="utf-8")
                    )
                except (OSError, ValueError) as error:
                    raise RuntimeError(
                        "Worker dừng bất thường. Nhật ký: " + str(folder)
                    ) from error
                if process.returncode or not result.get("ok"):
                    raise RuntimeError(
                        result.get("error", "Worker thất bại")
                        + " · Nhật ký: "
                        + str(folder)
                    )
    finally:
        if request.get("temporary"):
            partial = Path(request["temporary"])
            if (
                partial.parent == Path(request["output"]).resolve().parent
                and folder.name in partial.name
            ):
                # TerminateJobObject trả về trước khi FFmpeg nhả hết handle file.
                for attempt in range(50):
                    try:
                        partial.unlink(missing_ok=True)
                        break
                    except PermissionError:
                        if attempt == 49:
                            raise
                        time.sleep(0.1)
    return result["result"]
