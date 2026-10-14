@echo off
setlocal
cd /d "%~dp0"
py -3 build_template.py %*
if errorlevel 1 pause
endlocal
