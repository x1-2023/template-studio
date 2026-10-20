"""Mở app Template Studio riêng bằng py template_gui.py, không cần venv."""
import importlib.util
import os
import subprocess
import sys
from pathlib import Path


def main():
    for stream in (sys.stdout, sys.stderr):
        if stream and hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8', errors='replace')
    root = Path(__file__).resolve().parent
    if not (root / 'template_studio').is_dir():
        root /= 'studio_pro'
    if sys.version_info < (3, 11):
        raise RuntimeError('Cần Python 3.11 trở lên, bản 64 bit.')
    explicit_home = os.environ.get('TEMPLATE_STUDIO_HOME')
    if explicit_home:
        home = Path(explicit_home).resolve()
    elif root.drive.lower() == 'c:':
        home = (Path(os.environ.get('LOCALAPPDATA', str(root / 'data'))) / 'Dublora' / 'TemplateStudio').resolve()
    else:
        home = root / 'data/template-studio'
    cache = home / 'cache'
    cache.mkdir(parents=True, exist_ok=True)
    packages_root = home / 'runtime' if root.drive.lower() == 'c:' else root / '.runtime'
    packages = packages_root / f'python-packages-{sys.version_info.major}.{sys.version_info.minor}'
    sys.dont_write_bytecode = True
    os.environ.update(TEMP=str(cache), TMP=str(cache), PYTHONDONTWRITEBYTECODE='1',
                      PIP_CACHE_DIR=str(cache / 'pip'), QT_QUICK_CONTROLS_STYLE='Basic')
    import tempfile
    tempfile.tempdir = str(cache)
    sys.path[:0] = [str(packages), str(root)]
    pyside_spec = importlib.util.find_spec('PySide6')
    pyside = Path(pyside_spec.origin).parent if pyside_spec else packages / 'PySide6'
    if pyside.is_dir():
        os.environ['PATH'] = os.pathsep.join([str(pyside), os.environ.get('PATH', '')])
    dll_directory = os.add_dll_directory(str(pyside)) if os.name == 'nt' and pyside.is_dir() else None
    if (pyside / 'bin').is_dir():
        os.environ['PATH'] = os.pathsep.join([str(pyside / 'bin'), os.environ.get('PATH', '')])
    if (pyside / 'plugins').is_dir():
        os.environ['QT_PLUGIN_PATH'] = str(pyside / 'plugins')
    if (pyside / 'qml').is_dir():
        os.environ['QML2_IMPORT_PATH'] = str(pyside / 'qml')
    missing = [req for module, req in [('PySide6', 'PySide6==6.11.2'), ('PIL', 'Pillow==12.2.0'),
                                      ('moderngl', 'moderngl==5.13.0'), ('glcontext', 'glcontext==3.1.0'),
                                      ('certifi', 'certifi==2026.10.19')]
               if importlib.util.find_spec(module) is None]
    if importlib.util.find_spec('video_fx') is None:
        missing.append('video-fx @ https://github.com/tomastimelock/video-fx/archive/751315965bc5e740b62136153ec4a9bf4e21ea20.zip')
    if missing:
        print('Đang chuẩn bị thư viện cạnh app; không tạo venv…', flush=True)
        subprocess.run([sys.executable, '-m', 'pip', 'install', '--target', str(packages),
                        '--upgrade', '--only-binary=:all:', '--disable-pip-version-check', *missing], check=True)
        return subprocess.call([sys.executable, '-B', str(Path(__file__).resolve()), *sys.argv[1:]])
    from template_studio.app import main as run
    try:
        return run(root, home)
    finally:
        if dll_directory:
            dll_directory.close()


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f'Không mở được Template Studio: {error}', file=sys.stderr)
        raise SystemExit(1)
