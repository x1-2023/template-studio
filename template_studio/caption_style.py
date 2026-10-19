"""Quy tắc màu/emoji minh bạch, áp dụng cho mọi video có lời thoại."""

import re
import unicodedata
from bisect import bisect_right

from pathlib import Path

import numpy as np
from PIL import Image

ASSETS = Path(__file__).resolve().parent / "assets/emoji"

# Màu và biểu tượng được chọn theo từ, không dùng lời của video mẫu làm preset.
RULES = (
    ("1f4b0", "FFFF00", "money|pay|paid|salary|cash|dollar|price|cost|tiền|lương"),
    ("1f3e0", "00FF00", "home|house|residence|apartment|nhà"),
    ("1f4bc", "FFFF00", "job|work|business|career|công việc"),
    ("1f681", "FFFF00", "helicopter|trực thăng"),
    ("1f50e", "00FF00", "investigation|investigate|research|evidence|điều tra"),
    ("1f3c0", "FFFF00", "basketball|nba|knicks|sixers|team|bóng rổ"),
    ("1f4c5", "FFFF00", "monday|tuesday|wednesday|thursday|friday|saturday|sunday|january|february|march|april|may|june|july|august|september|october|november|december|date|year|month|ngày|tháng|năm"),
    ("1f44d", "FFFF00", "accept|accepted|agree|yes|okay|good|đồng ý"),
    ("1f389", "FFFF00", "ladies|gentlemen|welcome|celebrate|party|chúc mừng"),
    ("1f914", "FFFF00", "think|thought|question|why|what|how|because|tại sao"),
    ("1f4cd", "00FF00", "new york|philadelphia|city|location|place|thành phố"),
    ("1f4f0", "FFFF00", "news|journalism|journalist|report|báo chí"),
    ("1f91d", "00FF00", "partnership|partner|together|friend|bạn bè"),
    ("1f3a4", "FFFF00", "speak|speaking|voice|talk|said|nói"),
)


def token_key(text):
    text = unicodedata.normalize("NFD", text.casefold().replace("đ", "d"))
    return " ".join(re.findall(r"[a-z0-9]+", "".join(c for c in text if not unicodedata.combining(c))))


def keyword_style(group):
    matches = {}
    emoji = None
    tokens, owners = [], []
    for i, word in enumerate(group):
        keys = token_key(word["text"]).split()
        tokens.extend(keys)
        owners.extend([i]*len(keys))
    for icon, color, terms in RULES:
        for term in terms.split("|"):
            phrase = token_key(term).split()
            for start in range(len(tokens)-len(phrase)+1):
                if tokens[start:start+len(phrase)] == phrase:
                    for owner in owners[start:start+len(phrase)]:
                        matches.setdefault(owner, color)
                    if emoji is None:
                        emoji = icon
    return matches, emoji


class EmojiTrack:
    """Ghép một ảnh RGBA nhỏ; không sao chép toàn bộ canvas ở mỗi frame."""

    def __init__(self, groups, width, height, angle=-11, y_ratio=.66534):
        self.cues = []
        self.images = {}
        for group, end in groups:
            _, icon = keyword_style(group)
            if icon:
                self.cues.append((max(0, group[0]["start"]), end, icon))
        self.starts = [cue[0] for cue in self.cues]
        self.x, self.y = round(width*.65), round(height*(y_ratio+.067))
        self.size, self.angle = max(24, round(height*.046)), angle

    def apply(self, frame, time):
        index = bisect_right(self.starts, time)-1
        if index < 0 or time >= self.cues[index][1]:
            return frame
        icon = self.cues[index][2]
        if icon not in self.images:
            with Image.open(ASSETS / (icon+".png")) as image:
                image = image.convert("RGBA").resize((self.size, self.size), Image.Resampling.LANCZOS)
                rgba = np.asarray(image.rotate(-self.angle, Image.Resampling.BICUBIC, expand=True)).astype(np.float32)
            self.images[icon] = (rgba[:, :, :3], rgba[:, :, 3:4]/255)
        rgb, alpha = self.images[icon]
        h, w = alpha.shape[:2]
        x, y = self.x-w//2, self.y-h//2
        region = frame[y:y+h, x:x+w]
        if region.shape != rgb.shape:
            return frame
        if not frame.flags.writeable:
            frame = frame.copy()
            region = frame[y:y+h, x:x+w]
        region[:] = np.clip(rgb*alpha+region*(1-alpha), 0, 255).astype(np.uint8)
        return frame
