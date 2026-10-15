param(
    [string]$InputVideo = (Join-Path $PSScriptRoot "..\02_REFERENCE_MEDIA\source_original_compre_juguetes.mp4"),
    [string]$OutputVideo = (Join-Path $PSScriptRoot "artifacts\benchmark_1080_10s.mp4"),
    [string]$Python = (Join-Path $PSScriptRoot ".venv\Scripts\python.exe")
)
$ErrorActionPreference = "Stop"
$env:PYTHONUTF8 = "1"
& $Python (Join-Path $PSScriptRoot "render.py") $InputVideo $OutputVideo --preset capcut-pentagon --encoder h264_nvenc --seconds 10 --overwrite
exit $LASTEXITCODE
