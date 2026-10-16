"""Điểm vào bản Beta Render portable đã đóng gói."""
import sys
import os
from pathlib import Path
from template_studio.paths import data_home


if __name__ == '__main__':
    if '--render-worker' in sys.argv:
        sys.argv.remove('--render-worker')
        from template_studio.worker import main as worker_main
        raise SystemExit(worker_main())
    root = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))
    app_root = Path(sys.executable).resolve().parent
    home = data_home(app_root)
    os.environ.setdefault('QT_QUICK_CONTROLS_STYLE', 'Basic')
    dll_handles = []
    if os.name == 'nt':
        for directory in (root, root / 'PySide6'):
            if directory.is_dir():
                dll_handles.append(os.add_dll_directory(str(directory)))
    try:
        from template_studio.app import main
        raise SystemExit(main(root, home))
    except Exception as error:
        import traceback
        (home / 'startup-error.log').write_text(traceback.format_exc(), encoding='utf-8')
        if '--check' not in sys.argv:
            from PySide6.QtWidgets import QApplication, QMessageBox
            application = QApplication.instance() or QApplication([])
            QMessageBox.critical(None, 'Không mở được Beta Render', str(error) + '\nChi tiết: ' + str(home / 'startup-error.log'))
        raise SystemExit(1)
