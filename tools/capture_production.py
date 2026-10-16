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
    click(window.findChild(QQuickItem, "editConfigButton"))
    dialog = window.findChild(QObject, "configDialog")
    assert dialog.property("visible")
    capture("beta-render-config")
    scroll = window.findChild(QQuickItem, "configurationScroll")
    flick = scroll.property("contentItem")
    output = window.findChild(QQuickItem, "outputSection")

    def show_output():
        flick.setProperty("contentY", output.y())
        settle()

    original = p.config
    show_output()
    quality = window.findChild(QQuickItem, "qualitySelect")
    click(quality)
    ratios.extend(verify_popup(quality))
    QTest.keyClick(window, Qt.Key_Home)
    QTest.keyClick(window, Qt.Key_Return)
    settle()
    assert p.config == original
    assert quality.property("currentIndex") == 0
    click(quality)
    popup = window.findChild(QObject, "qualitySelectPopup")
    high = next(
        item for item in walk(popup.property("contentItem"))
        if item.objectName() == "optionText"
        and item.property("text") == "Chất lượng cao"
    )
    click(high.parentItem())
    assert quality.property("currentIndex") == 2
    assert p.config == original
    click(quality)
    QTest.keyClick(window, Qt.Key_Escape)
    settle()
    assert not popup.property("visible")
    click(window.findChild(QQuickItem, "cancelConfigButton"))
    assert p.config == original
    click(window.findChild(QQuickItem, "editConfigButton"))
    show_output()
    bitrate = window.findChild(QQuickItem, "bitrateField")
    click(bitrate)
    QTest.keyClick(window, Qt.Key_A, Qt.ControlModifier)
    for key in (Qt.Key_8, Qt.Key_Period, Qt.Key_5, Qt.Key_Tab):
        QTest.keyClick(window, key)
    settle()
    assert p.config == original
    flick.setProperty("contentY", 0)
    settle()
    slider = window.findChild(QQuickItem, "scaleSlider")
    click(slider)
    speed = window.findChild(QQuickItem, "playback_rateField")
    click(speed)
    QTest.keyClick(window, Qt.Key_A, Qt.ControlModifier)
    for char in "1.25":
        QTest.keyClick(window, Qt.Key(ord(char)))
    QTest.keyClick(window, Qt.Key_Tab)
    settle()
    assert p.config == original
    capture("beta-render-config-edited")
    click(window.findChild(QQuickItem, "saveConfigButton"))
    assert not dialog.property("visible")
    assert p.config["video_bitrate"] == 8.5, p.config
    assert p.config["playback_rate"] == 1.25, p.config
    assert p.config["scale"] != original["scale"], p.config
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
    assert number.property("value") == 5
    number.setProperty("value", 0)
    p.choosePreset("reference")
    QTest.mouseMove(window, QPoint(15, 15))
    settle()
    panels = [window.findChild(QQuickItem, name) for name in
              ("videoPanel", "configurationPanel", "previewPanel")]
    bar = window.findChild(QQuickItem, "configurationBar")
    layouts = []
    for width, height, name in (
        (1440, 900, "beta-render-main"),
        (1100, 720, "beta-render-narrow"),
        (1366, 768, "beta-render-laptop"),
        (1920, 1080, "beta-render-wide"),
    ):
        window.resize(width, height)
        QTest.qWait(400)
        positions = [item.mapToScene(QPointF(0, 0)).x() for item in panels]
        sizes = [item.width() for item in panels]
        assert 260 <= sizes[0] <= 286, sizes
        assert sizes[1] > sizes[0], sizes
        assert all(positions[i] + sizes[i] < positions[i + 1] for i in range(2))
        assert positions[2] + sizes[2] <= window.width() - 11
        actions = window.findChild(QQuickItem, "presetActions")
        assert actions.mapToScene(QPointF(0, actions.height())).y() <= panels[1].mapToScene(QPointF(0, panels[1].height())).y() - 14
        capture(name)
        click(window.findChild(QQuickItem, "editConfigButton"))
        assert dialog.property("height") <= height - 49
        assert dialog.property("width") <= width - 59
        assert bar.height() > 100 and bar.property("contentItem").height() > 10
        flick.setProperty("contentY", max(0, flick.property("contentHeight") - flick.height()))
        settle()
        output_bottom = output.mapToScene(QPointF(0, output.height())).y()
        scroll_bottom = scroll.mapToScene(QPointF(0, scroll.height())).y()
        assert output_bottom <= scroll_bottom + 2, (width, output_bottom, scroll_bottom)
        if width == 1100:
            capture("beta-render-config-narrow")
        flick.setProperty("contentY", 0)
        click(window.findChild(QQuickItem, "cancelConfigButton"))
        layouts.append(dict(width=width, height=height, panels=sizes))
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
                save_cancel=True,
                slider=True,
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
