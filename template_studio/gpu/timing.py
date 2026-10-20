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


def video_windows(timeline, position, seconds, fps):
    """Giữ một lưới FPS chung qua các điểm bỏ đoạn, không cộng frame ở mỗi mối nối."""
    result = []
    for window in timeline.windows(position, seconds):
        first = math.ceil((window["start"] - position)*fps - 1e-6)
        last = math.ceil((window["start"] + window["seconds"] - position)*fps - 1e-6)
        if last > first:
            offset = window["source"] + (position + first/fps - window["start"])*timeline.rate
            result.append(dict(source=offset, frames=last-first))
    return result


def edited_audio_window(timeline, position, seconds, delay_ms=0, part_start=0):
    """Nối âm thanh trước khi bù trễ; preview giữa part dùng lại âm thanh trước mốc."""
    delay = delay_ms / 1000
    rewind = min(delay, max(0, position-part_start)) if delay > 0 else delay
    padding = max(0, delay-rewind)
    windows = timeline.windows(position-rewind, max(0, seconds-padding))
    if not windows:
        return 0, f"anullsrc=r=48000:cl=stereo,atrim=duration={seconds:.12f}[audio]"
    seek = windows[0]["source"]
    count = len(windows)
    filters = []
    if count > 1:
        filters.append(f"[1:a:0]asplit={count}" + "".join(f"[a{i}]" for i in range(count)))
    for i, window in enumerate(windows):
        a = window["source"] - seek
        b = a + window["seconds"]*timeline.rate
        label = f"[a{i}]" if count > 1 else "[1:a:0]"
        filters.append(f"{label}atrim=start={a:.12f}:end={b:.12f},asetpts=PTS-STARTPTS,"
                       f"apad,atrim=duration={b-a:.12f},"
                       f"asetpts=N/SR/TB[s{i}]")
    tail = "".join(f"[s{i}]" for i in range(count))
    tail += f"concat=n={count}:v=0:a=1" if count > 1 else "anull"
    # Đổi tốc độ một lần sau nối, tránh tạo đệm atempo ở từng mối cắt.
    tail += f",atempo={timeline.rate:.15g},asetpts=N/SR/TB"
    if padding:
        # Concat dùng timebase microsecond; căn lại mẫu để giữ đủ khoảng lặng adelay.
        tail += f",adelay={padding*1000:.6f}:all=1,aresample=async=1:first_pts=0"
    filters.append(tail + f",apad,atrim=duration={seconds:.12f}[audio]")
    return seek, ";".join(filters)
