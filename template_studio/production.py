"""Điều phối màn hình sản xuất gọn: nguồn → preset → worker → đầu ra."""

import copy
import csv
import hashlib
import json
import shutil
import threading
import time
import uuid
from pathlib import Path

from PySide6.QtCore import Property, QObject, QUrl, Signal, Slot
from PySide6.QtGui import QColor, QDesktopServices
from PySide6.QtWidgets import QColorDialog, QFileDialog

from offline_studio.cancellation import TaskCancelled, check_cancelled
from offline_studio.config import atomic_json
from offline_studio.process import probe

from .assets_local import discover, import_cache, validate
from .gpu.resources import bundled_cache
from .output_files import archive_output_artifacts, reports_directory
from .parts import plan_source_parts, render_parts
from .speech import prepare_captions
from .presets import (
    DEFAULT_PRESET_ID, EFFECT_NAME, FILTER_NAME, LEGACY_NAMES,
    catalog, main_catalog, normalize, safe_name, tiktok_config, tiktok_name,
)
from .version import VERSION
from .worker_client import run_worker

EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".flv", ".m4v"}


def fingerprint(source, config):
    path = Path(source)
    stamp = path.stat()
    payload = dict(
        path=str(path.resolve()),
        bytes=stamp.st_size,
        modified=stamp.st_mtime_ns,
        config=config,
        version=VERSION,
    )
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


class Production(QObject):
    changed = Signal()

    def __init__(self, host):
        super().__init__(host)
        self.host, self.home, self.root = host, host.home, host.root
        self.pool = host.pool
        self._rows = []
        self._custom = []
        self._config = main_catalog()[0]["config"]
        self._preset = DEFAULT_PRESET_ID
        self._output = str(self.home / "exports")
        self._index = -1
        self._preview = ""
        self._preview_key = ""
        self._mode = "result"
        self._runtime = "Đang kiểm tra GPU…"
        self._gpu = ""
        self._ready = False
        self._cache = ""
        self._stop_after = threading.Event()
        self._selected = set()
        self._active = False
        self._total = 0
        self._completed = 0
        self._state = self.home / "production.json"
        try:
            saved = json.loads(self._state.read_text(encoding="utf-8-sig"))
            if saved.get("schema") != 1:
                raise ValueError("Phiên bản dữ liệu không được hỗ trợ.")
            configs = [saved["config"], *(row.get("config", {}) for row in saved.get("rows", []))]
            if any("part_count" not in config for config in configs):
                backup = self.home / "production-before-karaoke.json"
                if not backup.exists():
                    shutil.copy2(self._state, backup)
            self._config = normalize(saved["config"])
            self._preset = saved.get("preset", DEFAULT_PRESET_ID)
            self._output = str(saved["output"])
            self._custom = [
                dict(
                    id=str(p["id"]),
                    name=str(p["name"])[:80],
                    description="Preset đã lưu",
                    config=normalize(p["config"]),
                    custom=True,
                )
                for p in saved.get("custom", [])
            ]
            self._rows = saved.get("rows", [])
            for row in self._rows:
                if row["status"] == "Đang xuất":
                    row.update(
                        status="Đã dừng",
                        percent=0,
                        detail="Chạy tiếp để xuất lại file này.",
                    )
                if row["status"] != "Hoàn tất" and not Path(row["path"]).is_file():
                    row.update(status="Thiếu nguồn", detail="Nguồn đã bị dời hoặc xóa.")
                row["config"] = normalize(row.get("config", self._config))
                row.setdefault("presetName", self.presetName)
            self._index = 0 if self._rows else -1
            if saved.get("production_defaults") != "tiktok":
                self.migrate_tiktok_defaults()
        except FileNotFoundError:
            if host._rows:
                legacy = self.home / "session.json"
                if (
                    legacy.is_file()
                    and not (self.home / "session-before-1.1.json").exists()
                ):
                    shutil.copy2(legacy, self.home / "session-before-1.1.json")
                self._output = host.output
                for old in host._rows:
                    self._rows.append(
                        dict(
                            id=uuid.uuid4().hex,
                            path=old["path"],
                            name=old["name"],
                            status=old["status"]
                            if old["status"] == "Hoàn tất"
                            else "Chờ xử lý",
                            percent=100 if old["status"] == "Hoàn tất" else 0,
                            detail="Nhập từ phiên bản cũ",
                            result=old.get("result", ""),
                            duration=0,
                            meta="",
                            config=copy.deepcopy(self._config),
                            presetName="Phiên bản cũ"
                            if old["status"] == "Hoàn tất"
                            else self.presetName,
                        )
                    )
                self._index = 0
        except (OSError, ValueError, KeyError, TypeError) as error:
            if self._state.exists():
                shutil.copy2(
                    self._state,
                    self.home / f"production-invalid-{uuid.uuid4().hex[:8]}.json",
                )
            host.message("Đã giữ bản sao cấu hình lỗi: " + str(error))
            self._rows = []
        host.changed.connect(self.changed.emit)

    def save(self):
        atomic_json(
            self._state,
            dict(
                schema=1,
                production_defaults="tiktok",
                config=self._config,
                preset=self._preset,
                output=self._output,
                custom=self._custom,
                rows=self._rows,
            ),
        )

    def migrate_tiktok_defaults(self):
        backup = self.home / "production-before-tiktok.json"
        if not backup.exists():
            shutil.copy2(self._state, backup)
        self._config = tiktok_config(self._config)
        self._preset = {
            "pentagon-3x4": DEFAULT_PRESET_ID,
            "reference": DEFAULT_PRESET_ID,
            "color": "color-9x16",
        }.get(self._preset, self._preset)
        custom_names = {p["name"] for p in self._custom}
        system_names = set(LEGACY_NAMES) | set(LEGACY_NAMES.values()) | {p["name"] for p in catalog()}
        for row in self._rows:
            if row["status"] == "Hoàn tất":
                continue
            try:
                row["config"] = tiktok_config(row["config"])
                if row["presetName"] in system_names and row["presetName"] not in custom_names:
                    row["presetName"] = tiktok_name(row["config"])
            except (ValueError, TypeError, KeyError) as error:
                row.update(status="Lỗi", detail="Cần chỉnh lại cấu hình: " + str(error))
        self.save()
        self.host.message("Đã chuyển cấu hình sang khung dọc 9:16 cho TikTok. Cấu hình cũ đã được sao lưu.")

    @Property("QVariantList", notify=changed)
    def rows(self):
        custom_names = {p["name"] for p in self._custom}
        items = []
        for row in self._rows:
            name = row.get("presetName", "")
            if name not in custom_names:
                name = LEGACY_NAMES.get(name, name)
            items.append({**row, "presetName": name, "selected": row["id"] in self._selected})
        return items

    @Property(str, constant=True)
    def effectName(self):
        return EFFECT_NAME

    @Property(str, constant=True)
    def filterName(self):
        return FILTER_NAME

    @Property("QVariantList", notify=changed)
    def presets(self):
        return catalog(self._custom)

    @Property("QVariantList", notify=changed)
    def mainPresets(self):
        return main_catalog(self._custom)

    @Property("QVariantMap", notify=changed)
    def config(self):
        return self._config

    @Property(str, notify=changed)
    def presetId(self):
        return self._preset

    @Property(str, notify=changed)
    def presetName(self):
        return next(
            (p["name"] for p in catalog(self._custom) if p["id"] == self._preset),
            "Tùy chỉnh",
        )

    @Property(str, notify=changed)
    def output(self):
        return self._output

    @Property(int, notify=changed)
    def currentIndex(self):
        return self._index

    @Property(str, notify=changed)
    def runtimeNotice(self):
        return self._runtime

    @Property(bool, notify=changed)
    def ready(self):
        return self._ready and self.host.mediaReady

    @Property(bool, notify=changed)
    def batchRunning(self):
        return self._active

    @Property(str, notify=changed)
    def gpu(self):
        return self._gpu

    @Property(str, notify=changed)
    def cachePath(self):
        return self._cache

    @Property(str, notify=changed)
    def previewUrl(self):
        if self._mode == "source" and self._index >= 0:
            return QUrl.fromLocalFile(self._rows[self._index]["path"]).toString()
        return self._preview

    @Property(bool, notify=changed)
    def previewStale(self):
        return bool(self._preview) and self._preview_key != self.preview_signature()

    @Property(bool, notify=changed)
    def sourceMode(self):
        return self._mode == "source"

    @Property(str, notify=changed)
    def summary(self):
        done = sum(r["status"] == "Hoàn tất" for r in self._rows)
        errors = sum(r["status"] in ("Lỗi", "Thiếu nguồn") for r in self._rows)
        if not self._rows:
            return "Chưa có video"
        parts = [f"{len(self._rows)} video"]
        if done:
            parts.append(f"{done} đã xuất")
        if errors:
            parts.append(f"{errors} lỗi")
        return ", ".join(parts)

    @Property(float, notify=changed)
    def overall(self):
        if not self._rows:
            return 0
        total = sum(max(1, r.get("duration", 0)) for r in self._rows)
        return (
            sum(max(1, r.get("duration", 0)) * r["percent"] for r in self._rows) / total
        )

    @Property(str, notify=changed)
    def estimate(self):
        duration = sum(
            r.get("duration", 0) / r["config"]["playback_rate"]
            for r in self._rows
            if r["status"] != "Hoàn tất"
        )
        if not duration:
            return ""
        if self._config["quality"] == "high":
            return "Dung lượng tùy nội dung video."
        bitrate = self._config["video_bitrate"] * (
            0.6 if self._config["quality"] == "small" else 1
        )
        return f"Dung lượng xuất dự kiến: {duration * (bitrate + 0.192) * 1_000_000 / 8 / 1024**2:.0f} MiB"

    def preview_signature(self):
        return json.dumps(
            [self._rows[self._index]["path"] if self._index >= 0 else "", self._config],
            sort_keys=True,
        )

    def finish(self):
        for r in self._rows:
            if r["status"] == "Đang xuất":
                r.update(status="Đã dừng", percent=0, detail="Có thể chạy tiếp.")
        self._active = False
        self.host._busy = False
        self.save()
        self.changed.emit()
        self.host.changed.emit()
        if self.host._closing:
            self.host.close_when_ready()

    def task_event(self, event):
        if "row" in event:
            row = next(r for r in self._rows if r["id"] == event["row"])
            row.update(event["values"])
            if event.get("save"):
                self.save()
        if "notice" in event:
            self.host.message(event["notice"])
        self.changed.emit()

    @Slot()
    def checkRuntime(self):
        if self.host.busy:
            return
        self.host._busy = True
        self._runtime = "Đang kiểm tra GPU và tài nguyên…"
        self.changed.emit()
        self.host.changed.emit()

        def work(emit):
            archive_output_artifacts(self._output, self.home)
            cache = discover(self.root, self.home)
            if (
                cache
                and cache.resolve() != (self.home / "runtime/capcut-cache").resolve()
                and cache.resolve() != bundled_cache(self.root).resolve()
            ):
                cache = import_cache(cache, self.home)
            health = run_worker(
                self.root, self.home, dict(action="health", timeout=120)
            )
            if cache:
                validate(cache)
            return dict(cache=str(cache) if cache else "", **health)

        def done(result):
            self._gpu = result["gpu"]
            self._cache = result["cache"]
            self._ready = bool(self._cache)
            self._runtime = (
                "GPU: " + self._gpu
                if self._ready
                else "Chưa có hiệu ứng. Mở Cài đặt để nhập gói CapCut."
            )
            self.host.message(
                ("Sẵn sàng xuất video." if self._rows else "Thêm video để bắt đầu.")
                if self._ready
                else self._runtime
            )

        def fail(error):
            self._ready = False
            self._runtime = error
            self.host.message(error)

        self.pool.submit(work, result=done, error=fail, finished=self.finish)

    @Slot()
    def importAssets(self):
        if self.host.busy:
            return
        path, _ = QFileDialog.getOpenFileName(
            None, "Chọn file hiệu ứng CapCut", "", "File RAR (*.rar)"
        )
        if path:
            self.install_assets(path)

    @Slot()
    def importAssetsFolder(self):
        if self.host.busy:
            return
        path = QFileDialog.getExistingDirectory(None, "Chọn thư mục hiệu ứng CapCut")
        if path:
            self.install_assets(path)

    def install_assets(self, path):
        self.host._busy = True
        self.host.message("Đang nhập hiệu ứng…")

        def done(cache):
            self._cache = str(cache)
            self._ready = bool(self._gpu)
            self._runtime = (
                "GPU: " + self._gpu
                if self._ready
                else "Đã nhập hiệu ứng. Bấm Kiểm tra GPU để tiếp tục."
            )
            self.host.message("Đã nhập hiệu ứng." if self._ready else self._runtime)

        self.pool.submit(
            lambda emit: import_cache(path, self.home),
            result=done,
            error=self.host.message,
            finished=self.finish,
        )

    @Slot(str)
    def choosePreset(self, slug):
        if self.host.busy:
            return
        item = next((p for p in self.presets if p["id"] == slug), None)
        if item:
            self._preset = slug
            self._config = copy.deepcopy(item["config"])
            self.apply_pending()

    def apply_pending(self):
        for row in self._rows:
            if row["status"] != "Hoàn tất":
                row["config"] = copy.deepcopy(self._config)
                row["presetName"] = self.presetName
        self.save()
        self.changed.emit()

    @Slot(str, "QVariant")
    def configure(self, key, value):
        if self.host.busy:
            return
        try:
            config = copy.deepcopy(self._config)
            if key == "aspect":
                config["height"] = round(
                    config["width"] * (16 / 9 if value == "9:16" else 4 / 3)
                )
            elif key == "resolution":
                ratio = config["height"] / config["width"]
                config["width"] = int(value)
                config["height"] = round(int(value) * ratio)
            elif key in ("offsetX", "offsetY"):
                config["offset"][0 if key == "offsetX" else 1] = float(value)
            else:
                config[key] = value
            self._config = normalize(config)
            self.apply_pending()
        except (ValueError, TypeError) as error:
            self.host.message(str(error))

    @Slot("QVariantMap", result=bool)
    def applyConfig(self, value):
        if self.host.busy:
            return False
        try:
            config = normalize(value)
        except (ValueError, TypeError) as error:
            self.host.message(str(error))
            return False
        self._config = config
        self.apply_pending()
        return True

    @Slot(str)
    def savePreset(self, name):
        if self.host.busy or not name.strip():
            return
        item = dict(
            id="custom-" + uuid.uuid4().hex,
            name=name.strip()[:80],
            description="Preset của bạn",
            config=copy.deepcopy(self._config),
            custom=True,
        )
        self._custom.append(item)
        self._preset = item["id"]
        self.apply_pending()

    @Slot()
    def exportPreset(self):
        if self.host.busy:
            return
        path, _ = QFileDialog.getSaveFileName(
            None, "Xuất preset", safe_name(self.presetName) + ".json", "Preset (*.json)"
        )
        if path:
            try:
                atomic_json(path, dict(name=self.presetName, config=self._config))
            except OSError as error:
                self.host.message(str(error))

    @Slot()
    def importPreset(self):
        if self.host.busy:
            return
        path, _ = QFileDialog.getOpenFileName(
            None, "Nhập preset", "", "Preset (*.json)"
        )
        if not path:
            return
        try:
            if Path(path).stat().st_size > 64 * 1024:
                raise ValueError("Preset vượt 64 KiB.")
            item = json.loads(Path(path).read_text(encoding="utf-8-sig"))
            config = normalize(item["config"])
            self._config = config
            self.savePreset(str(item["name"]))
        except (OSError, ValueError, KeyError, TypeError) as error:
            self.host.message(str(error))

    @Slot()
    def importFiles(self):
        if self.host.busy:
            return
        paths, _ = QFileDialog.getOpenFileNames(
            None, "Thêm video", "", "Video (*.mp4 *.mov *.mkv *.webm *.avi *.m4v)"
        )
        self.add_paths(paths)

    @Slot()
    def importFolder(self):
        if self.host.busy:
            return
        path = QFileDialog.getExistingDirectory(None, "Thêm thư mục video")
        if path:
            self.add_paths([path])

    @Slot("QVariantList")
    def dropFiles(self, urls):
        if self.host.busy:
            return
        paths = []
        for value in urls:
            url = value if isinstance(value, QUrl) else QUrl(str(value))
            if url.isValid() and url.isLocalFile() and url.toLocalFile():
                paths.append(url.toLocalFile())
        if paths:
            self.add_paths(paths)

    def add_paths(self, paths):
        if self.host.busy or not paths:
            return
        seen = {r["path"].casefold() for r in self._rows}
        sources = []
        for raw in paths:
            path = Path(raw).resolve()
            items = path.iterdir() if path.is_dir() else [path]
            for item in sorted(items):
                if (
                    item.is_file()
                    and item.suffix.lower() in EXTENSIONS
                    and str(item.resolve()).casefold() not in seen
                ):
                    sources.append(item.resolve())
                    seen.add(str(item.resolve()).casefold())
        if not sources:
            return
        self.host._busy = True
        self.host.message("Đang đọc thông tin video…")
        snapshot = copy.deepcopy(self._config)
        title = self.presetName

        def work(emit):
            rows = []
            for path in sources[: max(0, 200 - len(self._rows))]:
                check_cancelled()
                row = dict(
                    id=uuid.uuid4().hex,
                    path=str(path),
                    name=path.name,
                    status="Chờ xử lý",
                    percent=0,
                    detail="",
                    duration=0,
                    meta="",
                    result="",
                    config=copy.deepcopy(snapshot),
                    presetName=title,
                )
                try:
                    data = probe(path)
                    video = next(
                        s for s in data["streams"] if s["codec_type"] == "video"
                    )
                    row["duration"] = float(video.get("duration", data["format"]["duration"]))
                    row["meta"] = (
                        f"{video['width']}×{video['height']} · {row['duration']:.1f}s"
                    )
                    if row["duration"] <= 0:
                        raise ValueError("Thời lượng nguồn không hợp lệ.")
                except TaskCancelled:
                    raise
                except (
                    ValueError,
                    OSError,
                    StopIteration,
                    KeyError,
                    RuntimeError,
                ) as error:
                    row.update(status="Lỗi", detail=str(error)[:600])
                rows.append(row)
            return rows

        def done(rows):
            self._rows.extend(rows)
            if self._index < 0 and self._rows:
                self._index = 0
            self.host.message("Đã đọc thông tin video.")

        self.pool.submit(
            work, result=done, error=self.host.message, finished=self.finish
        )

    @Slot(int)
    def select(self, index):
        if 0 <= index < len(self._rows):
            self._index = index
            self._mode = "result"
            result = self._rows[index].get("result", "")
            self._preview = (
                QUrl.fromLocalFile(result).toString()
                if result and Path(result).is_file()
                else ""
            )
            self._preview_key = self.preview_signature() if self._preview else ""
            self.changed.emit()

    @Slot(int)
    def toggle(self, index):
        if self.host.busy:
            return
        token = self._rows[index]["id"]
        if token in self._selected:
            self._selected.remove(token)
        else:
            self._selected.add(token)
        self.changed.emit()

    @Slot()
    def removeSelected(self):
        if self.host.busy:
            return
        self._rows = [
            r
            for i, r in enumerate(self._rows)
            if not (
                r["id"] in self._selected or (not self._selected and i == self._index)
            )
        ]
        self._selected.clear()
        self._index = 0 if self._rows else -1
        self._preview = ""
        self.save()
        self.changed.emit()

    @Slot()
    def clearDone(self):
        if self.host.busy:
            return
        self._rows = [r for r in self._rows if r["status"] != "Hoàn tất"]
        self._index = 0 if self._rows else -1
        self._preview = ""
        self.save()
        self.changed.emit()

    @Slot()
    def retrySelected(self):
        if self.host.busy:
            return
        for row in self._rows:
            if (self._selected and row["id"] in self._selected) or (
                not self._selected and row["status"] in ("Lỗi", "Đã dừng")
            ):
                row.update(
                    status="Chờ xử lý",
                    percent=0,
                    detail="",
                    config=copy.deepcopy(self._config),
                    presetName=self.presetName,
                )
        self.save()
        self.changed.emit()

    @Slot()
    def chooseOutput(self):
        if self.host.busy:
            return
        path = QFileDialog.getExistingDirectory(None, "Nơi lưu video", self._output)
        if path:
            self._output = path
            self.save()
            self.changed.emit()

    @Slot(str, result=str)
    def chooseColor(self, current):
        if self.host.busy:
            return ""
        color = QColorDialog.getColor(QColor("#" + current.removeprefix("#")), None, "Chọn màu chữ")
        return color.name(QColor.NameFormat.HexRgb)[1:].upper() if color.isValid() else ""

    @Slot()
    def openOutput(self):
        Path(self._output).mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(self._output))

    @Slot()
    def openResult(self):
        if self._index >= 0:
            path = self._rows[self._index].get("result", "")
            if path and Path(path).is_file():
                QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    @Slot(int)
    def openPart(self, index):
        if self._index >= 0:
            paths = self._rows[self._index].get("parts", [])
            if 0 <= index < len(paths) and Path(paths[index]).is_file():
                QDesktopServices.openUrl(QUrl.fromLocalFile(paths[index]))

    @Slot(result=str)
    def chooseSubtitleFile(self):
        path, _ = QFileDialog.getOpenFileName(None, "Chọn phụ đề", "", "Phụ đề (*.srt *.json)")
        return path

    @Slot(result="QVariantMap")
    def chooseSubtitleFont(self):
        if self.host.busy:
            return {}
        path, _ = QFileDialog.getOpenFileName(
            None, "Chọn font phụ đề", "", "Font chữ (*.ttf *.otf *.ttc)"
        )
        if not path:
            return {}
        from .fonts import import_font
        try:
            return import_font(path, self.home)
        except (OSError, ValueError) as error:
            self.host.message(str(error))
            return {}

    @Slot(bool)
    def showSource(self, enabled):
        self._mode = "source" if enabled else "result"
        self.changed.emit()

    def request(self, source, output, config, preview=False, offset=0):
        encoder = config["encoder"]
        if encoder == "auto":
            encoder = "h264_nvenc" if self.host._nvenc else "libx264"
        bitrate = (
            None
            if config["quality"] == "high"
            else config["video_bitrate"] * (0.6 if config["quality"] == "small" else 1)
        )
        return dict(
            action="render",
            source=source,
            output=str(output),
            config=config,
            cache=self._cache,
            encoder=encoder,
            bitrate=bitrate,
            preview=preview,
            seconds=3 if preview else None,
            offset=offset,
        )

    @Slot(float)
    def preview(self, offset=0):
        if self.host.busy or self._index < 0:
            return
        if not self.ready:
            self.host.message(self._runtime)
            return
        source = self._rows[self._index]["path"]
        config = copy.deepcopy(self._config)
        folder = self.home / "cache/previews"
        folder.mkdir(parents=True, exist_ok=True)
        # Chỉ dọn preview do GUI này tạo, không đụng tới video nguồn/đầu ra.
        for old in sorted(
            folder.glob("gpu-*.mp4"), key=lambda item: item.stat().st_mtime
        )[:-4]:
            try:
                old.unlink()
                for suffix in (".render.json", ".decode.log", ".encode.log"):
                    old.with_suffix(suffix).unlink(missing_ok=True)
            except OSError:
                pass
        destination = folder / ("gpu-" + uuid.uuid4().hex + ".mp4")
        key = self.preview_signature()
        self.host._busy = True
        self.host.message("Đang dựng bản xem thử…")

        def done(result):
            self._preview = QUrl.fromLocalFile(result["output"]).toString()
            self._preview_key = key
            self._mode = "result"
            self.host.message("Đã tạo bản xem thử.")

        def work(emit):
            prepared = prepare_captions(self.root, self.home, source, config,
                                        lambda text: emit(dict(notice=text)))
            seconds = 3
            effect_offset = 0
            part_range = None
            if prepared["part_count"] != 1:
                intervals = plan_source_parts(source, prepared)
                index = max(i for i, part in enumerate(intervals) if part["start"] <= offset)
                part = intervals[index]
                seconds = min(3, part["start"] + part["seconds"] - offset)
                prepared = {**prepared, "subtitle_part_label": f"PART {index+1}"}
                effect_offset = part["start"]
                part_range = [part["start"], part["start"] + part["seconds"]]
            request = self.request(source, destination, prepared, True, offset)
            request["effect_offset"] = effect_offset
            request["part_range"] = part_range
            request["seconds"] = seconds
            return run_worker(
                self.root, self.home, request,
                lambda event: emit(dict(notice=f"Đang dựng bản xem thử: {event['percent']:.0f}%")),
            )

        self.pool.submit(
            work,
            result=done,
            error=self.host.message,
            event=self.task_event,
            finished=self.finish,
        )

    @Slot()
    def stopAfterFile(self):
        self._stop_after.set()
        self.host.message("Sẽ dừng sau video hiện tại.")

    @Slot()
    def runBatch(self):
        if self.host.busy:
            return
        if not self.ready:
            self.host.message(self._runtime)
            return
        for row in self._rows:
            if (
                row["status"] == "Hoàn tất"
                and row.get("result")
                and any(not Path(path).is_file() for path in row.get("parts", [row["result"]]))
            ):
                row.update(
                    status="Chờ xử lý",
                    percent=0,
                    detail="File kết quả không còn; sẽ xuất lại.",
                )
            elif (
                row["status"] == "Hoàn tất"
                and row.get("sourceStamp")
                and Path(row["path"]).is_file()
            ):
                stamp = Path(row["path"]).stat()
                if row["sourceStamp"] != [stamp.st_size, stamp.st_mtime_ns]:
                    row.update(
                        status="Chờ xử lý",
                        percent=0,
                        detail="Video nguồn đã đổi; sẽ xuất lại.",
                    )
        pending = [
            copy.deepcopy(r)
            for r in self._rows
            if r["status"] != "Hoàn tất"
            and (not self._selected or r["id"] in self._selected)
        ]
        if not pending:
            self.host.message("Không có video chờ xuất.")
            return
        output = Path(self._output)
        try:
            output.mkdir(parents=True, exist_ok=True)
            with (output / ".studio-write-check").open("a"):
                pass
            (output / ".studio-write-check").unlink()
        except OSError as error:
            self.host.message(str(error))
            return
        self._active = True
        self._stop_after.clear()
        self.host._busy = True
        self.host.message("Đang xuất hàng loạt…")

        def work(emit):
            done = 0
            began = time.monotonic()
            results = []
            for row in pending:
                check_cancelled()
                if self._stop_after.is_set():
                    break
                token = row["id"]
                config = row["config"]
                started = time.monotonic()
                emit(
                    dict(
                        row=token,
                        values=dict(
                            status="Đang xuất", percent=0, detail="Đang chuẩn bị", errorLog=""
                        ),
                        save=True,
                    )
                )
                try:
                    if not Path(row["path"]).is_file():
                        raise FileNotFoundError("Không tìm thấy video nguồn.")
                    signature = fingerprint(row["path"], config)
                    config = prepare_captions(self.root, self.home, row["path"], config,
                        lambda text: emit(dict(row=token, values=dict(detail=text), notice=text)))
                    destination = output / (
                        safe_name(Path(row["name"]).stem)
                        + "_"
                        + safe_name(row["presetName"])
                        + "_"
                        + uuid.uuid4().hex[:8]
                        + ".mp4"
                    )

                    def progress(p):
                        elapsed = time.monotonic() - started
                        percent = p["percent"]
                        eta = elapsed * (100 - percent) / percent if percent else 0
                        emit(
                            dict(
                                row=token,
                                values=dict(
                                    percent=round(percent),
                                    detail=f"{elapsed:.0f}s · còn ~{eta:.0f}s",
                                ),
                            )
                        )

                    if config["part_count"] != 1:
                        result = render_parts(
                            self.root, self.home, token, row["path"], config, output,
                            self.request, progress,
                            lambda parts: emit(dict(row=token, values=dict(parts=parts, result=parts[0]), save=True)),
                        )
                        outputs = result["parts"]
                    else:
                        result = run_worker(self.root, self.home,
                                            self.request(row["path"], destination, config), progress)
                        outputs = [str(destination)]
                    stamp = Path(row["path"]).stat()
                    done += 1
                    values = dict(
                        status="Hoàn tất",
                        percent=100,
                        result=outputs[0], parts=outputs,
                        signature=signature,
                        sourceStamp=[stamp.st_size, stamp.st_mtime_ns],
                        detail=f"{len(outputs)} phần · {result['wall_seconds']:.1f}s" if len(outputs) > 1 else
                               f"{result['wall_seconds']:.1f}s · {destination.stat().st_size / 1024**2:.1f} MiB",
                    )
                except TaskCancelled:
                    raise
                except Exception as error:
                    check_cancelled()
                    values = dict(
                        status="Lỗi", percent=0,
                        detail=(str(error).splitlines() or [type(error).__name__])[0][:240],
                        errorLog=getattr(error, "log_path", ""),
                    )
                emit(dict(row=token, values=values, save=True))
                results.append(
                    dict(
                        source=row["path"],
                        preset=row["presetName"],
                        config=config,
                        **values,
                    )
                )
            report = reports_directory(self.home) / (
                "bao-cao-"
                + time.strftime("%Y%m%d-%H%M%S")
                + "-"
                + uuid.uuid4().hex[:6]
                + ".json"
            )
            atomic_json(report, dict(version=VERSION, results=results))
            with report.with_suffix(".csv").open(
                "w", encoding="utf-8-sig", newline=""
            ) as stream:
                writer = csv.DictWriter(
                    stream,
                    fieldnames=["source", "preset", "status", "result", "detail"],
                    extrasaction="ignore",
                )
                writer.writeheader()
                writer.writerows(results)
            return f"Đã xuất {done}/{len(pending)} video trong {time.monotonic() - began:.0f} giây."

        self.pool.submit(
            work,
            result=self.host.message,
            error=self.host.message,
            event=self.task_event,
            finished=self.finish,
        )

    @Slot()
    def openLogs(self):
        path = self.home / "cache/workers"
        path.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    @Slot()
    def openErrorLog(self):
        if self._index >= 0:
            path = self._rows[self._index].get("errorLog", "")
            if path and Path(path).is_file():
                QDesktopServices.openUrl(QUrl.fromLocalFile(path))
                return
        self.openLogs()
