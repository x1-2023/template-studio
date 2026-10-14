"""Tác vụ Qt và giao tiếp engine offline trong cùng ứng dụng."""
import os
import subprocess
import sys
import threading
from pathlib import Path
from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal
from .cancellation import TaskCancelled, cancellation_scope, check_cancelled, managed_process
from .config import ROOT, ASSETS, DATA, APP_ROOT, LANGUAGES, STYLES, DEFAULT_RECIPE, normalize_recipe

NO_WINDOW = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0

def default_setup():
    model = ASSETS / 'ggml-base.bin'
    if not model.is_file():
        model = APP_ROOT / 'runtime/media/ggml-base.bin'
    return {'outputDir': str(APP_ROOT / 'exports' / 'offline'), 'modelPath': str(model)}

def backend_call(setup, request, emit=lambda event: None):
    import copy
    from .batch import dispatch
    request = copy.deepcopy(request)
    if request.get('action') == 'render':
        request['recipe']['captions']['model_path'] = setup['modelPath']
    return dispatch(request, emit)

class TaskSignals(QObject):
    result = Signal(object)
    error = Signal(str)
    event = Signal(object)
    finished = Signal()


class Task(QRunnable):
    def __init__(self, function):
        super().__init__()
        self.function = function
        self.signals = TaskSignals()
        self.cancel = threading.Event()

    def run(self):
        try:
            with cancellation_scope(self.cancel):
                result = self.function(self.signals.event.emit)
                check_cancelled()
                self.signals.result.emit(result)
        except TaskCancelled:
            pass
        except Exception as error:
            if not self.cancel.is_set():
                self.signals.error.emit(str(error))
        finally:
            self.signals.finished.emit()


class TaskPool(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.pool = QThreadPool(self)
        self.pool.setMaxThreadCount(4)
        self.active = set()
        self.accepting = True

    def shutdown(self, cancel=False):
        self.accepting = False
        if cancel:
            for task in tuple(self.active):
                task.cancel.set()

    def submit(self, function, result=None, error=None, event=None, finished=None):
        if not self.accepting:
            return None
        task = Task(function)
        self.active.add(task)
        for signal, callback in [(task.signals.result, result), (task.signals.error, error),
                                 (task.signals.event, event), (task.signals.finished, finished)]:
            if callback:
                signal.connect(callback)
        task.signals.finished.connect(lambda: self.active.discard(task))
        self.pool.start(task)
        return task
