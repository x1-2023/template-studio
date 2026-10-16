"""Điều phối GUI riêng, hàng đợi tuần tự và preview đã render thật."""
import argparse
import json
import os
import re
import sys
import time
import uuid
from pathlib import Path
from PySide6.QtCore import QObject, Property, Signal, Slot, QUrl, QTimer, QLockFile
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QApplication, QFileDialog
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickWindow
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtMultimedia import QMediaPlayer  # noqa: F401 — nạp DLL trước khi Qt tải plugin QML.
from offline_studio.services import TaskPool
from offline_studio.config import atomic_json
from offline_studio.hardware import detect, format_time
from offline_studio.media import scan
from offline_studio.process import binary
from offline_studio.cancellation import TaskCancelled, check_cancelled
from .render import DEFAULTS, normalize, render
from .version import VERSION
from .updater import check_update, prepare_update, launch_update
from .effects import catalog, thumbnails, effect_name
from .media_setup import ensure_media
from .production import Production


class Controller(QObject):
    changed = Signal()
    closeReady = Signal()

    def __init__(self, root, home):
        super().__init__()
        self.root, self.home = root, home
        self.pool = TaskPool(self)
        self.pool.pool.setMaxThreadCount(1)
        self._busy, self._closing, self._preview, self._index = False, False, '', -1
        self._notice = 'Thêm video để bắt đầu · Ctrl+O'
        self._hardware = 'Đang nhận diện phần cứng…'
        self._nvenc = False
        self._media_busy, self._media_ready = False, False
        self._update_busy, self._available_update, self._update_plan = False, None, None
        self._update_notice = 'Kiểm tra bản mới trên GitHub'
        self._library = [dict(entry) for entry in catalog()]
        self._library_candidate, self._library_preview = 'none', ''
        self._candidate_intensity, self._candidate_duration = 65, 0
        self._thumbnail_source = 'Ảnh mẫu · cường độ 65%'
        self._settings, self._rows = dict(DEFAULTS), []
        self._output = str(home / 'exports')
        try:
            saved = json.loads((home / 'session.json').read_text(encoding='utf-8-sig'))
            self._settings = normalize(saved['settings'])
            self._output = saved['output']
            self._rows = [r for r in saved['rows'] if Path(r['path']).is_file()]
            for row in self._rows:
                if row['status'] == 'Đang xuất':
                    row['status'] = 'Đã dừng'
            self._index = 0 if self._rows else -1
        except (OSError, ValueError, KeyError, TypeError):
            pass
        self._production = Production(self)
        self.prepareMedia()

    @Property(QObject, constant=True)
    def production(self):
        return self._production

    @Property(bool, notify=changed)
    def mediaReady(self):
        return self._media_ready

    @Slot()
    def prepareMedia(self):
        if self.busy or self.pool.active:
            return
        self._media_busy = True
        self.changed.emit()
        def work(emit):
            ensure_media(self.home, lambda notice: emit({'notice': notice}))
            return detect()
        def ready(info):
            self._media_ready = True
            self.hardware_ready(info)
            self.message('FFmpeg sẵn sàng · thêm video hoặc mở thư viện filter.')
        def failed(error):
            self._media_ready = False
            self.message('Không chuẩn bị được FFmpeg: ' + error + ' · bấm Chuẩn bị FFmpeg để thử lại.')
        def finished():
            self._media_busy = False
            self.changed.emit()
            if self._closing:
                self.close_when_ready()
        self.pool.submit(work, result=ready, error=failed, event=self.task_event, finished=finished)

    @Property('QVariantList', notify=changed)
    def rows(self):
        return self._rows

    @Property('QVariantMap', notify=changed)
    def settings(self):
        return self._settings

    @Property('QVariantList', notify=changed)
    def library(self):
        return self._library

    @Property(str, notify=changed)
    def effectName(self):
        return effect_name(self._settings['effect'])

    @Property(str, notify=changed)
    def candidateEffect(self):
        return self._library_candidate

    @Property(float, notify=changed)
    def candidateIntensity(self):
        return self._candidate_intensity

    @Property(float, notify=changed)
    def candidateDuration(self):
        return self._candidate_duration

    @Slot(str, float)
    def configureCandidate(self, key, value):
        if self.busy or key not in {'effectIntensity', 'effectDuration'}:
            return
        settings = normalize({**self._settings, key: value})
        if key == 'effectIntensity':
            self._candidate_intensity = settings[key]
        else:
            self._candidate_duration = settings[key]
        self._library_preview = ''
        self.changed.emit()

    @Property(str, notify=changed)
    def libraryPreviewUrl(self):
        return self._library_preview

    @Property(str, notify=changed)
    def thumbnailSource(self):
        return self._thumbnail_source

    @Slot()
    def refreshLibrary(self):
        if self.busy:
            return
        source = self._rows[self._index]['path'] if self._index >= 0 else None
        self._busy = True
        self.message('Đang tạo thumbnail thư viện filter…')
        def ready(entries):
            self._library = entries
            self._thumbnail_source = ('Ảnh từ ' + Path(source).name if source else 'Ảnh mẫu') + ' · cường độ 65%'
            self.message('Thư viện sẵn sàng · chọn filter, xem preview rồi áp dụng vào cấu hình.')
        self.pool.submit(lambda emit: thumbnails(self.home, source), result=ready,
                         error=self.message, finished=self.finish)

    @Slot(str)
    def inspectEffect(self, slug):
        if self.busy or slug not in {entry['id'] for entry in self._library}:
            return
        self._library_candidate, self._library_preview = slug, ''
        self._candidate_intensity = self._settings['effectIntensity']
        self._candidate_duration = self._settings['effectDuration']
        self.changed.emit()

    @Slot()
    def applyEffect(self):
        if not self.busy:
            self.set_settings({**self._settings, 'effect': self._library_candidate,
                               'effectIntensity': self._candidate_intensity, 'effectDuration': self._candidate_duration})
            self.message('Đã áp dụng ' + self.effectName + ' vào cấu hình chung của cả danh sách.')

    @Slot()
    def previewEffect(self):
        if self.busy or self._index < 0:
            return
        source = self._rows[self._index]['path']
        settings = {**self._settings, 'effect': self._library_candidate,
                    'effectIntensity': self._candidate_intensity, 'effectDuration': self._candidate_duration}
        self._busy, self._library_preview = True, ''
        self.message('Đang tạo preview video của ' + effect_name(self._library_candidate) + '…')
        folder = self.home / 'cache/previews'
        folder.mkdir(parents=True, exist_ok=True)
        destination = folder / ('preview-' + uuid.uuid4().hex + '.mp4')
        def work(emit):
            return render(source, destination, settings, self._nvenc, preview=True,
                          progress=lambda p: emit({'notice': f'Preview filter · {p:.0f}%'}))
        def ready(result):
            self._library_preview = QUrl.fromLocalFile(result['path']).toString()
            self.message('Preview filter sẵn sàng · bấm Áp dụng để lưu vào cấu hình.')
        self.pool.submit(work, result=ready, error=self.message, event=self.task_event, finished=self.finish)

    @Property(bool, notify=changed)
    def busy(self):
        return self._busy or self._update_busy or self._media_busy

    @Property(str, constant=True)
    def version(self):
        return VERSION

    @Property(str, notify=changed)
    def updateNotice(self):
        return self._update_notice

    @Property(bool, notify=changed)
    def updateAvailable(self):
        return self._available_update is not None and getattr(sys, 'frozen', False)

    @Slot()
    def checkUpdates(self):
        if self.busy:
            return
        self._update_busy = True
        self._update_notice = 'Đang kiểm tra GitHub…'
        self.changed.emit()
        def ready(release):
            self._available_update = release
            self._update_notice = ('Có bản ' + release['version'] if release else 'Bạn đang dùng bản mới nhất')
            if release and not getattr(sys, 'frozen', False):
                self._update_notice += ' · bản source cập nhật bằng Git'
        def failed(error):
            self._update_notice = error
        self.pool.submit(lambda emit: check_update(), result=ready, error=failed, finished=self.finish_update)

    def finish_update(self):
        self._update_busy = False
        if self._update_plan:
            try:
                self.save()
                launch_update(self._update_plan)
            except (OSError, ValueError) as error:
                self._update_notice = 'Không mở được updater: ' + str(error)
                self._update_plan = None
            else:
                QApplication.instance().quit()
        self.changed.emit()
        if self._closing:
            self.close_when_ready()

    @Slot()
    def installUpdate(self):
        if self.busy or self.pool.active or not self._available_update:
            return
        self._update_busy = True
        self._update_notice = 'Đang tải và xác minh cập nhật…'
        self.changed.emit()
        def work(emit):
            return prepare_update(self._available_update, self.home,
                                  lambda percent: emit({'notice': f'Đang tải cập nhật · {percent:.0f}%'}))
        def ready(plan):
            self._update_plan = plan
        def failed(error):
            self._update_notice = error
        self.pool.submit(work, result=ready, error=failed, event=self.task_event, finished=self.finish_update)

    @Property(str, notify=changed)
    def notice(self):
        return self._notice

    @Property(str, notify=changed)
    def hardware(self):
        return self._hardware

    @Property(str, notify=changed)
    def output(self):
        return self._output

    @Property(str, notify=changed)
    def previewUrl(self):
        return self._preview

    @Property(int, notify=changed)
    def currentIndex(self):
        return self._index

    def hardware_ready(self, info):
        self._nvenc = info['nvenc']
        gpu = ', '.join(g['name'] for g in info['gpus'])
        self._hardware = ((gpu or info['cpu']) + ' · NVENC' if self._nvenc else info['cpu'] + ' · CPU')
        self.changed.emit()

    def save(self):
        atomic_json(self.home / 'session.json', dict(settings=self._settings, rows=self._rows, output=self._output))
        if hasattr(self, '_production'):
            self._production.save()

    def message(self, value):
        self._notice = value
        self.changed.emit()

    @Slot(str, 'QVariant')
    def configure(self, key, value):
        if not self.busy and key in DEFAULTS:
            self.set_settings({**self._settings, key: value})

    def set_settings(self, settings):
        normalized = normalize(settings)
        if normalized != self._settings:
            self._settings = normalized
            self._preview = ''
            for row in self._rows:
                if row['status'] == 'Hoàn tất':
                    row.update(status='Chờ xử lý', percent=0, detail='Cấu hình đã thay đổi; xuất lại sẽ tạo file mới.')
            self.save()
            self.changed.emit()

    @Slot()
    def importFiles(self):
        paths, _ = QFileDialog.getOpenFileNames(None, 'Thêm video', '', 'Video (*.mp4 *.mov *.mkv *.webm *.avi)')
        self.add_paths(paths)

    @Slot()
    def importFolder(self):
        path = QFileDialog.getExistingDirectory(None, 'Thêm thư mục video')
        if path:
            self.add_paths([path])

    @Slot('QVariantList')
    def dropFiles(self, urls):
        self.add_paths([QUrl(str(url)).toLocalFile() for url in urls])

    def add_paths(self, paths):
        if self.busy or not paths:
            return
        try:
            seen = {r['path'].casefold() for r in self._rows}
            for row in scan(paths):
                if row['path'].casefold() not in seen and len(self._rows) < 200:
                    self._rows.append(dict(path=row['path'], name=row['name'], status='Chờ xử lý',
                                           percent=0, detail='', result=''))
                    seen.add(row['path'].casefold())
            if self._index < 0 and self._rows:
                self._index = 0
            self.save()
            self.message(f'{len(self._rows)}/200 video · một cấu hình cho cả danh sách')
        except Exception as error:
            self.message(str(error))

    @Slot(int)
    def select(self, index):
        if not self.busy and 0 <= index < len(self._rows):
            self._index, self._preview = index, ''
            self._library_preview = ''
            self.changed.emit()

    @Slot()
    def remove(self):
        if not self.busy and 0 <= self._index < len(self._rows):
            self._rows.pop(self._index)
            self._index = min(self._index, len(self._rows)-1)
            self._preview = ''
            self.save()
            self.changed.emit()

    @Slot()
    def clear(self):
        if not self.busy:
            self._rows, self._index, self._preview = [], -1, ''
            self.save()
            self.changed.emit()

    @Slot()
    def chooseOutput(self):
        folder = QFileDialog.getExistingDirectory(None, 'Thư mục xuất', self._output)
        if folder:
            self._output = folder
            self.save()
            self.changed.emit()

    @Slot()
    def openOutput(self):
        Path(self._output).mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(self._output))

    def task_event(self, event):
        if 'index' in event:
            self._rows[event['index']].update(event['values'])
            if event.get('save'):
                self.save()
        if 'notice' in event:
            self._notice = event['notice']
        self.changed.emit()

    def finish(self):
        for row in self._rows:
            if row['status'] == 'Đang xuất':
                row.update(status='Đã dừng', detail='Có thể chạy lại')
        self._busy = False
        self.save()
        self.changed.emit()
        if self._closing:
            self.closeReady.emit()

    @Slot(float)
    def preview(self, offset=0):
        if self.busy or self._index < 0:
            return
        source = self._rows[self._index]['path']
        settings = dict(self._settings)
        self._busy, self._preview = True, ''
        self.message('Đang tạo preview 8 giây bằng đúng template…')
        folder = self.home / 'cache/previews'
        folder.mkdir(parents=True, exist_ok=True)
        # Cache chỉ chứa clip do app tạo; giữ tối đa 5 bản.
        for old in sorted(folder.glob('preview-*.mp4'), key=lambda p: p.stat().st_mtime)[:-4]:
            try:
                old.unlink()
            except OSError:
                pass
        destination = folder / ('preview-' + uuid.uuid4().hex + '.mp4')
        def work(emit):
            return render(source, destination, settings, self._nvenc, preview=True, offset=offset,
                          progress=lambda p: emit({'notice': f'Đang tạo preview · {p:.0f}%'}))
        def ready(result):
            self._preview = QUrl.fromLocalFile(result['path']).toString()
            self.message(f'Preview sẵn sàng · tạo trong {result["elapsed"]:.1f}s · 360 × 640 / 30 FPS')
        self.pool.submit(work, result=ready, error=self.message, event=self.task_event, finished=self.finish)

    @Slot()
    def runBatch(self):
        if self.busy or not self._rows:
            return
        pending = [(i, r['path']) for i, r in enumerate(self._rows) if r['status'] != 'Hoàn tất']
        if not pending:
            self.message('Tất cả đã hoàn tất. Thêm video mới hoặc bỏ rồi thêm lại để xuất bản khác.')
            return
        settings, output = dict(self._settings), Path(self._output)
        self._busy = True
        self.message('Đang xuất tuần tự…')
        def work(emit):
            began = time.monotonic()
            completed = 0
            for index, source in pending:
                check_cancelled()
                started = time.monotonic()
                emit(dict(index=index, values=dict(status='Đang xuất', percent=0, detail='Đang chuẩn bị'), save=True))
                def update(percent):
                    elapsed = time.monotonic()-started
                    eta = elapsed * (100-percent)/percent if percent > 1 else 0
                    emit(dict(index=index, values=dict(percent=round(percent),
                              detail=f'Đã chạy {format_time(elapsed)} · còn ~{format_time(eta)}')))
                destination = output / (Path(source).stem + '_template_' + uuid.uuid4().hex[:8] + '.mp4')
                try:
                    result = render(source, destination, settings, self._nvenc, progress=update)
                    completed += 1
                    emit(dict(index=index, values=dict(status='Hoàn tất', percent=100, result=result['path'],
                              detail=f'{format_time(result["elapsed"])} · {destination.stat().st_size/1024**2:.1f} MiB'), save=True))
                except TaskCancelled:
                    raise
                except Exception as error:
                    emit(dict(index=index, values=dict(status='Lỗi', detail=str(error)[-1200:]), save=True))
            return f'Hoàn tất {completed}/{len(pending)} video · tổng {format_time(time.monotonic()-began)}'
        self.pool.submit(work, result=self.message, error=self.message, event=self.task_event, finished=self.finish)

    @Slot()
    def stop(self):
        for task in tuple(self.pool.active):
            task.cancel.set()
        self.message('Đang dừng… giữ các video đã hoàn tất.')

    @Slot(result=bool)
    def requestClose(self):
        if self.busy or self.pool.active:
            self._closing = True
            self.stop()
            QTimer.singleShot(200, self.close_when_ready)
            return False
        self.save()
        return True

    def close_when_ready(self):
        if self.pool.active:
            QTimer.singleShot(200, self.close_when_ready)
        else:
            self.closeReady.emit()


def main(root, home):
    home.mkdir(parents=True, exist_ok=True)
    os.environ['TEMPLATE_STUDIO_HOME'] = str(home)
    parser = argparse.ArgumentParser(description='Template Studio · app riêng xử lý video dọc')
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--capture')
    parser.add_argument('--input', action='append', default=[])
    parser.add_argument('--update-token')
    parser.add_argument('--library', action='store_true')
    options = parser.parse_args()
    # Kiểm tra module worker độc lập trước khi bắt đầu các bước thiết lập dài.
    # Thiếu cache/driver không làm updater hiểu nhầm bản EXE bị hỏng.
    if options.update_token:
        from .worker_client import run_worker
        run_worker(root,home,dict(action='health',structural=True,timeout=120))
    QQuickStyle.setStyle('Basic')
    app = QApplication([])
    app.setApplicationName('Template Studio')
    lock = QLockFile(str(home / 'app.lock'))
    if not options.check and not lock.tryLock(0):
        raise RuntimeError('Template Studio đã mở. Hãy dùng cửa sổ hiện tại.')
    controller = Controller(root, home)
    def initial_inputs():
        if controller.busy or controller.pool.active:
            QTimer.singleShot(100, initial_inputs)
            return
        if options.input:
            (controller.add_paths if options.library else controller.production.add_paths)(options.input)
        if options.library:
            controller.refreshLibrary()
        elif not options.check:
            def runtime():
                if controller.pool.active or controller.busy:
                    QTimer.singleShot(200,runtime)
                else:
                    controller.production.checkRuntime()
            QTimer.singleShot(200,runtime)
    QTimer.singleShot(0, initial_inputs)
    engine = QQmlApplicationEngine()
    errors = []
    engine.warnings.connect(lambda messages: errors.extend(m.toString() for m in messages))
    engine.rootContext().setContextProperty('studio', controller)
    engine.rootContext().setContextProperty('startInLibrary', options.library)
    engine.load(QUrl.fromLocalFile(str(root / ('template_studio/Main.qml' if options.library else 'template_studio/Production.qml'))))
    if not engine.rootObjects():
        raise RuntimeError('Không nạp được giao diện: ' + '\n'.join(errors))
    if options.update_token and re.fullmatch(r'[a-f0-9]{32}', options.update_token):
        job = Path(sys.executable).resolve().parent / '.updates' / options.update_token
        if job.is_dir():
            def report_healthy():
                if not errors:atomic_json(job / 'healthy.json', {'version': VERSION})
            QTimer.singleShot(1500,report_healthy)
    if getattr(sys, 'frozen', False) and not options.check:
        QTimer.singleShot(3500, controller.checkUpdates)
    if options.check:
        def finish():
            if controller.pool.active:
                QTimer.singleShot(200, finish)
                return
            if options.capture:
                from shiboken6 import getCppPointer, wrapInstance
                window = wrapInstance(getCppPointer(engine.rootObjects()[0])[0], QQuickWindow)
                capture = Path(options.capture).resolve()
                if not window.grabWindow().save(str(capture)):
                    errors.append('Không lưu được ảnh kiểm tra.')
            if not controller.mediaReady:
                errors.append('FFmpeg chưa sẵn sàng.')
            diagnostic = dict(ok=not errors, errors=errors, hardware=controller.hardware,
                              mediaReady=controller.mediaReady, ffmpeg=binary('ffmpeg') if controller.mediaReady else '')
            atomic_json(home / 'check-result.json', diagnostic)
            print(json.dumps(diagnostic, ensure_ascii=False))
            app.exit(1 if errors else 0)
        QTimer.singleShot(1500, finish)
    return app.exec()
