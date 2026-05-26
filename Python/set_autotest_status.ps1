param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("waiting_fix", "codex_working", "ready_to_run", "running", "success", "failed", "stopped")]
    [string]$State,

    [string]$Note = "",

    [string]$Script = "",

    [string]$Log = ""
)

$root = Split-Path -Parent $PSScriptRoot
$statusPath = Join-Path $PSScriptRoot "autotest_status.json"

if (-not $Script) {
    $latestScript = Get-ChildItem -Path $PSScriptRoot -Filter "*.py" |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1

    if ($latestScript) {
        $Script = $latestScript.FullName
    }
}

if (-not $Log) {
    $latestLog = Get-ChildItem -Path (Join-Path $root "LOG") -Filter "log_python_*.txt" -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1

    if ($latestLog) {
        $Log = $latestLog.FullName
    }
}

$scriptWriteTimeUtc = ""

if ($Script -and (Test-Path -LiteralPath $Script)) {
    $scriptWriteTimeUtc = (Get-Item -LiteralPath $Script).LastWriteTimeUtc.ToString("o")
}

$status = [ordered]@{
    state = $State
    script = $Script
    log = $Log
    updated_at = (Get-Date).ToString("yyyy-MM-ddTHH:mm:ss.fffzzz")
    script_write_time_utc = $scriptWriteTimeUtc
    note = $Note
}

$status | ConvertTo-Json -Depth 3 | Set-Content -LiteralPath $statusPath -Encoding UTF8
Get-Content -LiteralPath $statusPath
