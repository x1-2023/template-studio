"""Tách tài nguyên chỉ đọc khỏi dữ liệu và video xuất có thể ghi."""
import os
from pathlib import Path


def data_home(app_root):
    explicit = os.environ.get('TEMPLATE_STUDIO_HOME')
    if explicit:
        home = Path(explicit).resolve()
        home.mkdir(parents=True, exist_ok=True)
        return home
    home = Path(app_root) / 'data' / 'template-studio'
    try:
        home.mkdir(parents=True, exist_ok=True)
        probe = home / '.write-check'
        with probe.open('a'):
            pass
        probe.unlink()
        return home
    except OSError:
        home = Path(os.environ.get('LOCALAPPDATA', Path.home())) / 'TemplateStudio'
        home.mkdir(parents=True, exist_ok=True)
        return home
