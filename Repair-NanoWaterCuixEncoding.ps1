param(
    [string]$ModuleRoot = "C:\Program Files\CSoft\Model Studio CS\NANOWATER",
    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function New-UnicodeString {
    param([int[]]$CodePoints)
    return -join ($CodePoints | ForEach-Object { [char]$_ })
}

function Write-Info {
    param([string]$Message)
    Write-Host ("[{0}] {1}" -f (Get-Date -Format "HH:mm:ss"), $Message)
}

function Load-CuixToTemp {
    param([string]$CuixPath)
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("dtmxtest_fix_" + [guid]::NewGuid().ToString("N"))
    [System.IO.Directory]::CreateDirectory($tempRoot) | Out-Null
    [System.IO.Compression.ZipFile]::ExtractToDirectory($CuixPath, $tempRoot)
    return $tempRoot
}

function Save-TempToCuix {
    param(
        [string]$TempRoot,
        [string]$DestinationCuixPath
    )

    if (Test-Path -LiteralPath $DestinationCuixPath) {
        Remove-Item -LiteralPath $DestinationCuixPath -Force
    }

    Add-Type -AssemblyName System.IO.Compression.FileSystem
    [System.IO.Compression.ZipFile]::CreateFromDirectory($TempRoot, $DestinationCuixPath)
}

function Backup-File {
    param(
        [string]$FilePath,
        [string]$BackupRoot
    )

    [System.IO.Directory]::CreateDirectory($BackupRoot) | Out-Null
    $backupName = "{0}.{1}.bak" -f ([System.IO.Path]::GetFileName($FilePath)), (Get-Date -Format "yyyyMMdd_HHmmss")
    $backupPath = Join-Path $BackupRoot $backupName
    Copy-Item -LiteralPath $FilePath -Destination $backupPath -Force
    return $backupPath
}

function Save-Utf8BomText {
    param(
        [string]$Path,
        [string]$Text
    )

    $encoding = New-Object System.Text.UTF8Encoding($true)
    [System.IO.File]::WriteAllText($Path, $Text, $encoding)
}

function Get-CyrillicScore {
    param([string]$Value)
    if ([string]::IsNullOrEmpty($Value)) { return 0 }
    return ([regex]::Matches($Value, '\p{IsCyrillic}')).Count
}

function Get-MojibakeScore {
    param([string]$Value)
    if ([string]::IsNullOrEmpty($Value)) { return 0 }
    return ([regex]::Matches($Value, $script:MojibakeRegex)).Count
}

function Convert-MojibakeText {
    param([string]$Value)
    if ([string]::IsNullOrEmpty($Value)) { return $Value }
    $cp1251 = [System.Text.Encoding]::GetEncoding(1251)
    return [System.Text.Encoding]::UTF8.GetString($cp1251.GetBytes($Value))
}

function Repair-TextFile {
    param([string]$Path)

    $original = [System.IO.File]::ReadAllText($Path, [System.Text.Encoding]::UTF8)
    $candidate = Convert-MojibakeText -Value $original

    $origCyr = Get-CyrillicScore -Value $original
    $candCyr = Get-CyrillicScore -Value $candidate
    $origBad = Get-MojibakeScore -Value $original
    $candBad = Get-MojibakeScore -Value $candidate

    if ($candidate -ne $original -and ($candCyr -gt $origCyr -or $candBad -lt $origBad)) {
        Save-Utf8BomText -Path $Path -Text $candidate
        return 1
    }

    return 0
}

function Repair-Cuix {
    param(
        [string]$CuixPath,
        [string]$BackupRoot
    )

    Write-Info "Repairing $CuixPath"
    $tempRoot = Load-CuixToTemp -CuixPath $CuixPath
    try {
        $changedTotal = 0
        Get-ChildItem -LiteralPath $tempRoot -Filter *.cui | ForEach-Object {
            $changed = Repair-TextFile -Path $_.FullName
            if ($changed -gt 0) {
                $changedTotal += $changed
                Write-Info (" - {0}: repaired raw text" -f $_.Name)
            }
        }

        if ($DryRun) {
            Write-Info "DryRun: no write for $CuixPath"
            return
        }

        $backupPath = Backup-File -FilePath $CuixPath -BackupRoot $BackupRoot
        Write-Info "Backup created: $backupPath"
        Save-TempToCuix -TempRoot $tempRoot -DestinationCuixPath $CuixPath
        Write-Info ("Saved repaired CUIX. Total fixed files: {0}" -f $changedTotal)
    }
    finally {
        if (Test-Path -LiteralPath $tempRoot) {
            Remove-Item -LiteralPath $tempRoot -Recurse -Force
        }
    }
}

$supportRoot = Join-Path $ModuleRoot "Support\WATER"
$backupRoot = Join-Path $supportRoot "DTMXtest-backup"
$script:MojibakeRegex = '[' + [regex]::Escape(
    (New-UnicodeString -CodePoints @(0x0420,0x0421,0x0402,0x0452,0x0403,0x0453,0x00D0,0x00D1))
) + ']'

Repair-Cuix -CuixPath (Join-Path $supportRoot "MSMAIN.cuix") -BackupRoot $backupRoot
Repair-Cuix -CuixPath (Join-Path $supportRoot "water.cuix") -BackupRoot $backupRoot
Write-Info "Encoding repair completed."
