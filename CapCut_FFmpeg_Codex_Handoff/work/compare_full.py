"""So ba bản đầy đủ thời lượng; cột nguồn được lật/căn thời gian và giữ hình nguyên."""

import subprocess

from align import MEDIA, ROOT
from PIL import Image, ImageDraw, ImageFont
from render import load_preset, probe


def main():
    config = load_preset("capcut-pentagon")
    gpu = ROOT / "artifacts/gpu_full_capcut_bitrate.mp4"
    reference = MEDIA / "capcut_export_test.mp4"
    video = next(s for s in probe(gpu)["streams"] if s["codec_type"] == "video")
    seconds = video["duration"]
    labels = Image.new("RGB", (1080, 32), "#151515")
    draw = ImageDraw.Draw(labels)
    font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 18)
    for i, label in enumerate(
        (
            "Nguồn · lật / đồng bộ thời gian",
            "CapCut thật",
            "GPU của chúng ta · 9,65 Mb/s",
        )
    ):
        draw.text((i * 360 + 8, 5), label, font=font, fill="white")
    label_path = ROOT / "artifacts/full_labels.png"
    labels.save(label_path)
    cmd = ["ffmpeg", "-v", "error", "-y"]
    for path in (MEDIA / "source_original_compre_juguetes.mp4", reference, gpu):
        cmd += ["-i", str(path)]
    cmd += [
        "-loop",
        "1",
        "-i",
        str(label_path),
        "-filter_complex",
        (
            f"[0:v]setpts=(PTS-STARTPTS)/{config['playback_rate']},fps=30:round=up,hflip,"
            "scale=270:480,pad=360:480:45:0:black,setsar=1[a];"
            "[1:v]fps=30,scale=360:480,setsar=1[b];[2:v]scale=360:480,setsar=1[c];"
            "[a][b][c]hstack=inputs=3[panels];[3:v]fps=30[labels];"
            "[labels][panels]vstack=inputs=2[v]"
        ),
        "-map",
        "[v]",
        "-map",
        "1:a:0?",
        "-t",
        str(seconds),
        "-c:v",
        "h264_nvenc",
        "-preset",
        "p5",
        "-rc",
        "vbr",
        "-b:v",
        "6M",
        "-maxrate",
        "9M",
        "-bufsize",
        "18M",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-movflags",
        "+faststart",
        str(ROOT / "artifacts/compare_source_capcut_gpu_full.mp4"),
    ]
    subprocess.run(cmd, check=True)


if __name__ == "__main__":
    main()
