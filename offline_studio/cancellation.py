"""Hủy hợp tác theo tác vụ; chỉ dừng cây tiến trình do tác vụ đó tạo."""
import os
import signal
import subprocess
import threading
from contextlib import contextmanager, suppress


class TaskCancelled(Exception):
    """Người dùng đã yêu cầu dừng, không coi là lỗi cần thử lại."""


_context = threading.local()


def check_cancelled():
    event = getattr(_context, 'cancel', None)
    if event is not None and event.is_set():
        raise TaskCancelled('Đã dừng tác vụ theo yêu cầu.')


@contextmanager
def cancellation_scope(event):
    previous = getattr(_context, 'cancel', None)
    _context.cancel = event
    try:
        check_cancelled()
        yield
    finally:
        _context.cancel = previous


class _WindowsJob:
    """Giữ cây tiến trình kể cả khi PID cha đã thoát trước lúc người dùng hủy."""
    def __init__(self, process):
        import ctypes
        from ctypes import wintypes
        self.api = ctypes.WinDLL('kernel32', use_last_error=True)
        self.api.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
        self.api.CreateJobObjectW.restype = wintypes.HANDLE
        self.api.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
        self.api.AssignProcessToJobObject.restype = wintypes.BOOL
        self.api.TerminateJobObject.argtypes = [wintypes.HANDLE, wintypes.UINT]
        self.api.TerminateJobObject.restype = wintypes.BOOL
        self.api.CloseHandle.argtypes = [wintypes.HANDLE]
        self.api.CloseHandle.restype = wintypes.BOOL
        self.handle = self.api.CreateJobObjectW(None, None)
        if not self.handle:
            raise ctypes.WinError(ctypes.get_last_error())
        if not self.api.AssignProcessToJobObject(self.handle, int(process._handle)):
            error = ctypes.WinError(ctypes.get_last_error())
            self.close()
            raise error

    def terminate(self):
        return bool(self.api.TerminateJobObject(self.handle, 1))

    def close(self):
        self.api.CloseHandle(self.handle)


def _stop_process_tree(process, job=None):
    if job is not None and job.terminate():
        return
    if process.poll() is not None:
        return
    if os.name == 'nt':
        # Không dùng tên ứng dụng: chỉ PID con thuộc tác vụ hiện tại.
        try:
            subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           creationflags=subprocess.CREATE_NO_WINDOW, timeout=5)
        except (OSError, subprocess.TimeoutExpired):
            pass
    else:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    if process.poll() is None:
        process.kill()


@contextmanager
def managed_process(*args, **kwargs):
    """Ngắt cả khi stdout đang im lặng; không chặn luồng giao diện."""
    check_cancelled()
    if os.name != 'nt':
        kwargs.setdefault('start_new_session', True)
    process = subprocess.Popen(*args, **kwargs)
    job = None
    if os.name == 'nt':
        try:
            job = _WindowsJob(process)
        except OSError:
            # Một số môi trường Windows giới hạn Job Object: dự phòng bằng PID.
            pass
    cancel = getattr(_context, 'cancel', None)
    done = threading.Event()

    def watch():
        while not done.wait(.1):
            if cancel.is_set():
                _stop_process_tree(process, job)
                return

    watcher = threading.Thread(target=watch, daemon=True) if cancel is not None else None
    if watcher:
        watcher.start()
    try:
        yield process
    finally:
        # Giữ watcher sống đến khi tiến trình kết thúc, kể cả lúc đang wait().
        if process.poll() is None or job is not None:
            _stop_process_tree(process, job)
        process.wait()
        done.set()
        if watcher:
            watcher.join()
        if job is not None:
            job.close()
        for stream in (process.stdin, process.stdout, process.stderr):
            if stream is not None:
                # Lỗi flush/đóng pipe khi thu dọn không được che lỗi render gốc.
                with suppress(OSError):
                    stream.close()
