"""Build Beta Render standalone: không cần Python/venv trên máy đích."""
import os
import hashlib
import importlib.metadata
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def clean_build_directory(path):
    path = Path(path)
    if not path.resolve().is_relative_to(ROOT) or path == ROOT or path.is_symlink() or getattr(path, 'is_junction', lambda: False)():
        raise ValueError('Từ chối xóa thư mục ngoài workspace hoặc qua liên kết.')
    if path.exists():
        shutil.rmtree(path)


def collect_licenses(target):
    destination = target / '_internal' / 'licenses'
    destination.mkdir(parents=True, exist_ok=True)
    sources = []
    for distribution in importlib.metadata.distributions():
        name = distribution.metadata['Name']
        sources.append(dict(name=name, version=distribution.version,
                            source=f'https://pypi.org/project/{name}/{distribution.version}/#files',
                            upstream=distribution.metadata.get_all('Project-URL') or []))
        for file in distribution.files or []:
            lowered = str(file).lower()
            if '/licenses/' not in lowered and not file.name.lower().startswith(('license', 'copying', 'notice')):
                continue
            source = Path(distribution.locate_file(file))
            if source.is_file():
                parts = Path(str(file)).parts
                info_index = next((index for index, part in enumerate(parts) if part.endswith('.dist-info')), -1)
                relative = Path(*parts[info_index + 1:]) if info_index >= 0 else Path(file.name)
                output = destination / name / relative
                output.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, output)
    python_license = Path(sys.base_prefix) / 'LICENSE.txt'
    if python_license.is_file():
        shutil.copy2(python_license, destination / 'Python-LICENSE.txt')
    (destination / 'package-sources.json').write_text(json.dumps(sources, ensure_ascii=False, indent=2), encoding='utf-8')


def main():
    from template_studio.version import VERSION, ASSET_NAME
    from template_studio.assets_local import validate
    from template_studio.gpu.resources import bundled_cache
    validate(bundled_cache(ROOT))
    for stream in (sys.stdout, sys.stderr):
        if stream is not None and hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8', errors='replace')
    dist = ROOT / '.runtime' / 'dist-template'
    work = ROOT / '.runtime' / 'build-template'
    cache = ROOT / '.runtime' / 'build-cache-template'
    cache.mkdir(parents=True, exist_ok=True)
    for path in (dist, work):
        clean_build_directory(path)
    spec = ROOT / '.runtime' / 'template_studio.spec'
    from PyInstaller.utils.win32.versioninfo import (
        FixedFileInfo, StringFileInfo, StringStruct, StringTable,
        VarFileInfo, VarStruct, VSVersionInfo,
    )
    version_tuple = tuple(int(part) for part in VERSION.split('.')) + (0,)
    version_info = VSVersionInfo(
        ffi=FixedFileInfo(filevers=version_tuple, prodvers=version_tuple),
        kids=[StringFileInfo([StringTable('040904B0', [
            StringStruct('FileDescription', 'Beta Render'),
            StringStruct('ProductName', 'Beta Render'),
            StringStruct('FileVersion', VERSION),
            StringStruct('ProductVersion', VERSION),
            StringStruct('OriginalFilename', 'TemplateStudio.exe'),
        ])]), VarFileInfo([VarStruct('Translation', [1033, 1200])])],
    )
    version_file = ROOT / '.runtime' / 'beta-render-version.txt'
    version_file.write_text(str(version_info), encoding='utf-8')
    args = [sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean', '--onedir', '--windowed', '--noupx',
            '--version-file', str(version_file),
            '--icon', str(ROOT / 'template_studio/assets/beta-render.ico'),
            '--name', 'TemplateStudio', '--distpath', str(dist), '--workpath', str(work), '--specpath', str(spec.parent),
            '--paths', str(ROOT), '--collect-submodules', 'template_studio', '--collect-submodules', 'offline_studio',
            '--collect-all', 'video_fx',
            '--collect-all', 'moderngl', '--collect-all', 'glcontext',
            '--exclude-module', 'tkinter', '--exclude-module', 'PySide6.QtWebEngineWidgets',
            '--exclude-module', 'PySide6.QtWebEngineCore', '--exclude-module', 'PySide6.QtWebEngineQuick',
            '--add-data', f'{ROOT / "template_studio/Main.qml"};template_studio',
            '--add-data', f'{ROOT / "template_studio/Production.qml"};template_studio',
            '--add-data', f'{ROOT / "template_studio/assets"};template_studio/assets',
            '--add-data', f'{ROOT / "template_studio/apply_update.ps1"};template_studio',
            str(ROOT / 'template_studio/frozen_entry.py')]
    env = os.environ.copy()
    env.update(TEMP=str(cache), TMP=str(cache), PYINSTALLER_CONFIG_DIR=str(cache / 'pyinstaller'))
    # Không lấy DLL từ PATH của ứng dụng khác (ví dụ ICU của Poppler không tương thích Qt).
    import PySide6
    runtime_paths = [Path(sys.executable).parent, Path(sys.base_prefix), Path(PySide6.__file__).parent,
                     Path(os.environ.get('SystemRoot', r'C:\Windows')) / 'System32',
                     Path(os.environ.get('SystemRoot', r'C:\Windows'))]
    env['PATH'] = os.pathsep.join(str(path) for path in runtime_paths)
    env['QT_PLUGIN_PATH'] = str(Path(PySide6.__file__).parent / 'plugins')
    env['QML2_IMPORT_PATH'] = str(Path(PySide6.__file__).parent / 'qml')
    env['QML_IMPORT_PATH'] = env['QML2_IMPORT_PATH']
    subprocess.run(args, cwd=ROOT, env=env, check=True)
    target = ROOT / 'release' / 'template-studio' / 'TemplateStudio'
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        if not (target / 'release.json').is_file() or any((target / name).exists() for name in ('data', 'exports', 'runtime')):
            raise RuntimeError('Thư mục build cũ chứa dữ liệu hoặc chưa có manifest. Hãy dời nó trước khi build lại.')
        clean_build_directory(target)
    shutil.copytree(dist / 'TemplateStudio', target)
    for name in ('LICENSE', 'THIRD_PARTY_NOTICES.md', 'README.md'):
        shutil.copy2(ROOT / name, target / name)
    collect_licenses(target)
    (target / 'release.json').write_text(json.dumps(dict(version=VERSION, platform='windows-x64')), encoding='utf-8')
    archive = Path(shutil.make_archive(str(target.parent / Path(ASSET_NAME).stem), 'zip', root_dir=target.parent, base_dir=target.name))
    with archive.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    archive.with_suffix(archive.suffix + '.sha256').write_text(f'{digest}  {archive.name}\n', encoding='ascii')
    print('Đã build:', target / 'TemplateStudio.exe')
    print('Gói phát hành:', archive)


if __name__ == '__main__':
    main()
