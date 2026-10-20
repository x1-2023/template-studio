"""Nhận giọng nói local bằng Whisper native, tải runtime đã xác minh một lần."""

import hashlib
import importlib.util
import json
import math
import os
import re
import shutil
import sys
import time
import urllib.request
import uuid
import zipfile
from pathlib import Path

from offline_studio.cancellation import check_cancelled, managed_process
from offline_studio.config import atomic_json
from offline_studio.process import NO_WINDOW, binary, probe, run
from .network import error_hint, open_https

RUNTIME_VERSION = "b5454"
RUNTIME_URL = f"https://github.com/ggml-org/whisper.cpp/releases/download/{RUNTIME_VERSION}/whisper-bin-x64.zip"
RUNTIME_SHA256 = "6ba69e3482d7826214f90a6a9c84ca07782aec1e1d0c6a7c30c994fd5d816ccb"
MODEL_URL = "https://huggingface.co/ggerganov/whisper.cpp/resolve/5359861c739e955e79d9a303bcbc70fb988958b1/ggml-base.bin"
MODEL_SHA256 = "60ed5bc3dd14eea856493d334349b405782ddcaf0028d4b5df4088345fba2efe"
MODEL_BYTES = 147951465


def _digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _download(url, target, expected, limit, emit, staging=None):
    pending = Path(staging or target.parent) / (target.name + "." + uuid.uuid4().hex + ".partial")
    received = 0
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "BetaRender"})
        with open_https(request, timeout=30) as response, pending.open("xb") as stream:
            while chunk := response.read(1024**2):
                check_cancelled()
                received += len(chunk)
                if received > limit:
                    raise ValueError("Gói nhận giọng nói vượt kích thước cho phép.")
                stream.write(chunk)
                emit(dict(percent=0, stage=f"Lần đầu: tải bộ nhận giọng nói · {received / 1024**2:.0f} MiB"))
        if _digest(pending) != expected:
            raise ValueError("Checksum bộ nhận giọng nói không khớp; chưa cài.")
        check_cancelled()
        os.replace(pending, target)
    except OSError as error:
        raise RuntimeError("Không tải được bộ nhận giọng nói. " + error_hint(error)) from error
    finally:
        pending.unlink(missing_ok=True)


def ensure_speech(home, emit=lambda event: None, staging=None):
    home = Path(home).resolve()
    runtime = home / "runtime/speech" / RUNTIME_VERSION
    runtime.mkdir(parents=True, exist_ok=True)
    manifest = runtime / "files.json"
    try:
        files = json.loads(manifest.read_text(encoding="utf-8"))
        ready = bool(files.get("whisper-cli.exe")) and all(
            Path(name).name == name and (runtime / name).is_file()
            and _digest(runtime / name) == digest for name, digest in files.items()
        )
    except (OSError, ValueError, AttributeError, TypeError):
        ready = False
    if not ready:
        if shutil.disk_usage(home).free < 400 * 1024**2:
            raise OSError("Cần ít nhất 400 MiB trống để chuẩn bị nhận giọng nói.")
        archive = Path(staging or runtime) / "whisper-runtime.zip"
        _download(RUNTIME_URL, archive, RUNTIME_SHA256, 32 * 1024**2, emit, staging)
        files = {}
        try:
            with zipfile.ZipFile(archive) as package:
                for entry in package.infolist():
                    name = Path(entry.filename).name
                    if not (name in ("whisper-cli.exe", "whisper.dll") or re.fullmatch(r"ggml[\w-]*\.dll", name)):
                        continue
                    if entry.file_size > 16 * 1024**2 or name in files:
                        raise ValueError("Gói Whisper có file không hợp lệ.")
                    data = package.read(entry)
                    (runtime / name).write_bytes(data)
                    files[name] = hashlib.sha256(data).hexdigest()
            if not {"whisper-cli.exe", "whisper.dll", "ggml.dll", "ggml-base.dll"} <= files.keys():
                raise ValueError("Gói Whisper thiếu thư viện.")
            atomic_json(manifest, files)
        finally:
            archive.unlink(missing_ok=True)
    model = home / "runtime/speech/ggml-base.bin"
    if not model.is_file() or model.stat().st_size != MODEL_BYTES or _digest(model) != MODEL_SHA256:
        _download(MODEL_URL, model, MODEL_SHA256, MODEL_BYTES, emit, staging)
    return runtime / "whisper-cli.exe", model


def parse_whisper(data):
    from .karaoke import _words_for_phrase
    words = []
    for segment in data.get("transcription", []):
        text = segment.get("text", "").strip()
        times = segment.get("offsets", {})
        start, end = float(times.get("from", 0)) / 1000, float(times.get("to", 0)) / 1000
        if not all(math.isfinite(t) for t in (start, end)) or start < 0:
            raise ValueError("Whisper trả mốc thời gian không hợp lệ.")
        if not text or text.startswith(("[_", "[BLANK_AUDIO]", "[SILENCE]")) or end <= start:
            continue
        words.extend(_words_for_phrase(text, start, end))
    if len(words) > 50_000:
        raise ValueError("Video có quá nhiều từ phụ đề.")
    return words


def transcribe(source, home, folder, emit):
    source, folder = Path(source).resolve(), Path(folder).resolve()
    info = probe(source)
    if not any(s["codec_type"] == "audio" for s in info["streams"]):
        raise ValueError("Video không có âm thanh để nhận lời thoại. Có thể tắt phụ đề trong cấu hình.")
    executable, model = ensure_speech(home, emit, staging=folder)
    wave = folder / "audio.wav"
    result = folder / "speech.json"
    emit(dict(percent=0, stage="Đang đọc âm thanh…"))
    try:
        run([binary("ffmpeg"), "-v", "error", "-y", "-i", str(source),
             "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(wave)])
        command = [str(executable), "-m", os.path.relpath(model, folder), "-f", "audio.wav", "-l", "auto",
                   "-t", str(max(1, min(8, (os.cpu_count() or 4) // 2))), "-ng", "-ml", "1",
                   "-sow", "-oj", "-of", "speech", "-pp"]
        env = dict(os.environ)
        windows = Path(os.environ.get("SystemRoot", "C:/Windows"))
        libraries = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
        qt_libraries = Path(importlib.util.find_spec("PySide6").origin).parent
        env["PATH"] = os.pathsep.join(map(str, (executable.parent, libraries, qt_libraries, windows / "System32", windows)))
        began = time.monotonic()
        with (folder / "speech.log").open("wb") as log:
            with managed_process(command, cwd=folder, env=env, stdout=log, stderr=log, creationflags=NO_WINDOW) as process:
                last = -1
                while process.poll() is None:
                    check_cancelled()
                    if time.monotonic() - began > max(900, float(info["format"]["duration"]) * 5):
                        raise TimeoutError("Nhận giọng nói vượt thời gian chờ; xem speech.log.")
                    content = (folder / "speech.log").read_text(encoding="utf-8", errors="replace")[-2000:]
                    matches = re.findall(r"progress\s*=\s*(\d+)%", content)
                    percent = int(matches[-1]) if matches else 0
                    if percent != last:
                        emit(dict(percent=percent, stage=f"Đang nhận lời thoại · {percent}%"))
                        last = percent
                    time.sleep(.15)
                if process.returncode or not result.is_file():
                    raise RuntimeError("Không nhận được lời thoại; xem speech.log trong nhật ký tác vụ.")
        return dict(words=parse_whisper(json.loads(result.read_text(encoding="utf-8"))))
    finally:
        wave.unlink(missing_ok=True)


def prepare_captions(root, home, source, config, notice):
    """Preview và các phần xuất dùng chung phụ đề đã nhận của nguồn không đổi."""
    if config.get("subtitle_mode") != "auto":
        return config
    from .worker_client import run_worker
    path = Path(source).resolve()
    stamp = (path.stat().st_size, path.stat().st_mtime_ns)
    key = hashlib.sha256(json.dumps([str(path), stamp, MODEL_SHA256, RUNTIME_VERSION]).encode()).hexdigest()
    destination = Path(home) / "cache/captions" / (key + ".words.json")
    try:
        data = json.loads(destination.read_text(encoding="utf-8"))
        cached = data.get("schema") == 1 and isinstance(data.get("words"), list)
        if cached:
            from .karaoke import load_words
            load_words(destination)
    except (OSError, ValueError, AttributeError):
        cached = False
    if not cached:
        result = run_worker(root, home, dict(action="transcribe", source=str(path), timeout=14400),
                            lambda event: notice(event.get("stage", "Đang nhận lời thoại…")))
        if stamp != (path.stat().st_size, path.stat().st_mtime_ns):
            raise ValueError("Video nguồn đã thay đổi trong lúc nhận lời thoại.")
        atomic_json(destination, dict(schema=1, words=result["words"]))
    return {**config, "subtitle_mode": "file", "subtitle_file": str(destination)}
