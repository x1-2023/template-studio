"""Ánh xạ đoạn nguồn được giữ sang thời gian xuất, dùng chung cho part và preview."""

import math


RANGE_KEYS = ("source_offset", "source_end", "source_skip")


def parse_time(value):
    """Nhận giây, phút:giây hoặc giờ:phút:giây; không tự sửa mốc nhập sai."""
    if not isinstance(value, str):
        raise ValueError("Nhập thời gian dạng 10:00 hoặc 00:10:00.")
    fields = value.strip().split(":")
    try:
        numbers = [float(item) for item in fields]
    except ValueError:
        raise ValueError("Nhập thời gian dạng 10:00 hoặc 00:10:00.") from None
    if not 1 <= len(numbers) <= 3 or any(not math.isfinite(n) or n < 0 for n in numbers):
        raise ValueError("Mốc thời gian không hợp lệ.")
    if len(numbers) > 1 and (any(n >= 60 for n in numbers[1:]) or
                             any(n != int(n) for n in numbers[:-1])):
        raise ValueError("Phút và giây sau dấu : phải nhỏ hơn 60.")
    seconds = sum(n * 60**i for i, n in enumerate(reversed(numbers)))
    if seconds > 86400:
        raise ValueError("Mốc thời gian tối đa là 24 giờ.")
    return seconds


def format_time(seconds):
    milliseconds = round(float(seconds) * 1000)
    whole, fraction = divmod(milliseconds, 1000)
    hours, rest = divmod(whole, 3600)
    minutes, secs = divmod(rest, 60)
    value = f"{hours:02}:{minutes:02}:{secs:02}" if hours else f"{minutes:02}:{secs:02}"
    return value + (f".{fraction:03}".rstrip("0") if fraction else "")


class SourceTimeline:
    def __init__(self, duration, config):
        duration = float(duration)
        self.rate = float(config.get("playback_rate", 1))
        start = float(config.get("source_offset", 0))
        end = min(duration, float(config.get("source_end", 0)) or duration)
        if not math.isfinite(duration) or duration <= 0 or not 0 <= start < end:
            raise ValueError("Đoạn đã chọn không còn nội dung trong video nguồn.")
        if not math.isfinite(self.rate) or self.rate <= 0:
            raise ValueError("Tốc độ video không hợp lệ.")
        self.spans = []
        cursor, output = start, 0.0
        for a, b in sorted(config.get("source_skip", [])):
            a, b = max(start, a), min(end, b)
            if b <= cursor or a >= end:
                continue
            if a > cursor:
                self.spans.append(dict(source=cursor, end=a, start=output))
                output += (a - cursor) / self.rate
            cursor = max(cursor, b)
        if cursor < end:
            self.spans.append(dict(source=cursor, end=end, start=output))
            output += (end - cursor) / self.rate
        if output <= 0:
            raise ValueError("Các khoảng bỏ đã xóa hết đoạn video được chọn.")
        self.duration = output

    def source_at(self, position):
        if not math.isfinite(position) or not 0 <= position < self.duration:
            raise ValueError("Mốc xem thử nằm ngoài đoạn video đã chọn.")
        for span in reversed(self.spans):
            if position >= span["start"]:
                return span["source"] + (position - span["start"]) * self.rate
        raise ValueError("Không tìm được mốc nguồn.")

    def windows(self, start, seconds):
        """Các khoảng nguồn cần đọc cho một cửa sổ trên trục video đã cắt."""
        stop = min(self.duration, start + seconds)
        windows = []
        for span in self.spans:
            end = span["start"] + (span["end"] - span["source"]) / self.rate
            a, b = max(start, span["start"]), min(stop, end)
            if b > a + 1e-9:
                windows.append(dict(start=a, seconds=b-a,
                                    source=span["source"] + (a-span["start"])*self.rate))
        return windows

    def map_words(self, words):
        result = []
        for span in self.spans:
            for word in words:
                a, b = max(word["start"], span["source"]), min(word["end"], span["end"])
                if b > a:
                    result.append({**word, "start": span["start"] + (a-span["source"])/self.rate,
                                   "end": span["start"] + (b-span["source"])/self.rate})
        return result
