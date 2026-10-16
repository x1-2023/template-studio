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
from PySide6.QtCore import QPointF, QUrl  # noqa: E402
from PySide6.QtQml import QQmlApplicationEngine  # noqa: E402
from PySide6.QtQuick import QQuickItem, QQuickWindow  # noqa: E402
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
    panels = [
        window.findChild(QQuickItem, name)
        for name in ("videoPanel", "configurationPanel", "previewPanel")
    ]
    grid = window.findChild(QQuickItem, "configurationGrid")
    scroll = window.findChild(QQuickItem, "configurationScroll")
    custom = window.findChild(QQuickItem, "customPresetCard")
    assert all(item is not None for item in [*panels, grid, scroll, custom])
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
        assert window.grabWindow().save(str(ROOT / f".runtime/{name}.png"))
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
    assert not errors, errors
    print("GUI và preview thật: OK", flush=True)
    window.close()


if __name__ == "__main__":
    main()
