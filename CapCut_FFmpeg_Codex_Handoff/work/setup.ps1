param([string]$Python = "py", [switch]$SkipInstall)
$ErrorActionPreference = "Stop"
$env:PYTHONUTF8 = "1"
$pythonPath = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $pythonPath)) {
    if ($Python -eq "py") { & $Python -3 -m venv (Join-Path $PSScriptRoot ".venv") }
    else { & $Python -m venv (Join-Path $PSScriptRoot ".venv") }
    if ($LASTEXITCODE -ne 0) { throw "Khong tao duoc venv" }
}
if (-not $SkipInstall) {
    & $pythonPath -m pip install -r (Join-Path $PSScriptRoot "requirements.txt")
    if ($LASTEXITCODE -ne 0) { throw "Khong cai duoc dependencies" }
}
foreach ($tool in @("ffmpeg", "ffprobe")) {
    if (-not (Get-Command $tool -ErrorAction SilentlyContinue)) { throw "Can $tool trong PATH" }
}
& $pythonPath (Join-Path $PSScriptRoot "prepare_cache.py")
if ($LASTEXITCODE -ne 0) { throw "Khong chuan bi duoc cache" }
& $pythonPath (Join-Path $PSScriptRoot "inspect_cache.py")
if ($LASTEXITCODE -ne 0) { throw "Khong doc duoc shader" }
Write-Host "San sang. Chay render.bat source.mp4 output.mp4 --seconds 3"
