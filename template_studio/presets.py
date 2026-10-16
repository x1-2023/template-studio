"""Preset sản xuất đã chuẩn hóa; tách cấu hình đối chiếu khỏi mặc định 1×."""

import copy
import math
import re

# Tên và resource đối chiếu trong tài liệu bàn giao CapCut.
EFFECT_NAME = "Lớp phủ ngũ giác lấp lánh"  # 7491138615477685505
FILTER_NAME = "Camera độ nét cao 2"  # 7514206177195068689

PRESET_NAMES = {
    "pentagon-3x4": f"Ngũ giác + {FILTER_NAME} · 3:4",
    "pentagon-9x16": f"Ngũ giác + {FILTER_NAME} · 9:16",
    "color": f"Chỉ {FILTER_NAME} · 3:4",
    "layout": "Chỉ nền mờ · 9:16",
    "reference": "Theo video mẫu CapCut · 3:4",
}

BASE = dict(
    width=1080,
    height=1440,
    fps=30,
    flip=False,
    scale=1.0513,
    offset=[0, 0],
    playback_rate=1.0,
    source_offset=0.0,
    background_sigma_ratio=1 / 24,
    effect_start=0.0,
    effect_end=2.166667,
    effect_slider=1 / 3,
    ae_time_scale=1.0,
    bokeh_size=0.7,
    filter_stage="after",
    filter_start=0.0,
    filter_intensity=1.0,
    sharpness=0.6,
    intro_enabled=True,
    filter_enabled=True,
    encoder="auto",
    quality="standard",
    video_bitrate=9.65,
    skin="none",
    mute=False,
    resolution=1080,
)

SYSTEM = [
    dict(
        id="pentagon-3x4",
        name=PRESET_NAMES["pentagon-3x4"],
        description=f"{EFFECT_NAME} + {FILTER_NAME}. Tốc độ 1×, không lật ngang.",
        config={},
    ),
    dict(
        id="pentagon-9x16",
        name=PRESET_NAMES["pentagon-9x16"],
        description=f"{EFFECT_NAME} + {FILTER_NAME}. Bố cục theo draft 9:16, chưa có cặp video gốc để đối chiếu.",
        config=dict(
            height=1920,
            scale=0.8877484472,
            offset=[0.03188405797, 0],
            video_bitrate=12.0,
        ),
    ),
    dict(
        id="color",
        name=PRESET_NAMES["color"],
        description="Chỉ bộ lọc màu và độ nét; tắt hiệu ứng ngũ giác mở đầu.",
        config=dict(intro_enabled=False),
    ),
    dict(
        id="layout",
        name=PRESET_NAMES["layout"],
        description="Chỉ bố cục nền mờ; tắt hiệu ứng ngũ giác và bộ lọc Camera.",
        config=dict(
            height=1920,
            scale=0.8877484472,
            intro_enabled=False,
            filter_enabled=False,
            video_bitrate=12.0,
        ),
    ),
    dict(
        id="reference",
        name=PRESET_NAMES["reference"],
        description=f"{EFFECT_NAME} + {FILTER_NAME}. Lật ngang, tốc độ 1,02× theo cặp nguồn–CapCut đã đối chiếu.",
        config=dict(flip=True, playback_rate=1.02),
    ),
]

# Đổi nhãn snapshot cũ; giữ cấu hình và tên preset tự đặt.
LEGACY_NAMES = {
    "Ngũ giác 3:4": PRESET_NAMES["pentagon-3x4"],
    "Ngũ giác 9:16": PRESET_NAMES["pentagon-9x16"],
    "Màu và nét 3:4": PRESET_NAMES["color"],
    "Đối chiếu CapCut 3:4": PRESET_NAMES["reference"],
    f"{EFFECT_NAME} · 3:4": PRESET_NAMES["pentagon-3x4"],
    f"{EFFECT_NAME} · 9:16": PRESET_NAMES["pentagon-9x16"],
    f"{FILTER_NAME} · 3:4": PRESET_NAMES["color"],
    "Nền mờ 9:16": PRESET_NAMES["layout"],
    f"{EFFECT_NAME} · Đối chiếu 3:4": PRESET_NAMES["reference"],
}


def normalize(value):
    if not isinstance(value, dict) or any(key not in BASE for key in value):
        raise ValueError("Preset có trường không được hỗ trợ.")
    s = copy.deepcopy(BASE)
    s.update(copy.deepcopy(value))
    for key, lo, hi in [
        ("scale", 0.3, 1.5),
        ("playback_rate", 0.5, 2),
        ("background_sigma_ratio", 0, 0.1),
        ("effect_start", 0, 60),
        ("effect_end", 0, 120),
        ("effect_slider", 0, 1),
        ("ae_time_scale", 0.25, 4),
        ("bokeh_size", 0, 1.5),
        ("filter_intensity", 0, 1),
        ("sharpness", 0, 1),
        ("source_offset", 0, 3600),
        ("filter_start", 0, 3600),
        ("video_bitrate", 0.5, 100),
    ]:
        x = float(s[key])
        if not math.isfinite(x) or not lo <= x <= hi:
            raise ValueError(f"Thông số {key} ngoài khoảng {lo}–{hi}.")
        s[key] = x
    if s["effect_end"] < s["effect_start"]:
        raise ValueError("Thời điểm kết thúc intro phải sau bắt đầu.")
    if s["width"] not in (720, 1080) or s["height"] not in (960, 1280, 1440, 1920):
        raise ValueError("Khung xuất cần là 3:4 hoặc 9:16 ở 720/1080.")
    if (s["width"], s["height"]) not in (
        (720, 960),
        (720, 1280),
        (1080, 1440),
        (1080, 1920),
    ):
        raise ValueError("Tỷ lệ khung xuất không hợp lệ.")
    if s["fps"] != 30:
        raise ValueError("Bản này xuất 30 fps.")
    if not isinstance(s["offset"], list) or len(s["offset"]) != 2:
        raise ValueError("Vị trí clip không hợp lệ.")
    s["offset"] = [float(v) for v in s["offset"]]
    if any(not math.isfinite(v) or abs(v) > 0.5 for v in s["offset"]):
        raise ValueError("Vị trí X/Y phải trong ±50%.")
    for key in ("flip", "intro_enabled", "filter_enabled", "mute"):
        if not isinstance(s[key], bool):
            raise ValueError(f"{key} phải là boolean.")
    for key, choices in [
        ("encoder", ("auto", "h264_nvenc", "libx264")),
        ("quality", ("small", "standard", "high")),
        ("skin", ("none", "chroma")),
        ("filter_stage", ("before", "after")),
    ]:
        if s[key] not in choices:
            raise ValueError(f"Giá trị {key} không hợp lệ.")
    s["resolution"] = s["width"]
    return s


def catalog(custom=()):
    return [
        dict(
            id=p["id"],
            name=p["name"],
            description=p["description"],
            config=normalize(p["config"]),
            custom=False,
        )
        for p in SYSTEM
    ] + list(custom)


def safe_name(value):
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", str(value)).strip(" .")[:80]
    return name or "video"
