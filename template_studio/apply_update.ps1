# Chỉ thay các thành phần của app; giữ nguyên data và exports.
param([Parameter(Mandatory = $true)][string]$PlanPath)
$ErrorActionPreference = 'Stop'
$plan = Get-Content -LiteralPath $PlanPath -Raw -Encoding UTF8 | ConvertFrom-Json
$target = [IO.Path]::GetFullPath($plan.target).TrimEnd('\')
$stage = [IO.Path]::GetFullPath($plan.stage).TrimEnd('\')
$job = [IO.Path]::GetFullPath($plan.job).TrimEnd('\')
$backup = Join-Path $job 'backup'
$log = Join-Path $job 'result.txt'
$managed = @('TemplateStudio.exe', '_internal', 'LICENSE', 'THIRD_PARTY_NOTICES.md', 'README.md', 'release.json')
$moved = [Collections.Generic.List[string]]::new()
$installed = [Collections.Generic.List[string]]::new()
$newProcess = $null
$committed = $false

function Assert-Child([string]$parent, [string]$child) {
    $absolute = [IO.Path]::GetFullPath($child)
    if (-not $absolute.StartsWith($parent.TrimEnd('\') + '\', [StringComparison]::OrdinalIgnoreCase)) {
        throw 'Duong dan vuot ngoai thu muc du kien.'
    }
    $cursor = $absolute
    while ($cursor -and $cursor.Length -ge $parent.Length) {
        if (Test-Path -LiteralPath $cursor) {
            $entry = Get-Item -LiteralPath $cursor -Force
            if ($entry.Attributes -band [IO.FileAttributes]::ReparsePoint) {
                throw 'Khong cap nhat qua junction hoac symbolic link.'
            }
        }
        $cursor = [IO.Path]::GetDirectoryName($cursor)
    }
}

try {
    if ($plan.token -notmatch '^[a-f0-9]{32}$' -or $plan.version -notmatch '^\d+\.\d+\.\d+$') {
        throw 'Manifest cap nhat khong hop le.'
    }
    Assert-Child $job $stage
    Assert-Child $job $backup
    $manifest = Get-Content -LiteralPath (Join-Path $stage 'release.json') -Raw | ConvertFrom-Json
    if ($manifest.version -ne $plan.version -or $manifest.platform -ne 'windows-x64') {
        throw 'Phien ban staging khong khop.'
    }
    if (-not (Test-Path -LiteralPath (Join-Path $target 'TemplateStudio.exe') -PathType Leaf)) {
        throw 'Khong tim thay ban hien tai.'
    }
    # Chờ app tự đóng; không buộc dừng tác vụ render hoặc tiến trình khác.
    $parent = Get-Process -Id $plan.parent_pid -ErrorAction SilentlyContinue
    if ($parent -and -not $parent.WaitForExit(120000)) { throw 'App chua dong sau 120 giay.' }
    New-Item -ItemType Directory -Path $backup | Out-Null
    foreach ($name in $managed) {
        $oldPath = Join-Path $target $name
        $newPath = Join-Path $stage $name
        Assert-Child $target $oldPath
        Assert-Child $stage $newPath
        Assert-Child $backup (Join-Path $backup $name)
        if (Test-Path -LiteralPath $oldPath) {
            Move-Item -LiteralPath $oldPath -Destination (Join-Path $backup $name)
            $moved.Add($name)
        }
        if (Test-Path -LiteralPath $newPath) {
            Move-Item -LiteralPath $newPath -Destination $oldPath
            $installed.Add($name)
        }
    }
    $healthy = Join-Path $job 'healthy.json'
    $env:TEMPLATE_STUDIO_HOME = $plan.home
    $env:PYINSTALLER_RESET_ENVIRONMENT = '1'
    $newProcess = Start-Process -FilePath (Join-Path $target 'TemplateStudio.exe') -WorkingDirectory $target -ArgumentList @('--update-token', $plan.token) -PassThru -WindowStyle Normal
    $deadline = [DateTime]::UtcNow.AddSeconds(45)
    while ([DateTime]::UtcNow -lt $deadline -and -not (Test-Path -LiteralPath $healthy)) {
        if ($newProcess.HasExited) { throw 'Ban moi khong khoi dong duoc.' }
        Start-Sleep -Milliseconds 250
        $newProcess.Refresh()
    }
    if (-not (Test-Path -LiteralPath $healthy)) { throw 'Ban moi khong bao san sang.' }
    $health = Get-Content -LiteralPath $healthy -Raw | ConvertFrom-Json
    if ($health.version -ne $plan.version) { throw 'Ban moi bao sai phien ban.' }
    $committed = $true
    'Da cap nhat thanh cong. Ban cu duoc giu trong backup.' | Set-Content -LiteralPath $log -Encoding UTF8
} catch {
    $reason = $_.Exception.Message
    if (-not $committed) {
        if ($newProcess -and -not $newProcess.HasExited) {
            Stop-Process -Id $newProcess.Id -Force -ErrorAction SilentlyContinue
            $newProcess.WaitForExit(10000) | Out-Null
        }
        try {
            # Chuyển bản lỗi về staging, rồi khôi phục đúng các mục đã sao lưu.
            foreach ($name in $installed) {
                $badPath = Join-Path $target $name
                Assert-Child $target $badPath
                Assert-Child $stage (Join-Path $stage $name)
                Move-Item -LiteralPath $badPath -Destination (Join-Path $stage $name)
            }
            foreach ($name in $moved) {
                Assert-Child $backup (Join-Path $backup $name)
                Assert-Child $target (Join-Path $target $name)
                Move-Item -LiteralPath (Join-Path $backup $name) -Destination (Join-Path $target $name)
            }
            if ($moved.Count -gt 0) {
                $env:TEMPLATE_STUDIO_HOME = $plan.home
                $env:PYINSTALLER_RESET_ENVIRONMENT = '1'
                Start-Process -FilePath (Join-Path $target 'TemplateStudio.exe') -WorkingDirectory $target -WindowStyle Normal
            }
        } catch { $reason += ' | Loi phuc hoi: ' + $_.Exception.Message }
    }
    ('Cap nhat that bai: ' + $reason) | Set-Content -LiteralPath $log -Encoding UTF8
    exit 1
}
