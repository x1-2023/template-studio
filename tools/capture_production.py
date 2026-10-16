"""Tạo ảnh GUI mới với preview thật để kiểm tra bố cục và lỗi QML."""

import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
HOME = ROOT / ".runtime/qa-production-capture"
os.environ["TEMPLATE_STUDIO_HOME"] = str(HOME)
os.environ["QT_QUICK_CONTROLS_STYLE"] = "Basic"
from PySide6.QtCore import QUrl  # noqa: E402
from PySide6.QtQml import QQmlApplicationEngine  # noqa: E402
from PySide6.QtQuick import QQuickWindow  # noqa: E402
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
    assert window.grabWindow().save(str(ROOT / ".runtime/production-preview.png"))
    assert not errors, errors
    print("GUI và preview thật: OK", flush=True)
    window.close()


if __name__ == "__main__":
    main()
