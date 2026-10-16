"""Tạo ảnh GUI mới với preview thật để kiểm tra bố cục và lỗi QML."""

import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
HOME = ROOT / ".runtime/qa-production-capture"
os.environ["TEMPLATE_STUDIO_HOME"] = str(HOME)
os.environ["QT_QUICK_CONTROLS_STYLE"] = "Basic"
import PySide6  # noqa: E402

# Giữ đường dẫn DLL cho các plugin QML nạp sau khi khởi tạo cửa sổ.
DLL_DIRECTORY = (
    os.add_dll_directory(str(Path(PySide6.__file__).parent))
    if os.name == "nt"
    else None
)
from PySide6.QtCore import QMetaObject, QObject, QPoint, QPointF, Qt, QUrl  # noqa: E402
from PySide6.QtQml import QQmlApplicationEngine  # noqa: E402
from PySide6.QtQuick import QQuickItem, QQuickWindow  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402
from shiboken6 import getCppPointer, wrapInstance  # noqa: E402

from template_studio.app import Controller  # noqa: E402


def main():
    app = QApplication([])
    controller = Controller(ROOT, HOME)

    def wait():
        end = time.monotonic() + 60
        while controller.pool.active and time.monotonic() < end:
            app.processEvents()
            time.sleep(0.03)
        assert not controller.pool.active

    wait()
    p = controller.production
    p.checkRuntime()
    wait()
    p._rows = []
    p.choosePreset("reference")
    p.add_paths(
        [
            str(
                ROOT
                / "CapCut_FFmpeg_Codex_Handoff/02_REFERENCE_MEDIA/source_original_compre_juguetes.mp4"
            )
        ]
    )
    wait()
    p.preview(0)
    wait()
    assert p.previewUrl, controller.notice
    engine = QQmlApplicationEngine()
    errors = []
    engine.warnings.connect(lambda rows: errors.extend(r.toString() for r in rows))
    engine.rootContext().setContextProperty("studio", controller)
    engine.load(QUrl.fromLocalFile(str(ROOT / "template_studio/Production.qml")))
    assert engine.rootObjects(), errors
    end = time.monotonic() + 3
    while time.monotonic() < end:
        app.processEvents()
        time.sleep(0.02)
    window = wrapInstance(getCppPointer(engine.rootObjects()[0])[0], QQuickWindow)

    def settle():
        QTest.qWait(160)
        app.processEvents()

    def capture(name):
        # Yêu cầu vẽ lại toàn khung trước khi đọc ảnh từ swapchain Direct3D.
        window.contentItem().setOpacity(0.999)
        settle()
        window.contentItem().setOpacity(1)
        settle()
        assert window.grabWindow().save(str(ROOT / f".runtime/{name}.png"))

    def click(item, x=None, y=None):
        position = item.mapToScene(
            QPointF(
                item.width() / 2 if x is None else x,
                item.height() / 2 if y is None else y,
            )
        ).toPoint()
        QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, position)
        settle()

    def walk(item):
        yield item
        for child in item.childItems():
            yield from walk(child)

    def contrast(foreground, background):
        def luminance(color):
            channels = [color.redF(), color.greenF(), color.blueF()]
            linear = [
                x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4
                for x in channels
            ]
            return sum(x * y for x, y in zip(linear, (0.2126, 0.7152, 0.0722)))

        a, b = sorted((luminance(foreground), luminance(background)))
        return (b + 0.05) / (a + 0.05)

    def verify_popup(combo):
        popup = window.findChild(QObject, combo.objectName() + "Popup")
        assert popup is not None
        assert popup.property("visible"), combo.objectName()
        options = [
            item
            for item in walk(popup.property("contentItem"))
            if item.objectName() == "optionText"
        ]
        assert options, combo.objectName()
        other = next(
            label.parentItem()
            for label in options
            if not label.parentItem().property("selected")
        )
        QTest.mouseMove(
            window,
            other.mapToScene(QPointF(other.width() / 2, other.height() / 2)).toPoint(),
        )
        settle()
        ratios = []
        for label in options:
            background = label.parentItem().property("background").property("color")
            if background.alpha() == 0:
                background = popup.property("background").property("color")
            ratio = contrast(label.property("color"), background)
            assert ratio >= 4.5, (label.property("text"), ratio)
            ratios.append(ratio)
        return ratios

    # Kiểm tra cả model preset dạng object và danh sách chuỗi của combobox.
    preset = window.findChild(QQuickItem, "presetSelect")
    click(preset)
    ratios = verify_popup(preset)
    QTest.mouseMove(window, QPoint(15, 15))
    settle()
    capture("production-combobox")
    QTest.keyClick(window, Qt.Key_End)
    QTest.keyClick(window, Qt.Key_Up)
    QTest.keyClick(window, Qt.Key_Return)
    settle()
    assert p.presetId == "layout", p.presetId
    p.choosePreset("reference")
    settle()
    quality = window.findChild(QQuickItem, "qualitySelect")
    click(quality)
    ratios.extend(verify_popup(quality))
    QTest.keyClick(window, Qt.Key_Home)
    QTest.keyClick(window, Qt.Key_Return)
    settle()
    assert p.config["quality"] == "small", p.config
    p.configure("quality", "standard")
    click(quality)
    popup = window.findChild(QObject, "qualitySelectPopup")
    high = next(
        item
        for item in walk(popup.property("contentItem"))
        if item.objectName() == "optionText"
        and item.property("text") == "Chất lượng cao"
    )
    click(high.parentItem())
    assert p.config["quality"] == "high", p.config
    p.configure("quality", "standard")
    click(quality)
    QTest.keyClick(window, Qt.Key_Escape)
    settle()
    assert not window.findChild(QObject, "qualitySelectPopup").property("visible")
    intro = window.findChild(QQuickItem, "introCheck")
    click(intro)
    assert not p.config["intro_enabled"]
    click(intro)
    assert p.config["intro_enabled"]
    number = window.findChild(QQuickItem, "previewOffset")
    click(number, number.width() - 14)
    assert number.property("value") == 1
    click(number, 14)
    assert number.property("value") == 0
    click(number)
    QTest.keyClick(window, Qt.Key_A, Qt.ControlModifier)
    QTest.keyClick(window, Qt.Key_5)
    QTest.keyClick(window, Qt.Key_Return)
    settle()
    assert number.property("value") == 5, number.property("value")
    number.setProperty("value", 0)
    bitrate = window.findChild(QQuickItem, "bitrateField")
    click(bitrate)
    QTest.keyClick(window, Qt.Key_A, Qt.ControlModifier)
    for key in (Qt.Key_8, Qt.Key_Period, Qt.Key_5, Qt.Key_Return):
        QTest.keyClick(window, key)
    settle()
    assert p.config["video_bitrate"] == 8.5, p.config
    p.configure("video_bitrate", 9.65)
    QTest.mouseMove(window, QPoint(15, 15))
    settle()
    panels = [
        window.findChild(QQuickItem, name)
        for name in ("videoPanel", "configurationPanel", "previewPanel")
    ]
    grid = window.findChild(QQuickItem, "configurationGrid")
    scroll = window.findChild(QQuickItem, "configurationScroll")
    custom = window.findChild(QQuickItem, "customPresetCard")
    assert all(item is not None for item in [*panels, grid, scroll, custom])
    bar = window.findChild(QQuickItem, "configurationBar")
    flick = scroll.property("contentItem")
    layouts = []
    for width, height, name, columns in (
        (1440, 900, "production-preview", 2),
        (1100, 720, "production-narrow", 1),
        (1366, 768, "production-laptop", 2),
        (1920, 1080, "production-wide", 2),
    ):
        window.resize(width, height)
        end = time.monotonic() + 0.4
        while time.monotonic() < end:
            app.processEvents()
            time.sleep(0.02)
        positions = [item.mapToScene(QPointF(0, 0)).x() for item in panels]
        sizes = [item.width() for item in panels]
        assert 260 <= sizes[0] <= 286, sizes
        assert sizes[1] > sizes[0], sizes
        assert all(positions[i] + sizes[i] < positions[i + 1] for i in range(2))
        assert positions[2] + sizes[2] <= window.width() - 19
        assert grid.property("columns") == columns, (width, sizes)
        assert bar.height() > 100 and bar.property("contentItem").height() > 10
        assert (
            grid.mapToScene(QPointF(grid.width(), 0)).x()
            < bar.mapToScene(QPointF(0, 0)).x()
        )
        capture(name)
        flick.setProperty(
            "contentY", max(0, flick.property("contentHeight") - flick.height())
        )
        app.processEvents()
        custom_bottom = custom.mapToScene(QPointF(0, custom.height())).y()
        scroll_bottom = scroll.mapToScene(QPointF(0, scroll.height())).y()
        assert custom_bottom <= scroll_bottom + 2, (width, custom_bottom, scroll_bottom)
        assert custom_bottom > scroll.mapToScene(QPointF(0, 0)).y()
        flick.setProperty("contentY", 0)
        layouts.append(dict(width=width, height=height, panels=sizes, columns=columns))
    (ROOT / ".runtime/production-layout.json").write_text(json.dumps(layouts, indent=2))
    window.resize(1440, 900)
    drawer = window.findChild(QObject, "systemDrawer")
    QMetaObject.invokeMethod(drawer, "open")
    settle()
    capture("production-settings")
    QMetaObject.invokeMethod(drawer, "close")
    settle()
    (ROOT / ".runtime/production-controls.json").write_text(
        json.dumps(
            dict(
                ok=True,
                contrast=min(ratios),
                keyboard=True,
                checkbox=True,
                spinbox=True,
                input=True,
            ),
            indent=2,
        )
    )
    assert not errors, errors
    print("GUI và preview thật: OK", flush=True)
    window.close()


if __name__ == "__main__":
    main()
