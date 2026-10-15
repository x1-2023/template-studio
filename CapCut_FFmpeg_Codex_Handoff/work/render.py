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
from pathlib import Path

import numpy as np
from gpu import ROOT, Renderer
from PIL import Image

for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8", errors="replace")


def probe(path):
    run = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_streams",
            "-show_format",
            "-of",
            "json",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(run.stdout)


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


def render(source, output, config, args):
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
    sidecars = [
        output.with_suffix(suffix)
        for suffix in (".decode.log", ".encode.log", ".render.json")
    ]
    if any(path.resolve() in protected for path in [output, *sidecars]):
        raise ValueError("Đầu ra hoặc file phụ trùng với nguồn/skin mask")
    output.parent.mkdir(parents=True, exist_ok=True)
    info = probe(source)
    video = next(s for s in info["streams"] if s["codec_type"] == "video")
    audio = any(s["codec_type"] == "audio" for s in info["streams"])
    rate, offset = float(config["playback_rate"]), float(config.get("source_offset", 0))
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
    temporary = output.with_name(f"{output.stem}.{uuid.uuid4().hex}.partial.mp4")
    decode_log = output.with_suffix(".decode.log")
    encode_log = output.with_suffix(".encode.log")
    started = time.perf_counter()
    renderer = Renderer((dw, dh), (w, h), config, args.skin, args.cache)
    gpu_name = renderer.ctx.info["GL_RENDERER"]
    decoder = encoder = mask_decoder = None
    mask_still = None
    frame_count = 0
    gpu_times, process_times = [], []
    expected = math.ceil(seconds * fps - 1e-6)
    try:
        with decode_log.open("wb") as de, encode_log.open("wb") as en:
            decode = [
                "ffmpeg",
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
                "ffmpeg",
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
            if args.encoder == "h264_nvenc":
                encode += [
                    "-c:v",
                    "h264_nvenc",
                    "-preset",
                    "p5",
                    "-tune",
                    "hq",
                    "-rc",
                    "vbr",
                    "-cq",
                    "18",
                    "-b:v",
                    "0",
                ]
            else:
                encode += ["-c:v", "libx264", "-preset", "fast", "-crf", "18"]
            encode += [
                "-vf",
                "setsar=1",
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
            decoder = subprocess.Popen(
                decode, stdout=subprocess.PIPE, stderr=de, bufsize=10**7
            )
            encoder = subprocess.Popen(
                encode, stdin=subprocess.PIPE, stderr=en, bufsize=10**7
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
                    mask_decoder = subprocess.Popen(
                        [
                            "ffmpeg",
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
                    )
            print(
                f"GPU: {gpu_name}; {w}x{h}/{fps:g} fps; decode {dw}x{dh}; {expected} frames",
                flush=True,
            )
            while frame_count < expected:
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
                    frame_count / fps,
                    not args.no_effect,
                    not args.no_filter,
                    mask,
                )
                process_times.append((time.perf_counter() - begin) * 1000)
                gpu_times.append(renderer.last_gpu_ms)
                encoder.stdin.write(result.tobytes())
                frame_count += 1
                if frame_count % 30 == 0:
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
        output.with_suffix(".render.json").write_text(
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


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("input", nargs="?")
    p.add_argument("output", nargs="?")
    p.add_argument(
        "--batch", type=Path, help="JSON [{input,output,preset?,overrides?}]"
    )
    p.add_argument("--preset", default="capcut-pentagon")
    p.add_argument("--cache", type=Path, default=ROOT / "cache")
    p.add_argument(
        "--seconds", type=float, default=3, help="Mặc định 3 giây; --full để xuất hết"
    )
    p.add_argument("--full", action="store_true")
    p.add_argument("--width", type=int)
    p.add_argument("--height", type=int)
    p.add_argument("--set", action="append", default=[], metavar="KEY=JSON")
    p.add_argument("--encoder", choices=("h264_nvenc", "libx264"), default="h264_nvenc")
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
