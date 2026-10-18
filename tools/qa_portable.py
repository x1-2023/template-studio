"""Giải nén ZIP sang máy giả lập sạch, tự tải FFmpeg và render bằng EXE thật."""

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from template_studio.media_setup import FILES  # noqa: E402
from template_studio.presets import DEFAULT_PRESET_ID, catalog  # noqa: E402
from template_studio.updater import extract_package  # noqa: E402
from template_studio.version import ASSET_NAME, VERSION  # noqa: E402


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def run(command, env, log, timeout=180):
    with log.open("wb") as stream:
        subprocess.run(
            command,
            env=env,
            stdout=stream,
            stderr=stream,
            check=True,
            timeout=timeout,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )


def probe(ffprobe, path, env):
    return json.loads(
        subprocess.check_output(
            [
                str(ffprobe),
                "-v",
                "error",
                "-show_streams",
                "-show_format",
                "-of",
                "json",
                str(path),
            ],
            env=env,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument(
        "--archive", type=Path, default=ROOT / "release/template-studio" / ASSET_NAME
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument("--karaoke", action="store_true", help="Kiểm tra nhận giọng nói và ba phần karaoke bằng worker EXE")
    args = parser.parse_args()
    source = args.input.resolve()
    if not source.is_file():
        raise FileNotFoundError("Không tìm thấy video để kiểm tra.")
    folder = (
        args.output
        or ROOT
        / ".runtime"
        / ("qa-portable-" + datetime.now().strftime("%Y%m%d-%H%M%S"))
    ).resolve()
    if folder.exists():
        raise FileExistsError(
            "Thư mục kiểm tra đã tồn tại; chọn thư mục mới để không dùng lại dữ liệu."
        )
    app = extract_package(args.archive, folder, VERSION)
    home = app / "data/template-studio"
    assert not home.exists()
    env = dict(os.environ)
    for key in (
        "TEMPLATE_STUDIO_HOME",
        "TEMPLATE_STUDIO_CAPCUT_CACHE",
        "STUDIO_HOME",
        "STUDIO_OFFLINE_DATA_DIR",
        "PYTHONHOME",
        "PYTHONPATH",
        "QT_PLUGIN_PATH",
        "QML2_IMPORT_PATH",
        "QML_IMPORT_PATH",
    ):
        env.pop(key, None)
    windows = Path(env.get("SystemRoot", "C:/Windows"))
    env.update(
        PATH=os.pathsep.join(map(str, (windows / "System32", windows))),
        PYINSTALLER_RESET_ENVIRONMENT="1",
        PYTHONUTF8="1",
    )
    executable = app / "TemplateStudio.exe"
    print(
        "Máy giả lập sạch: không Python trong PATH, không FFmpeg, không cache effect.",
        flush=True,
    )
    run(
        [
            str(executable),
            "--check-gpu",
            "--input",
            str(source),
            "--capture",
            str(folder / "lan-dau.png"),
        ],
        env,
        folder / "lan-dau.log",
        timeout=240,
    )
    first = read_json(home / "check-result.json")
    assert first["ok"] and first["effectsReady"] and first["gpuReady"], first
    assert Path(first["effects"]).is_relative_to(app / "_internal")
    assert not (home / "runtime/capcut-cache").exists()
    media = home / "runtime/media/bin"
    assert Path(first["ffmpeg"]) == media / "ffmpeg.exe"
    for name, expected in FILES.items():
        with (media / name).open("rb") as stream:
            assert hashlib.file_digest(stream, "sha256").hexdigest() == expected
    print(
        "Lần đầu: tự tải FFmpeg, xác minh checksum, GPU và hiệu ứng sẵn sàng.",
        flush=True,
    )
    # Chặn truy cập mạng cho lần kiểm tra sau khi đã chuẩn bị runtime.
    offline = dict(
        env,
        HTTPS_PROXY="http://127.0.0.1:9",
        HTTP_PROXY="http://127.0.0.1:9",
        NO_PROXY="",
    )
    run([str(executable), "--check-gpu"], offline, folder / "offline.log")
    assert read_json(home / "check-result.json")["ok"]
    original = probe(media / "ffprobe.exe", source, offline)
    assert float(original["format"]["duration"]) >= 3.1, (
        "Video kiểm tra cần dài ít nhất 3,1 giây."
    )
    has_audio = any(s["codec_type"] == "audio" for s in original["streams"])
    results = []
    for preset_id in (DEFAULT_PRESET_ID, "reference"):
        preset = next(p for p in catalog() if p["id"] == preset_id)
        job = folder / preset_id
        job.mkdir()
        output = job / "exports/video.mp4"
        encoder = "h264_nvenc" if "NVENC" in first["hardware"] else "libx264"
        request = dict(
            action="render",
            source=str(source),
            output=str(output),
            config=preset["config"],
            cache=first["effects"],
            encoder=encoder,
            bitrate=preset["config"]["video_bitrate"],
            preview=False,
            seconds=3,
        )
        request_path = job / "request.json"
        request_path.write_text(
            json.dumps(request, ensure_ascii=False), encoding="utf-8"
        )
        run(
            [str(executable), "--render-worker", "--request", str(request_path)],
            offline,
            job / "launcher.log",
        )
        result = read_json(job / "result.json")
        assert result["ok"], result
        stats = result["result"]
        assert list(output.parent.iterdir()) == [output], "Thư mục xuất còn file kỹ thuật."
        assert all((job / name).is_file() for name in ("decode.log", "encode.log", "render.json"))
        metadata = probe(media / "ffprobe.exe", output, offline)
        video = next(s for s in metadata["streams"] if s["codec_type"] == "video")
        assert (video["width"], video["height"]) == (1080, preset["config"]["height"])
        assert video["codec_name"] == "h264" and video["r_frame_rate"] == "30/1"
        assert video["sample_aspect_ratio"] == "1:1" and video["nb_frames"] == "90"
        assert any(s["codec_type"] == "audio" for s in metadata["streams"]) == has_audio
        assert stats["encoder"] == encoder and not stats["proxy"]
        results.append(
            dict(
                preset=preset_id,
                gpu=stats["gpu"],
                encoder=encoder,
                width=video["width"],
                height=video["height"],
                frames=video["nb_frames"],
                wall_seconds=stats["wall_seconds"],
            )
        )
        print(
            f"EXE offline: {preset['name']} · {video['width']}×{video['height']} · 90 khung · OK",
            flush=True,
        )
    karaoke = None
    if args.karaoke:
        job = folder / "speech"
        job.mkdir()
        request_path = job / "request.json"
        request_path.write_text(json.dumps(dict(action="transcribe",source=str(source))),encoding="utf-8")
        run([str(executable),"--render-worker","--request",str(request_path)], env, job/"launcher.log", timeout=600)
        speech = read_json(job/"result.json")
        assert speech["ok"] and len(speech["result"]["words"]) > 5, speech
        captions = job/"words.json"
        captions.write_text(json.dumps(speech["result"]["words"],ensure_ascii=False),encoding="utf-8")
        preset = next(p for p in catalog() if p["id"]=="karaoke-1012")
        preset["config"].update(part_count=3, playback_rate=1)
        from template_studio.parts import plan_parts
        source_video = next(s for s in original["streams"] if s["codec_type"]=="video")
        intervals = plan_parts(float(source_video.get("duration",original["format"]["duration"])),preset["config"])
        outputs = folder/"karaoke-exports"
        outputs.mkdir()
        karaoke = dict(words=len(speech["result"]["words"]),parts=[])
        for i, interval in enumerate(intervals):
            part = folder/f"karaoke-{i+1}"
            part.mkdir()
            request = dict(action="render",source=str(source),output=str(outputs/f"part{i+1}.mp4"),
                           config={**preset["config"],"subtitle_mode":"file","subtitle_file":str(captions),"subtitle_part_label":f"PART {i+1}"},
                           cache=first["effects"],encoder="h264_nvenc",bitrate=12,preview=False,
                           seconds=interval["seconds"],offset=interval["start"])
            request["effect_offset"] = interval["start"]
            request_path = part/"request.json"
            request_path.write_text(json.dumps(request,ensure_ascii=False),encoding="utf-8")
            run([str(executable),"--render-worker","--request",str(request_path)], offline, part/"launcher.log", timeout=240)
            result = read_json(part/"result.json")
            assert result["ok"], result
            info = probe(media/"ffprobe.exe",Path(request["output"]),offline)
            video = next(s for s in info["streams"] if s["codec_type"]=="video")
            assert (video["width"],video["height"],video["r_frame_rate"])==(1080,1440,"30/1")
            assert abs(float(video["duration"])-interval["seconds"]) < .15
            assert any(s["codec_type"]=="audio" for s in info["streams"])==has_audio
            karaoke["parts"].append(dict(output=request["output"],frames=video["nb_frames"],seconds=video["duration"]))
            print(f"Karaoke EXE offline: phần {i+1}/3 · OK",flush=True)
        assert len(list(outputs.iterdir()))==3
    (folder / "xac-minh.json").write_text(
        json.dumps(
            dict(
                version=VERSION,
                first_start=first,
                offline=True,
                renders=results,
                karaoke=karaoke,
            ),
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(
        f"Bản tải dùng được với dữ liệu sạch; báo cáo: {folder / 'xac-minh.json'}",
        flush=True,
    )


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
