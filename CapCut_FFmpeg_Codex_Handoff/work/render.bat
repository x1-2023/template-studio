@echo off
setlocal
set "PYTHONUTF8=1"
if not exist "%~dp0.venv\Scripts\python.exe" (
    echo Can chay setup.ps1 truoc.
    exit /b 1
)
"%~dp0.venv\Scripts\python.exe" "%~dp0render.py" %*
exit /b %errorlevel%
