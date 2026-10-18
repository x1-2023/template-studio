"""CLI offline: FFmpeg decode → shader OpenGL → một lần encode video/audio."""

import argparse
import json
import math
import os
import shutil
import subprocess
import sys
import time
import uuid
from contextlib import ExitStack
from pathlib import Path

import numpy as np
from PIL import Image

from offline_studio.cancellation import check_cancelled, managed_process
from offline_studio.process import NO_WINDOW, binary
from offline_studio.process import probe as media_probe

from .renderer import Renderer
from .resources import ROOT

for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8", errors="replace")


def probe(path):
    return media_probe(path)


def read_exact(stream, count):
    result = bytearray()
    while len(result) < count:
        chunk = stream.read(count - len(result))
        if not chunk:
            break
        result.extend(chunk)
    return bytes(result)


def load_preset(name):
    path = Path(name)
    if not path.is_file():
        path = ROOT / "presets" / f"{name}.json"
    return json.loads(path.read_text(encoding="utf-8-sig"))


def video_encoder_args(encoder, bitrate_mbps=None):
    """Chọn chất lượng cố định hoặc bitrate mục tiêu; không giả định CQ là giới hạn dung lượng."""
    if bitrate_mbps is not None:
        if not math.isfinite(bitrate_mbps) or not 0.1 <= bitrate_mbps <= 200:
            raise ValueError("Bitrate video phải trong [0.1, 200] Mb/s")
        bitrate = round(bitrate_mbps * 1_000_000)
        budget = [
            "-b:v",
            str(bitrate),
            "-maxrate",
            str(round(bitrate * 1.5)),
            "-bufsize",
            str(bitrate * 3),
        ]
    else:
        budget = []
    if encoder == "h264_nvenc":
        base = ["-c:v", "h264_nvenc", "-preset", "p5", "-tune", "hq", "-rc", "vbr"]
        return base + (
            budget + ["-multipass", "qres"] if budget else ["-cq", "18", "-b:v", "0"]
        )
    return ["-c:v", "libx264", "-preset", "fast"] + (
        budget if budget else ["-crf", "18"]
    )


def render(source, output, config, args, progress=lambda event: None):
    source, output = Path(source).resolve(), Path(output).resolve()
    if source == output:
        raise ValueError("Đầu ra không được ghi đè video nguồn")
    if not source.is_file():
        raise FileNotFoundError(source)
    if output.exists() and not args.overwrite:
        raise ValueError(f"Đầu ra đã có; dùng --overwrite nếu muốn thay: {output}")
    if output.suffix.lower() != ".mp4":
        raise ValueError("Đầu ra cần có đuôi .mp4")
    protected = {source}
    if args.skin_mask:
        protected.add(args.skin_mask.resolve())
    diagnostics = getattr(args, "diagnostics", None)
    sidecars = (
        [Path(diagnostics).resolve() / name for name in ("decode.log", "encode.log", "render.json")]
        if diagnostics else
        [output.with_suffix(suffix) for suffix in (".decode.log", ".encode.log", ".render.json")]
    )
    if any(path.resolve() in protected for path in [output, *sidecars]):
        raise ValueError("Đầu ra hoặc file phụ trùng với nguồn/skin mask")
    output.parent.mkdir(parents=True, exist_ok=True)
    sidecars[0].parent.mkdir(parents=True, exist_ok=True)
    info = probe(source)
    video = next(s for s in info["streams"] if s["codec_type"] == "video")
    audio = any(s["codec_type"] == "audio" for s in info["streams"]) and not getattr(
        args, "mute", False
    )
    stamp = (source.stat().st_size, source.stat().st_mtime_ns)
    rate, offset = float(config["playback_rate"]), float(config.get("source_offset", 0))
    timeline_offset = max(0, float(getattr(args, "timeline_offset", 0)))
    effect_offset = float(getattr(args, "effect_offset", 0))
    if not math.isfinite(effect_offset) or not 0 <= effect_offset <= timeline_offset:
        raise ValueError("Mốc bắt đầu intro không hợp lệ.")
    part_range = getattr(args, "part_range", None)
    if part_range is not None and (not isinstance(part_range, (list, tuple)) or len(part_range) != 2 or
            any(not isinstance(x, (int, float)) or not math.isfinite(x) for x in part_range) or
            not 0 <= part_range[0] <= timeline_offset < part_range[1]):
        raise ValueError("Phạm vi part không hợp lệ.")
    offset += timeline_offset * rate
    bitrate_mbps = args.video_bitrate
    encoder_options = video_encoder_args(args.encoder, bitrate_mbps)
    if not 0.5 <= rate <= 2 or offset < 0:
        raise ValueError("playback_rate phải trong [0.5,2]; source_offset >= 0")
    seconds = (float(video.get("duration", info["format"]["duration"])) - offset) / rate
    if args.seconds is not None:
        seconds = min(seconds, args.seconds)
    if seconds <= 0:
        raise ValueError("Không còn khung hình trong khoảng thời gian yêu cầu")
    w, h, fps = int(config["width"]), int(config["height"]), float(config["fps"])
    if min(w, h) < 32 or w % 2 or h % 2 or not 1 <= fps <= 120:
        raise ValueError("Kích thước cần chẵn, >=32; fps trong [1,120]")
    # Decode đúng PAR sang pixel vuông; không kéo dãn video có SAR khác 1.
    iw, ih = int(video["width"]), int(video["height"])
    sar = video.get("sample_aspect_ratio", "1:1")
    if sar not in ("N/A", "0:1"):
        a, b = map(int, sar.split(":"))
        iw = round(iw * a / b)
    dw, dh = iw, ih
    if args.proxy:
        factor = min(1.0, h * config["scale"] / ih)
        dw, dh = max(2, round(iw * factor / 2) * 2), max(2, round(ih * factor / 2) * 2)
    temporary = Path(
        getattr(args, "temporary", None)
        or output.with_name(f".beta-render-{uuid.uuid4().hex}.partial.mp4")
    )
    if (
        temporary.resolve().parent != output.parent
        or temporary == source
        or not temporary.name.endswith(".partial.mp4")
    ):
        raise ValueError("Đường dẫn file dở không hợp lệ.")
    decode_log, encode_log, render_report = sidecars
    subtitle_ass = None
    if config.get("subtitle_mode", "off") != "off":
        from template_studio.karaoke import (
            find_caption_file, load_words, write_ass,
        )
        mode = config["subtitle_mode"]
        if mode == "sidecar":
            caption_file = find_caption_file(source)
            if caption_file is None:
                raise FileNotFoundError("Thiếu phụ đề cạnh video: video.words.json hoặc video.srt")
            words = load_words(caption_file)
        elif mode == "file":
            if not config.get("subtitle_file"):
                raise ValueError("Chọn đường dẫn phụ đề .srt/.json")
            words = load_words(config["subtitle_file"])
        elif mode == "auto":
            raise ValueError("Cần nhận lời thoại trước khi render. Chạy preset từ màn hình Xuất video.")
        else:
            raise ValueError("Chế độ phụ đề không được hỗ trợ")
        subtitle_ass = (Path(diagnostics).resolve() / "karaoke.ass" if diagnostics else
                        output.parent / (".beta-karaoke-" + uuid.uuid4().hex + ".ass"))
        write_ass(words, subtitle_ass, w, h, source_offset=rate*timeline_offset+float(config.get("source_offset", 0)),
                  playback_rate=rate, angle=float(config.get("subtitle_angle", -11)),
                  red=config.get("subtitle_red", "FF374A"),
                  title=config.get("subtitle_title", "").replace("{video}", source.stem.replace("_", " "))[:140],
                  part_label=config.get("subtitle_part_label", ""), duration=seconds,
                  context_start=float(config.get("source_offset", 0)) + rate*(part_range[0] if part_range else 0),
                  context_end=float(config.get("source_offset", 0)) + rate*part_range[1] if part_range else None)
    renderer = Renderer((dw, dh), (w, h), config, args.skin, args.cache)
    gpu_name = renderer.ctx.info["GL_RENDERER"]
    started = time.perf_counter()
    decoder = encoder = mask_decoder = None
    mask_still = None
    frame_count = 0
    gpu_times, process_times = [], []
    expected = math.ceil(seconds * fps - 1e-6)
    if shutil.disk_usage(output.parent).free < max(
        256 * 1024**2, seconds * (bitrate_mbps or 20) * 1_000_000 / 8 * 1.2
    ):
        renderer.close()
        raise OSError("Không đủ dung lượng trống cho video đầu ra.")
    try:
        with (
            ExitStack() as stack,
            decode_log.open("wb") as de,
            encode_log.open("wb") as en,
        ):
            decode = [
                binary("ffmpeg"),
                "-hide_banner",
                "-loglevel",
                "error",
                "-ss",
                str(offset),
                "-i",
                str(source),
                "-t",
                str(seconds),
                "-vf",
                f"setpts=(PTS-STARTPTS)/{rate},fps={fps}:round=up,scale={dw}:{dh},setsar=1",
                "-an",
                "-pix_fmt",
                "rgb24",
                "-f",
                "rawvideo",
                "pipe:1",
            ]
            encode = [
                binary("ffmpeg"),
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-f",
                "rawvideo",
                "-pix_fmt",
                "rgb24",
                "-s",
                f"{w}x{h}",
                "-r",
                str(fps),
                "-i",
                "pipe:0",
            ]
            if audio:
                encode += ["-ss", str(offset), "-i", str(source)]
            encode += ["-map", "0:v:0", "-t", str(seconds)]
            if audio:
                encode += [
                    "-map",
                    "1:a:0",
                    "-af",
                    f"atempo={rate},asetpts=PTS-STARTPTS",
                    "-c:a",
                    "aac",
                    "-b:a",
                    "192k",
                ]
            encode += encoder_options
            if subtitle_ass is not None:
                # File ASS có tên ASCII cố định trong cwd riêng của worker.
                overlay = "setsar=1,ass=filename=" + subtitle_ass.name
            else:
                overlay = "setsar=1"
            encode += [
                "-vf",
                overlay,
                "-pix_fmt",
                "yuv420p",
                "-colorspace",
                "bt709",
                "-color_primaries",
                "bt709",
                "-color_trc",
                "bt709",
                "-movflags",
                "+faststart",
                str(temporary),
            ]
            decoder = stack.enter_context(
                managed_process(
                    decode,
                    stdout=subprocess.PIPE,
                    stderr=de,
                    bufsize=10**7,
                    creationflags=NO_WINDOW,
                )
            )
            encoder = stack.enter_context(
                managed_process(
                    encode,
                    cwd=subtitle_ass.parent if subtitle_ass is not None else None,
                    stdin=subprocess.PIPE,
                    stderr=en,
                    bufsize=10**7,
                    creationflags=NO_WINDOW,
                )
            )
            if args.skin == "mask":
                mask_path = Path(args.skin_mask).resolve()
                if mask_path.suffix.lower() in (".png", ".jpg", ".jpeg", ".bmp"):
                    im = Image.open(mask_path).convert("L")
                    if im.size != (w, h):
                        raise ValueError(
                            "Ảnh skin mask phải cùng kích thước canvas đầu ra"
                        )
                    mask_still = np.asarray(im)
                else:
                    mask_info = next(
                        s
                        for s in probe(mask_path)["streams"]
                        if s["codec_type"] == "video"
                    )
                    if (mask_info["width"], mask_info["height"]) != (w, h):
                        raise ValueError(
                            "Video skin mask phải cùng kích thước canvas đầu ra"
                        )
                    mask_decoder = stack.enter_context(
                        managed_process(
                            [
                                binary("ffmpeg"),
                                "-v",
                                "error",
                                "-i",
                                str(mask_path),
                                "-t",
                                str(seconds),
                                "-vf",
                                f"fps={fps}",
                                "-an",
                                "-pix_fmt",
                                "gray",
                                "-f",
                                "rawvideo",
                                "pipe:1",
                            ],
                            stdout=subprocess.PIPE,
                            stderr=de,
                            bufsize=10**7,
                            creationflags=NO_WINDOW,
                        )
                    )
            print(
                f"GPU: {gpu_name}; {w}x{h}/{fps:g} fps; decode {dw}x{dh}; {expected} frames",
                flush=True,
            )
            while frame_count < expected:
                check_cancelled()
                data = read_exact(decoder.stdout, dw * dh * 3)
                if not data:
                    break
                if len(data) != dw * dh * 3:
                    raise RuntimeError("FFmpeg trả khung hình không đầy đủ")
                frame = np.frombuffer(data, np.uint8).reshape(dh, dw, 3)
                mask = mask_still
                if mask_decoder:
                    raw_mask = read_exact(mask_decoder.stdout, w * h)
                    if len(raw_mask) != w * h:
                        raise RuntimeError("Skin mask kết thúc trước video")
                    mask = np.frombuffer(raw_mask, np.uint8).reshape(h, w)
                begin = time.perf_counter()
                result = renderer.process(
                    frame,
                    timeline_offset + frame_count / fps,
                    not args.no_effect,
                    not args.no_filter,
                    mask,
                    effect_offset=effect_offset,
                )
                process_times.append((time.perf_counter() - begin) * 1000)
                gpu_times.append(renderer.last_gpu_ms)
                encoder.stdin.write(result.tobytes())
                frame_count += 1
                if frame_count % 30 == 0:
                    progress(
                        dict(
                            percent=min(99, frame_count / expected * 100),
                            frames=frame_count,
                            total=expected,
                        )
                    )
                    print(f"Đã render {frame_count}/{expected} frames", flush=True)
            decoder.stdout.close()
            encoder.stdin.close()
            if mask_decoder:
                mask_decoder.stdout.close()
            dc, ec = decoder.wait(timeout=60), encoder.wait(timeout=60)
            mc = mask_decoder.wait(timeout=30) if mask_decoder else 0
            if dc or ec or mc:
                raise RuntimeError(
                    f"FFmpeg lỗi decode={dc}, encode={ec}, mask={mc}; xem {decode_log.name}, {encode_log.name}"
                )
            if abs(frame_count - expected) > 1:
                raise RuntimeError(f"Thiếu frames: {frame_count}/{expected}")
        if frame_count == 0:
            raise RuntimeError("Không render được khung hình nào")
        check_cancelled()
        if stamp != (source.stat().st_size, source.stat().st_mtime_ns):
            raise ValueError("Video nguồn thay đổi trong khi xuất.")
        actual = probe(temporary)
        stream = next(s for s in actual["streams"] if s["codec_type"] == "video")
        if (stream["width"], stream["height"]) != (w, h) or abs(
            float(stream["duration"]) - frame_count / fps
        ) > 0.15:
            raise ValueError("Đầu ra sai kích thước/thời lượng; chưa xuất bản.")
        if any(s["codec_type"] == "audio" for s in actual["streams"]) != audio:
            raise ValueError("Đầu ra sai cấu hình audio.")
        if output.exists() and not args.overwrite:
            raise FileExistsError("Tên đầu ra đã tồn tại; không ghi đè.")
        os.replace(temporary, output)
        elapsed = time.perf_counter() - started
        early = gpu_times[: min(frame_count, math.ceil(0.966667 * fps))]
        stats = {
            "source": str(source),
            "output": str(output),
            "preset": config,
            "skin": args.skin,
            "gpu": gpu_name,
            "encoder": args.encoder,
            "target_video_bitrate_mbps": bitrate_mbps,
            "estimated_size_mib": (bitrate_mbps + (0.192 if audio else 0))
            * 1_000_000
            * seconds
            / 8
            / 1024**2
            if bitrate_mbps
            else None,
            "frames": frame_count,
            "seconds": frame_count / fps,
            "wall_seconds": elapsed,
            "throughput_fps": frame_count / elapsed,
            "gpu_ms_mean": float(np.mean(gpu_times)),
            "gpu_ms_p95": float(np.percentile(gpu_times, 95)),
            "gpu_effect_window_ms_mean": float(np.mean(early)),
            "process_ms_mean": float(np.mean(process_times)),
            "proxy": args.proxy,
            "decode_size": [dw, dh],
            "ffmpeg_decode": decode,
            "ffmpeg_encode": encode,
            "output_probe": probe(output),
        }
        render_report.write_text(
            json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(
            json.dumps(
                {
                    k: stats[k]
                    for k in (
                        "output",
                        "frames",
                        "wall_seconds",
                        "throughput_fps",
                        "gpu_ms_mean",
                        "gpu_effect_window_ms_mean",
                    )
                },
                ensure_ascii=False,
            ),
            flush=True,
        )
        return stats
    finally:
        for proc in (decoder, encoder, mask_decoder):
            if proc and proc.poll() is None:
                proc.kill()
                proc.wait()
            if proc:
                for pipe in (proc.stdin, proc.stdout):
                    if pipe and not pipe.closed:
                        try:
                            pipe.close()
                        except OSError:
                            pass
        renderer.close()
        if temporary.exists():
            temporary.unlink()
        if subtitle_ass is not None:
            subtitle_ass.unlink(missing_ok=True)


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("input", nargs="?")
    p.add_argument("output", nargs="?")
    p.add_argument(
        "--batch", type=Path, help="JSON [{input,output,preset?,overrides?}]"
    )
    p.add_argument("--preset", default="capcut-pentagon")
    p.add_argument("--cache", type=Path, default=None)
    p.add_argument(
        "--seconds", type=float, default=3, help="Mặc định 3 giây; --full để xuất hết"
    )
    p.add_argument("--full", action="store_true")
    p.add_argument("--width", type=int)
    p.add_argument("--height", type=int)
    p.add_argument("--set", action="append", default=[], metavar="KEY=JSON")
    p.add_argument("--encoder", choices=("h264_nvenc", "libx264"), default="h264_nvenc")
    p.add_argument(
        "--video-bitrate",
        type=float,
        metavar="MBPS",
        help="Bitrate video mục tiêu, đơn vị Mb/s; bỏ qua để dùng CQ/CRF 18",
    )
    p.add_argument("--skin", choices=("none", "chroma", "mask"), default="none")
    p.add_argument("--skin-mask", type=Path)
    p.add_argument(
        "--proxy",
        action="store_true",
        help="Giảm kích thước decode cho preview; benchmark mặc định dùng nguồn đầy đủ",
    )
    p.add_argument("--no-effect", action="store_true")
    p.add_argument("--no-filter", action="store_true")
    p.add_argument("--overwrite", action="store_true")
    return p


def main():
    p = parser()
    args = p.parse_args()
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        p.error("Cần ffmpeg và ffprobe trong PATH")
    if args.full:
        args.seconds = None
    if args.seconds is not None and (
        not math.isfinite(args.seconds) or args.seconds <= 0
    ):
        p.error("--seconds phải >0")
    if args.skin == "mask" and not args.skin_mask:
        p.error("--skin mask cần --skin-mask")
    jobs = (
        json.loads(args.batch.read_text(encoding="utf-8-sig"))
        if args.batch
        else [{"input": args.input, "output": args.output}]
    )
    if (
        not isinstance(jobs, list)
        or not jobs
        or any(
            not isinstance(job, dict) or not job.get("input") or not job.get("output")
            for job in jobs
        )
    ):
        p.error("Cần input và output, hoặc --batch hợp lệ")
    if args.batch:
        for job in jobs:
            for key in ("input", "output"):
                path = Path(job[key])
                job[key] = str(
                    path if path.is_absolute() else args.batch.resolve().parent / path
                )
    failed = False
    for job in jobs:
        try:
            config = load_preset(job.get("preset", args.preset))
            config.update(job.get("overrides", {}))
            for pair in args.set:
                key, value = pair.split("=", 1)
                config[key] = json.loads(value)
            if args.width:
                config["width"] = args.width
            if args.height:
                config["height"] = args.height
            render(job["input"], job["output"], config, args)
        except (Exception, KeyboardInterrupt) as exc:  # noqa: BLE001 -- Ranh giới job: báo lỗi và cho batch xử lý job tiếp theo.
            print(f"Lỗi: {exc}", file=sys.stderr, flush=True)
            failed = True
            if not args.batch or isinstance(exc, KeyboardInterrupt):
                break
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
