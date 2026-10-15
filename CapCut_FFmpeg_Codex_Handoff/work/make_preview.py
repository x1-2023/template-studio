"""Video đối chiếu ba cột, giữ audio của bản tham chiếu."""

import subprocess

from align import MEDIA, ROOT
from PIL import Image, ImageDraw, ImageFont


def main():
    labels = Image.new("RGB", (1080, 32), "#151515")
    draw = ImageDraw.Draw(labels)
    font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 20)
    for i, label in enumerate(
        ("CapCut thật", "V7 đã căn bố cục / thời gian", "GPU shader gốc")
    ):
        draw.text((i * 360 + 8, 4), label, font=font, fill="white")
    label_path = ROOT / "artifacts/preview_labels.png"
    labels.save(label_path)
    inputs = [
        MEDIA / "capcut_export_test.mp4",
        ROOT / "artifacts/baseline_v7_aligned_1080_3s.mp4",
        ROOT / "artifacts/gpu_final_1080_3s.mp4",
    ]
    cmd = ["ffmpeg", "-v", "error", "-y"]
    for path in inputs:
        cmd += ["-i", str(path)]
    cmd += [
        "-loop",
        "1",
        "-i",
        str(label_path),
        "-filter_complex",
        (
            "[0:v]fps=30,scale=360:480,setsar=1[a];[1:v]scale=360:480,setsar=1[b];"
            "[2:v]scale=360:480,setsar=1[c];[a][b][c]hstack=inputs=3[panels];"
            "[3:v]fps=30[labels];[labels][panels]vstack=inputs=2[v]"
        ),
        "-map",
        "[v]",
        "-map",
        "0:a:0?",
        "-t",
        "3",
        "-c:v",
        "h264_nvenc",
        "-preset",
        "p5",
        "-cq",
        "18",
        "-b:v",
        "0",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-movflags",
        "+faststart",
        str(ROOT / "artifacts/preview_compare_3s.mp4"),
    ]
    subprocess.run(cmd, check=True)


if __name__ == "__main__":
    main()
