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
from PySide6.QtGui import QColor, QDragEnterEvent, QDragMoveEvent, QDropEvent  # noqa: E402
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
        # Metadata đã giả lập; kiểm thử thao tác không tải runtime cho từng TEMP.
        self.media_setup = patch("template_studio.production.ensure_media")
        self.media_setup.start()
        self.addCleanup(self.media_setup.stop)
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

    def find_item(self, name):
        item = self.window.findChild(QQuickItem, name)
        if item is None:
            # Delegate của Repeater có cha hiển thị khác với cha QObject.
            pending = [self.window.contentItem()]
            while pending:
                child = pending.pop()
                if child.objectName() == name:
                    return child
                pending.extend(child.childItems())
        self.assertIsNotNone(item, name)
        return item

    def click(self, name):
        item = self.find_item(name)
        pos = item.mapToScene(QPointF(item.width() / 2, item.height() / 2)).toPoint()
        QTest.mouseClick(self.window, Qt.LeftButton, Qt.NoModifier, pos)
        self.wait()
        if name == "editConfigButton":
            # Trên Windows, visible có thể true trong khi Popup còn đang chạy enter.
            # Chờ onOpened khởi tạo draft trước khi kiểm thử tương tác với nội dung.
            dialog = self.window.findChild(QObject, "configDialog")
            deadline = time.monotonic()+2
            while not dialog.property("opened") and time.monotonic() < deadline:
                QTest.qWait(10)
            self.assertTrue(dialog.property("opened"))

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

    def test_karaoke_preset_saves_new_fields_and_preserves_default_presets(self):
        self.p.choosePreset("karaoke-1012")
        self.assertEqual(len(self.p.mainPresets), 4)
        self.assertEqual(self.p.config["subtitle_mode"], "auto")
        self.click("editConfigButton")
        dialog = self.window.findChild(QObject, "configDialog")
        draft = {**self.p.config, "part_count":1, "subtitle_title":"TIÊU ĐỀ MẪU", "rotation_deg":-8}
        dialog.setProperty("draft", draft)
        self.click("saveConfigButton")
        self.assertEqual(self.p.config, draft)
        self.p.choosePreset("pentagon-9x16")
        self.assertEqual(self.p.config["subtitle_mode"], "off")
        self.assertEqual(self.p.config["part_count"], 1)
        self.assertEqual(self.p.config["rotation_deg"], 0)

    def test_subtitle_picker_updates_draft_and_cancel_keeps_saved_config(self):
        self.p.choosePreset("karaoke-1012")
        self.click("editConfigButton")
        dialog = self.window.findChild(QObject, "configDialog")
        dialog.setProperty("draft", {**self.p.config,"subtitle_mode":"file"})
        scroll = self.window.findChild(QQuickItem, "configurationScroll")
        section = self.window.findChild(QQuickItem, "captionsSection")
        QTest.qWait(60)
        scroll.property("contentItem").setProperty("contentY", section.y()-20)
        QTest.qWait(60)
        path = self.home/"phụ đề.words.json"
        with patch("template_studio.production.QFileDialog.getOpenFileName",return_value=(str(path),"")) as picker:
            self.click("subtitlePicker")
        picker.assert_called_once()
        self.assertEqual(dialog.property("draft").toVariant()["subtitle_file"], str(path))
        self.click("cancelConfigButton")
        self.assertEqual(self.p.config["subtitle_file"], "")

    def test_font_picker_copies_font_and_cancel_keeps_previous_config(self):
        font = Path('C:/Windows/Fonts/arial.ttf')
        if not font.is_file():
            self.skipTest('Kiểm thử GUI nhập font dùng Arial của Windows.')
        self.p.choosePreset('karaoke-1012')
        self.click('editConfigButton')
        dialog = self.window.findChild(QObject,'configDialog')
        flick = self.window.findChild(QQuickItem,'configurationScroll').property('contentItem')
        QTest.qWait(60)
        item = self.window.findChild(QQuickItem,'subtitleFontPicker')
        y = item.mapToScene(QPointF(0,0)).y()
        flick.setProperty('contentY',flick.property('contentY')+y-260)
        QTest.qWait(70)
        with patch('template_studio.production.QFileDialog.getOpenFileName',return_value=(str(font),'')):
            self.click('subtitleFontPicker')
        draft = dialog.property('draft').toVariant()
        self.assertEqual(draft['subtitle_font_name'],'Arial')
        imported = Path(draft['subtitle_font_file'])
        self.assertTrue(imported.is_relative_to(self.home/'runtime/fonts'))
        self.assertEqual(imported.read_bytes(),font.read_bytes())
        with patch('template_studio.production.QFileDialog.getOpenFileName',return_value=('','')):
            self.click('subtitleFontPicker')
        self.assertEqual(dialog.property('draft').toVariant()['subtitle_font_file'],str(imported))
        self.click('cancelConfigButton')
        self.assertEqual(self.p.config['subtitle_font_file'],'')

    def scroll_to_config_item(self, name):
        item=self.find_item(name)
        flick=self.window.findChild(QQuickItem,'configurationScroll').property('contentItem')
        # FoldSection cập nhật chiều cao ở lượt layout sau onOpened.
        # Đợi tọa độ ổn định, không dùng chiều cao content còn cũ trên CI.
        deadline=time.monotonic()+2
        while time.monotonic()<deadline:
            QTest.qWait(20)
            y=item.mapToScene(QPointF(item.width()/2,item.height()/2)).y()
            center=flick.mapToScene(QPointF(flick.width()/2,flick.height()/2)).y()
            maximum=max(0,flick.property('contentHeight')-flick.height())
            flick.setProperty('contentY',min(maximum,max(0,flick.property('contentY')+y-center)))
            QTest.qWait(40)
            y=item.mapToScene(QPointF(item.width()/2,item.height()/2)).y()
            top=flick.mapToScene(QPointF(0,0)).y()
            if top+item.height()/2<y<top+flick.height()-item.height()/2:
                return item
        self.fail((name,y,top,flick.height(),flick.property('contentHeight')))

    def test_basic_palette_saves_independent_title_and_part_colors_and_cancel_discards(self):
        self.p.choosePreset('karaoke-1012')
        self.click('editConfigButton')
        dialog=self.window.findChild(QObject,'configDialog')
        selected=dict(title_color='FFFF00',title_background='000000',part_color='FF0000',part_background='00FFFF')
        with patch('template_studio.production.QColorDialog.getColor') as picker:
            for setting,value in selected.items():
                name=setting+'Basic'+value
                self.scroll_to_config_item(name)
                self.click(name)
                self.assertEqual(dialog.property('draft').toVariant()[setting],value)
            picker.assert_not_called()
        self.click('saveConfigButton')
        for key,value in selected.items():
            self.assertEqual(self.p.config[key],value)
        self.p.savePreset('Tiêu đề vàng, PART đỏ')
        saved=self.p.mainPresets[-1]['config']
        for key,value in selected.items():
            self.assertEqual(saved[key],value)
        self.click('editConfigButton')
        self.scroll_to_config_item('part_colorBasic00FF00')
        self.click('part_colorBasic00FF00')
        self.assertEqual(dialog.property('draft').toVariant()['part_color'],'00FF00')
        self.click('cancelConfigButton')
        self.assertEqual(self.p.config['part_color'],'FF0000')

    def test_color_picker_and_custom_part_count_save_with_preset(self):
        self.p.choosePreset("karaoke-1012")
        self.click("editConfigButton")
        dialog=self.window.findChild(QObject,"configDialog")
        scroll_to=self.scroll_to_config_item

        scroll_to("subtitle_redPicker")
        with patch("template_studio.production.QColorDialog.getColor",return_value=QColor()) as picker:
            self.click("subtitle_redPicker")
        picker.assert_called_once()
        self.assertEqual(dialog.property("draft").toVariant()["subtitle_red"],"FF0000")
        # Dialog giả lập trả ngay; tránh hai click liên tiếp thành double-click trên Windows.
        QTest.qWait(self.app.doubleClickInterval()+30)
        scroll_to("subtitle_redPicker")
        with patch("template_studio.production.QColorDialog.getColor",return_value=QColor("#33CCAA")) as picker:
            self.click("subtitle_redPicker")
        picker.assert_called_once()
        self.assertEqual(dialog.property("draft").toVariant()["subtitle_red"],"33CCAA")
        scroll_to("subtitle_colorField")
        self.click("subtitle_colorField")
        QTest.keyClick(self.window,Qt.Key_A,Qt.ControlModifier)
        for char in "#66AAFF":
            QTest.keyClick(self.window,Qt.Key(ord(char)))
        QTest.keyClick(self.window,Qt.Key_Tab)
        select=scroll_to("partCountSelect")
        self.click("partCountSelect")
        QTest.keyClick(self.window,Qt.Key_End)
        QTest.keyClick(self.window,Qt.Key_Return)
        self.wait()
        self.assertEqual(select.property("currentIndex"),2)
        self.assertEqual(dialog.property("draft").toVariant()["part_count"],2)
        scroll_to("partCountField")
        self.click("partCountField")
        QTest.keyClick(self.window,Qt.Key_A,Qt.ControlModifier)
        QTest.keyClick(self.window,Qt.Key_5)
        QTest.keyClick(self.window,Qt.Key_Tab)
        self.click("saveConfigButton")
        self.assertFalse(dialog.property("visible"),self.controller.notice)
        self.assertEqual(self.p.config["part_count"],5)
        self.assertEqual(self.p.config["subtitle_red"],"33CCAA")
        self.assertEqual(self.p.config["subtitle_color"],"66AAFF")
        self.p.savePreset("Màu và số part")
        saved=self.p.mainPresets[-1]["config"]
        self.assertEqual(saved["part_count"],5)
        self.assertEqual(saved["subtitle_red"],"33CCAA")

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
