"""Kiểm tra nhập video qua sự kiện GUI, không gọi tắt add_paths."""

import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import PySide6

DLL_DIRECTORY = (
    os.add_dll_directory(str(Path(PySide6.__file__).parent))
    if os.name == "nt"
    else None
)
os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")

from PySide6.QtCore import QEvent, QMimeData, QObject, QPointF, Qt, QUrl  # noqa: E402
from PySide6.QtGui import QDragEnterEvent, QDragMoveEvent, QDropEvent  # noqa: E402
from PySide6.QtQml import QQmlApplicationEngine  # noqa: E402
from PySide6.QtQuick import QQuickItem, QQuickWindow  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402
from shiboken6 import getCppPointer, wrapInstance  # noqa: E402

from template_studio.app import Controller  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
METADATA = dict(
    streams=[dict(codec_type="video", width=1920, height=1080)],
    format=dict(duration="3"),
)


class ImportUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setQuitOnLastWindowClosed(False)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        # Windows CI có thể trả TEMP dạng tên ngắn RUNNER~1.
        self.home = Path(self.temp.name).resolve()
        self.source = self.home / "video thử #1.mp4"
        self.source.write_bytes(b"video")
        with patch.object(Controller, "prepareMedia"):
            self.controller = Controller(ROOT, self.home)
        self.p = self.controller.production
        self.metadata = patch("template_studio.production.probe", return_value=METADATA)
        self.metadata.start()
        self.addCleanup(self.metadata.stop)
        self.engine = QQmlApplicationEngine()
        self.errors = []
        self.engine.warnings.connect(
            lambda messages: self.errors.extend(m.toString() for m in messages)
        )
        self.engine.rootContext().setContextProperty("studio", self.controller)
        self.engine.load(
            QUrl.fromLocalFile(str(ROOT / "template_studio/Production.qml"))
        )
        self.assertTrue(self.engine.rootObjects(), self.errors)
        self.window = wrapInstance(
            getCppPointer(self.engine.rootObjects()[0])[0], QQuickWindow
        )
        QTest.qWait(100)

    def tearDown(self):
        self.wait()
        self.window.close()
        self.engine.deleteLater()
        self.app.sendPostedEvents(None, QEvent.DeferredDelete)
        self.assertEqual(self.errors, [])

    def wait(self):
        deadline = time.monotonic() + 10
        while self.controller.pool.active and time.monotonic() < deadline:
            QTest.qWait(10)
        self.assertFalse(self.controller.pool.active)
        self.app.processEvents()

    def click(self, name):
        item = self.window.findChild(QQuickItem, name)
        self.assertIsNotNone(item)
        pos = item.mapToScene(QPointF(item.width() / 2, item.height() / 2)).toPoint()
        QTest.mouseClick(self.window, Qt.LeftButton, Qt.NoModifier, pos)
        self.wait()

    def drop(self, paths, over_row=False):
        item = self.window.findChild(
            QQuickItem, "videoListArea" if over_row else "videoPanel"
        )
        pos = item.mapToScene(
            QPointF(item.width() / 2, 40 if over_row else item.height() / 2)
        )
        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(str(path)) for path in paths])
        enter = QDragEnterEvent(
            pos.toPoint(), Qt.CopyAction, mime, Qt.LeftButton, Qt.NoModifier
        )
        self.app.sendEvent(self.window, enter)
        move = QDragMoveEvent(
            pos.toPoint(), Qt.CopyAction, mime, Qt.LeftButton, Qt.NoModifier
        )
        self.app.sendEvent(self.window, move)
        drop = QDropEvent(pos, Qt.CopyAction, mime, Qt.LeftButton, Qt.NoModifier)
        self.app.sendEvent(self.window, drop)
        self.wait()
        return drop.isAccepted()

    def test_empty_button_opens_picker_and_adds_video(self):
        with patch(
            "template_studio.production.QFileDialog.getOpenFileNames",
            return_value=([str(self.source)], "Video"),
        ) as picker:
            self.click("emptyImportButton")
        picker.assert_called_once()
        self.assertEqual([row["path"] for row in self.p.rows], [str(self.source)])

    def edit_speed(self, value):
        self.click("editConfigButton")
        self.click("playback_rateField")
        QTest.keyClick(self.window, Qt.Key_A, Qt.ControlModifier)
        for char in value:
            QTest.keyClick(self.window, Qt.Key(ord(char)))
        QTest.keyClick(self.window, Qt.Key_Tab)
        self.wait()

    def test_error_log_button_opens_selected_worker_log(self):
        self.drop([self.source])
        log = self.home / "cache/workers/test/worker.log"
        log.parent.mkdir(parents=True)
        log.write_text("loi-goc")
        self.p._rows[0].update(status="Lỗi", detail="Lỗi gốc", errorLog=str(log))
        self.p.changed.emit()
        QTest.qWait(60)
        button = self.window.findChild(QQuickItem, "errorLogButton")
        self.assertTrue(button.isVisible())
        with patch("template_studio.production.QDesktopServices.openUrl") as opened:
            self.click("errorLogButton")
        self.assertEqual(opened.call_args.args[0].toLocalFile(), str(log).replace("\\", "/"))

    def test_config_cancel_discards_draft_and_reopens_saved_values(self):
        original = self.p.config
        self.edit_speed("1.25")
        self.assertEqual(self.p.config, original)
        self.click("cancelConfigButton")
        self.click("editConfigButton")
        field = self.window.findChild(QQuickItem, "playback_rateField")
        self.assertEqual(float(field.property("text")), original["playback_rate"])
        self.click("cancelConfigButton")
        self.assertEqual(self.p.config, original)

    def test_config_save_updates_pending_but_preserves_completed(self):
        self.drop([self.source])
        other = self.home / "pending.mp4"
        other.write_bytes(b"video")
        self.drop([other])
        self.p._rows[0]["status"] = "Hoàn tất"
        original = self.p._rows[0]["config"]["playback_rate"]
        self.edit_speed("1.25")
        self.click("saveConfigButton")
        self.assertEqual(self.p.config["playback_rate"], 1.25)
        self.assertEqual(self.p._rows[0]["config"]["playback_rate"], original)
        self.assertEqual(self.p._rows[1]["config"]["playback_rate"], 1.25)
        self.assertFalse(self.window.findChild(QObject, "configDialog").property("visible"))

    def test_config_escape_discards_draft(self):
        original = self.p.config
        self.edit_speed("1.30")
        QTest.keyClick(self.window, Qt.Key_Escape)
        self.wait()
        self.assertFalse(self.window.findChild(QObject, "configDialog").property("visible"))
        self.assertEqual(self.p.config, original)

    def test_apply_config_rejects_invalid_data_and_running_tasks(self):
        original = self.p.config
        self.assertFalse(self.p.applyConfig({"playback_rate": 99}))
        self.assertEqual(self.p.config, original)
        self.controller._busy = True
        try:
            self.assertFalse(self.p.applyConfig({"playback_rate": 1.25}))
        finally:
            self.controller._busy = False
        self.assertEqual(self.p.config, original)

    def test_native_drop_imports_unicode_file(self):
        self.assertTrue(self.drop([self.source]))
        self.assertEqual([row["path"] for row in self.p.rows], [str(self.source)])
        self.assertEqual(self.source.read_bytes(), b"video")

    def test_empty_area_also_opens_picker(self):
        with patch(
            "template_studio.production.QFileDialog.getOpenFileNames",
            return_value=([str(self.source)], "Video"),
        ) as picker:
            self.click("videoListArea")
        picker.assert_called_once()
        self.assertEqual(len(self.p.rows), 1)

    def test_cancel_picker_then_use_top_button(self):
        with patch(
            "template_studio.production.QFileDialog.getOpenFileNames",
            return_value=([], "Video"),
        ) as picker:
            self.click("emptyImportButton")
        picker.assert_called_once()
        self.assertEqual(self.p.rows, [])
        with patch(
            "template_studio.production.QFileDialog.getOpenFileNames",
            return_value=([str(self.source)], "Video"),
        ) as picker:
            self.click("topImportButton")
        picker.assert_called_once()
        self.assertEqual(len(self.p.rows), 1)

    def test_native_folder_drop_over_existing_row_and_duplicate(self):
        self.assertTrue(self.drop([self.source]))
        folder = self.home / "thư mục #2"
        folder.mkdir()
        second = folder / "video thêm.mp4"
        second.write_bytes(b"second")
        (folder / "ghi chú.txt").write_text("không phải video", encoding="utf-8")
        self.assertTrue(self.drop([folder], over_row=True))
        self.assertEqual(
            {r["path"] for r in self.p.rows}, {str(self.source), str(second)}
        )
        self.assertTrue(self.drop([folder], over_row=True))
        self.assertEqual(len(self.p.rows), 2)
        self.assertEqual(second.read_bytes(), b"second")

    def test_qurl_and_string_urls_are_supported(self):
        second = self.home / "video khác.mp4"
        second.write_bytes(b"second")
        self.p.dropFiles(
            [
                QUrl.fromLocalFile(str(self.source)),
                QUrl.fromLocalFile(str(second)).toString(),
            ]
        )
        self.wait()
        self.assertEqual(
            {r["path"] for r in self.p.rows}, {str(self.source), str(second)}
        )

    def test_invalid_urls_do_not_import_working_directory(self):
        with patch.object(self.p, "add_paths") as add:
            self.p.dropFiles(
                [QUrl(), "", QUrl("https://example.com/video.mp4"), "text"]
            )
        add.assert_not_called()

    def test_busy_task_rejects_native_drop(self):
        self.controller._busy = True
        self.controller.changed.emit()
        try:
            self.assertFalse(self.drop([self.source]))
            self.assertEqual(self.p.rows, [])
        finally:
            self.controller._busy = False
            self.controller.changed.emit()
