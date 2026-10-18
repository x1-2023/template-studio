"""Đọc phụ đề SRT/JSON/Draft và tạo ASS karaoke đổi màu từng từ trên máy."""
from __future__ import annotations

import html
import json
import math
import re
import textwrap
from pathlib import Path

MAX_BYTES = 32 * 1024 * 1024
MAX_SEGMENTS = 50_000
_TS = re.compile(r"^(\d+):(\d{2}):(\d{2})[,.](\d{1,3})$")
_TAG = re.compile(r"<[^>]*>")


def _seconds(stamp):
    m = _TS.fullmatch(stamp.strip())
    if not m:
        raise ValueError(f"Mốc SRT không hợp lệ: {stamp!r}")
    h, mnt, sec, milli = m.groups()
    if int(mnt) > 59 or int(sec) > 59:
        raise ValueError("Mốc thời gian SRT không hợp lệ.")
    return int(h) * 3600 + int(mnt) * 60 + int(sec) + int(milli.ljust(3, "0")) / 1000


def _words_for_phrase(text, start, end):
    words = re.findall(r"\S+", html.unescape(_TAG.sub("", text)))
    if not words or end <= start:
        return []
    weights = [max(len(word.strip(".,!?")), 2) for word in words]
    duration, total = end - start, sum(weights)
    pos = start
    result = []
    for word, weight in zip(words, weights):
        stop = pos + duration * weight / total
        result.append(dict(text=word, start=pos, end=stop))
        pos = stop
    return result


def parse_srt(text):
    """Ước lượng thời gian từng từ từ thời gian cả dòng của SRT."""
    words = []
    for block in re.split(r"\n\s*\n", text.replace("\r\n", "\n").strip()):
        lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
        try:
            line = next(i for i, s in enumerate(lines) if "-->" in s)
        except StopIteration:
            continue
        left, right = lines[line].split("-->", 1)
        start, end = _seconds(left), _seconds(right.split()[0])
        words.extend(_words_for_phrase(" ".join(lines[line + 1:]), start, end))
    return words


def _extract_capcut_words(text, base, segment):
    times = text.get("words") or {}
    tokens, begins, ends = (times.get(k) or [] for k in ("text", "start_time", "end_time"))
    if not tokens or not (len(tokens) == len(begins) == len(ends)):
        return _words_for_phrase(text.get("recognize_text", ""), base, base + segment)
    words = []
    for tok, a, b in zip(tokens, begins, ends):
        # Mốc từng từ của CapCut dùng mili giây trong đoạn phụ đề.
        if not isinstance(tok, str) or not tok.strip():
            continue
        try:
            a, b = float(a), float(b)
        except (TypeError, ValueError):
            continue
        if not (math.isfinite(a) and math.isfinite(b) and 0 <= a <= b):
            continue
        start, end = base + a / 1000, base + b / 1000
        if end <= start:
            end = min(base + segment, start + 0.08)
        if end > start:
            words.append(dict(text=tok.strip(), start=start, end=end))
    return words


def parse_capcut_draft(draft):
    """Đọc các đoạn Draft lồng đang được tham chiếu, giữ vị trí và phần cắt."""
    result = []
    visited = set()

    def visit(node, offset=0.0, depth=0, clip_start=0.0, clip_end=float("inf")):
        if depth > 12:
            raise ValueError("Draft CapCut có quá nhiều cấp lồng.")
        if not isinstance(node, dict):
            return
        materials = node.get("materials") or {}
        text_map = {x["id"]: x for x in materials.get("texts", []) if isinstance(x, dict) and x.get("id")}
        template_map = {x["id"]: x for x in materials.get("text_templates", []) if isinstance(x, dict) and x.get("id")}
        drafts = {x["id"]: x["draft"] for x in materials.get("drafts", []) if isinstance(x, dict) and x.get("id") and isinstance(x.get("draft"), dict)}
        for track in node.get("tracks", []):
            for seg in track.get("segments", []):
                tr = seg.get("target_timerange") or {}
                src = seg.get("source_timerange") or {}
                start = offset + float(tr.get("start", 0)) / 1_000_000
                duration = float(tr.get("duration", 0)) / 1_000_000
                if duration <= 0:
                    continue
                template = template_map.get(seg.get("material_id"))
                if template and track.get("type") == "text":
                    for resource in template.get("text_info_resources", []):
                        txt = text_map.get(resource.get("text_material_id"))
                        if txt:
                            for word in _extract_capcut_words(txt, start, duration):
                                word["start"] = max(word["start"], start, clip_start)
                                word["end"] = min(word["end"], start + duration, clip_end)
                                if word["end"] > word["start"]:
                                    result.append(word)
                if track.get("type") == "video":
                    for ref in seg.get("extra_material_refs", []):
                        if ref in drafts:
                            if (seg.get("speed", 1) != 1 or
                                abs(float(src.get("duration", duration * 1_000_000)) / 1_000_000 - duration) > .001):
                                raise ValueError("Draft có đoạn lồng thay đổi tốc độ. Hãy xuất phụ đề SRT/JSON theo video đã xuất.")
                            key = (id(drafts[ref]), round(start, 6))
                            if key not in visited:
                                visited.add(key)
                                visit(drafts[ref], start - float(src.get("start", 0)) / 1_000_000,
                                      depth + 1, max(start, clip_start), min(start + duration, clip_end))
    visit(draft)
    if len(result) > MAX_SEGMENTS:
        raise ValueError("Phụ đề có quá nhiều từ.")
    return sorted(result, key=lambda x: (x["start"], x["end"]))


def _parse_timed_json(data):
    """Nhận danh sách từ có thời gian, cấu trúc words/segments hoặc Draft."""
    if isinstance(data, dict) and "materials" in data:
        return parse_capcut_draft(data)
    if isinstance(data, dict):
        flat = data.get("words")
        if flat is None:
            flat = [w for seg in data.get("segments", []) for w in seg.get("words", [])]
    else:
        flat = data
    if not isinstance(flat, list):
        raise ValueError("JSON cần có words/segments hoặc nội dung Draft CapCut.")
    result = []
    for x in flat:
        if not isinstance(x, dict):
            raise ValueError("Dữ liệu từ phụ đề không hợp lệ.")
        word = x.get("text", x.get("word", ""))
        if not isinstance(word, str) or len(word) > 2000:
            raise ValueError("Nội dung từ phụ đề không hợp lệ.")
        word = word.strip()
        try:
            a, b = float(x["start"]), float(x["end"])
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError("Thiếu mốc bắt đầu/kết thúc của từ phụ đề.") from error
        if not (math.isfinite(a) and math.isfinite(b) and 0 <= a < b):
            raise ValueError("Mốc thời gian của từ không hợp lệ.")
        if word:
            result.append(dict(text=word, start=a, end=b))
    return result


def load_words(source):
    path = Path(source)
    if path.stat().st_size > MAX_BYTES:
        raise ValueError("File phụ đề vượt 32 MiB.")
    if path.suffix.lower() == ".srt":
        words = parse_srt(path.read_text(encoding="utf-8-sig"))
    elif path.suffix.lower() == ".json":
        words = _parse_timed_json(json.loads(path.read_text(encoding="utf-8-sig")))
    else:
        raise ValueError("Phụ đề cần là SRT hoặc JSON có mốc từng từ/Draft CapCut.")
    if not words and path.suffix.lower() == ".json":
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        if isinstance(data, dict) and data.get("schema") == 1 and data.get("words") == []:
            return []
    if not words or len(words) > MAX_SEGMENTS:
        raise ValueError("File không có phụ đề hợp lệ hoặc vượt số từ cho phép.")
    return sorted(words, key=lambda x: (x["start"], x["end"]))


def _ass_time(seconds):
    centis = max(0, int(round(seconds * 100)))
    h, rest = divmod(centis, 360000)
    m, rest = divmod(rest, 6000)
    s, cs = divmod(rest, 100)
    return f"{h}:{m:02}:{s:02}.{cs:02}"


def _ass_text(value):
    return (value.replace("\\", "＼").replace("{", "｛").replace("}", "｝")
            .replace("\r", "").replace("\n", " "))


def _groups(words, max_words=4):
    """Chia nhóm từ ngắn để hiển thị karaoke hai dòng."""
    group = []
    for word in words:
        if group and (len(group) >= max_words or word["start"] - group[-1]["end"] > 0.65 or word["start"] - group[0]["start"] > 2.8):
            yield group
            group = []
        group.append(word)
        if word["text"].endswith((".", "?", "!")):
            yield group
            group = []
    if group:
        yield group


def write_ass(words, destination, width, height, *, source_offset=0.0,
              playback_rate=1.0, timeline_offset=0.0, font_name="Arial Black",
              red="FF374A", angle=-11.0, y_ratio=0.66534, max_words=6, title="", part_label="", duration=None):
    """Tạo ASS; source_offset tính theo nguồn, timeline_offset theo video xuất."""
    if not 0 < playback_rate <= 4 or not 0.1 <= y_ratio <= 0.9:
        raise ValueError("Thời gian hoặc vị trí phụ đề không hợp lệ.")
    if not 1 <= max_words <= 20 or any(c in font_name for c in ",\r\n{}"):
        raise ValueError("Phông chữ hoặc số từ mỗi nhóm không hợp lệ.")
    if duration is not None and (not math.isfinite(duration) or duration <= 0):
        raise ValueError("Thời lượng phụ đề phải là số dương hữu hạn.")
    if not re.fullmatch(r"[0-9a-fA-F]{6}", red):
        raise ValueError("Màu từ đang đọc cần theo dạng RRGGBB.")
    r, g, b = red[:2], red[2:4], red[4:]
    highlight = f"{b}{g}{r}"
    base = float(source_offset) + float(timeline_offset) * float(playback_rate)
    # Cỡ chữ ASS tính bằng pixel theo PlayResY.
    size = max(18, round(height * 0.05))
    x, y = round(width / 2), round(height * y_ratio)
    heading = ("[Script Info]\nScriptType: v4.00+\nScaledBorderAndShadow: yes\n"
               f"PlayResX: {width}\nPlayResY: {height}\nWrapStyle: 2\n\n"
               "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
               f"Style: Karaoke,{font_name},{size},&H00FFFFFF,&H00FFFFFF,&H00000000,&H90000000,-1,0,0,0,80,100,0,0,1,4.5,2.0,5,40,40,30,1\n"
               f"Style: Header,{font_name},{max(22,round(height*.043))},&H00FFFFFF,&H00FFFFFF,&H003300A2,&H003300A2,-1,0,0,0,80,100,0,0,3,10,0,5,40,40,30,1\n"
               f"Style: Part,{font_name},{max(18,round(height*.043))},&H00FFFFFF,&H00FFFFFF,&H003300A2,&H003300A2,-1,0,0,0,80,100,0,0,3,10,0,5,40,40,30,1\n\n"
               "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
    lines = [heading]
    # Tiêu đề và nhãn phần giữ suốt thời lượng video đang render.
    last_end = max((float(w["end"]) for w in words), default=0)
    visible_end = float(duration) if duration is not None else max(0.0, (last_end - base) / playback_rate)
    for style, value, yy in (("Header", title, .14066), ("Part", part_label, .85461)):
        if value and visible_end > 0:
            paragraphs = value.upper().replace(r"\n", "\n").splitlines()
            chunks = [line for paragraph in paragraphs for line in textwrap.wrap(paragraph, 32)]
            content = r"\N".join(_ass_text(line) for line in chunks)
            # ASS xoay dương ngược kim đồng hồ; Draft dùng dấu âm cho cùng hướng.
            anchor = rf"{{\an5\pos({x},{round(height*yy)})\frz{-angle*.9893:.2f}}}"
            lines.append(f"Dialogue: 0,0:00:00.00,{_ass_time(visible_end)},{style},,0,0,0,,{anchor}{content}\n")
    for group in _groups(words, max_words=max_words):
        mapped = [dict(x, start=(x["start"] - base) / playback_rate,
                       end=(x["end"] - base) / playback_rate) for x in group]
        if mapped[-1]["end"] <= 0:
            continue
        boundaries = sorted({max(0, min(visible_end, w[key])) for w in mapped for key in ("start", "end")})
        for start, end in zip(boundaries, boundaries[1:]):
            if end <= start or end <= 0:
                continue
            active_index = next((i for i, w in enumerate(mapped) if w["start"] <= start < w["end"]), None)
            parts = []
            split_at = (len(mapped) + 1) // 2 if len(mapped) > 2 else 0
            for j, word in enumerate(mapped):
                if j == split_at:
                    parts.append(r"\N")
                elif j:
                    parts.append(" ")
                token = _ass_text(word["text"].upper())
                if j == active_index:
                    parts.append(r"{\c&H" + highlight + "&}" + token + r"{\c&HFFFFFF&}")
                else:
                    parts.append(token)
            layout = rf"{{\an5\pos({x},{y})\frz{-angle:.2f}}}"
            lines.append(f"Dialogue: 0,{_ass_time(start)},{_ass_time(end)},Karaoke,,0,0,0,,{layout}{''.join(parts)}\n")
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(lines), encoding="utf-8-sig")
    return path


def find_caption_file(video):
    """Tìm phụ đề cùng tên video khi xuất nhiều nguồn độc lập."""
    video = Path(video)
    for suffix in (".words.json", ".srt"):
        sidecar = video.with_name(video.stem + suffix)
        if sidecar.is_file():
            return sidecar
    return None


