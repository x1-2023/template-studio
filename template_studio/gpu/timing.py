"""Giữ mốc nguồn khi seek giữa khung, tránh đặt lại pha FPS ở mỗi part."""

import math


def decode_window(video, container, offset, rate, fps, width, height):
    """Seek sớm một giây, giữ PTS rồi đặt gốc tại đúng mốc được yêu cầu."""
    video_start = float(video.get("start_time", container.get("start_time", 0)))
    container_start = float(container.get("start_time", 0))
    origin = video_start - container_start
    if not all(math.isfinite(x) for x in (origin, offset, rate)) or offset < 0 or rate <= 0:
        raise ValueError("Mốc decode không hợp lệ.")
    anchor = origin + offset
    seek = max(0.0, anchor - 1.0)
    filters = (f"setpts=(PTS-({anchor:.12f})/TB)/{rate:.15g},"
               f"fps={fps:g}:start_time=0:round=up,scale={width}:{height},setsar=1")
    return seek, filters


def audio_window(offset, rate, seconds, delay_ms=0, part_start=0):
    """Dịch âm thanh trên trục part; preview giữa part không chèn lại khoảng lặng."""
    if not all(math.isfinite(x) for x in (offset, rate, seconds, delay_ms, part_start)) or rate <= 0 or seconds <= 0:
        raise ValueError("Mốc âm thanh không hợp lệ.")
    delay = delay_ms / 1000
    available = max(0.0, (offset - part_start) / rate)
    rewind = min(delay, available) if delay > 0 else delay
    seek = max(0.0, offset - rewind * rate)
    padding = max(0.0, delay - rewind)
    filters = f"atempo={rate:.15g},asetpts=PTS-STARTPTS"
    if padding:
        filters += f",adelay={padding * 1000:.6f}:all=1"
    return seek, filters + f",apad,atrim=duration={seconds:.12f}"
