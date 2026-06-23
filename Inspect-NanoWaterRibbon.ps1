param(
    [string]$ModuleRoot = "C:\Program Files\CSoft\Model Studio CS\NANOWATER",
    [string[]]$CuixNames = @("MSMAIN.cuix", "water.cuix"),
    [string]$LogPath = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Log {
    param([string]$Message)

    $line = "{0} | {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss.fff"), $Message
    Write-Host $line
    if ($script:ResolvedLogPath) {
        Add-Content -LiteralPath $script:ResolvedLogPath -Value $line -Encoding UTF8
    }
}

function Get-LogPath {
    param([string]$RequestedPath)

    if ($RequestedPath) {
        return $RequestedPath
    }

    $root = Join-Path $env:APPDATA "CSoft\Model Studio CS\Library3D\DTMXtestLogs"
    New-Item -ItemType Directory -Path $root -Force | Out-Null
    return (Join-Path $root ("NanoWaterRibbonInspect_{0}.log" -f (Get-Date -Format "yyyyMMdd_HHmmss")))
}

function Open-CuixXml {
    param([string]$CuixPath)

    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $zip = [System.IO.Compression.ZipFile]::OpenRead($CuixPath)
    try {
        $entry = $zip.GetEntry("MenuGroup.cui")
        if (-not $entry) {
            throw "Entry MenuGroup.cui not found in $CuixPath"
        }

        $stream = $entry.Open()
        try {
            $reader = New-Object System.IO.StreamReader($stream)
            try {
                $xmlText = $reader.ReadToEnd()
            }
            finally {
                $reader.Dispose()
            }
        }
        finally {
            $stream.Dispose()
        }

        $xml = New-Object xml
        $xml.LoadXml($xmlText)
        return $xml
    }
    finally {
        $zip.Dispose()
    }
}

function Get-ElementReport {
    param(
        [System.Xml.XmlDocument]$Xml,
        [string]$CuixName
    )

    $allNodes = $Xml.SelectNodes("//*")
    $interesting = foreach ($node in $allNodes) {
        if (-not $node.Name) { continue }
        if (
            $node.Name -match "Ribbon|Tab|Panel|Toolbar|ToolBar|MenuMacro|Menu|Workspace" -or
            ($node.Attributes["Name"] -and $node.Attributes["Name"].Value -match "Ribbon|Tab|Panel|Разное|Misc|DTMX|WATER|MS") -or
            ($node.Attributes["UID"] -and $node.Attributes["UID"].Value -match "Ribbon|Tab|Panel|Разное|Misc|DTMX|WATER|MS")
        ) {
            [PSCustomObject]@{
                Cuix = $CuixName
                Node = $node.Name
                Name = if ($node.Attributes["Name"]) { $node.Attributes["Name"].Value } else { "" }
                UID  = if ($node.Attributes["UID"]) { $node.Attributes["UID"].Value } else { "" }
                Parent = if ($node.ParentNode) { $node.ParentNode.Name } else { "" }
            }
        }
    }

    return $interesting
}

function Get-MacroReport {
    param(
        [System.Xml.XmlDocument]$Xml,
        [string]$CuixName
    )

    $macros = $Xml.SelectNodes("//MenuMacro")
    foreach ($macro in $macros) {
        $macroBody = $macro.SelectSingleNode("./Macro")
        $nameNode = $macroBody.SelectSingleNode("./Name")
        $commandNode = $macroBody.SelectSingleNode("./Command")
        $helpNode = $macroBody.SelectSingleNode("./HelpString")

        [PSCustomObject]@{
            Cuix = $CuixName
            UID = if ($macro.Attributes["UID"]) { $macro.Attributes["UID"].Value } else { "" }
            Name = if ($nameNode) { $nameNode.InnerText } else { "" }
            Command = if ($commandNode) { $commandNode.InnerText } else { "" }
            Help = if ($helpNode) { $helpNode.InnerText } else { "" }
        }
    }
}

$script:ResolvedLogPath = Get-LogPath -RequestedPath $LogPath
Write-Log "Inspecting NANOWATER ribbon sources."
Write-Log "ModuleRoot = $ModuleRoot"
Write-Log "LogPath = $script:ResolvedLogPath"

$supportRoot = Join-Path $ModuleRoot "Support\WATER"
if (-not (Test-Path -LiteralPath $supportRoot)) {
    throw "Support folder not found: $supportRoot"
}

$reports = @()
$macroReports = @()

foreach ($cuixName in $CuixNames) {
    $cuixPath = Join-Path $supportRoot $cuixName
    if (-not (Test-Path -LiteralPath $cuixPath)) {
        Write-Log "Skipped missing file: $cuixPath"
        continue
    }

    Write-Log "Opening $cuixPath"
    $xml = Open-CuixXml -CuixPath $cuixPath
    $reports += Get-ElementReport -Xml $xml -CuixName $cuixName
    $macroReports += Get-MacroReport -Xml $xml -CuixName $cuixName
}

Write-Log "===== Interesting UI nodes ====="
$reports |
    Sort-Object Cuix, Node, Name, UID |
    Format-Table -AutoSize |
    Out-String -Width 4096 |
    ForEach-Object { Write-Log $_.TrimEnd() }

Write-Log "===== Commands summary ====="
$macroReports |
    Sort-Object Cuix, UID |
    Select-Object Cuix, UID, Name, Command |
    Format-Table -Wrap -AutoSize |
    Out-String -Width 4096 |
    ForEach-Object { Write-Log $_.TrimEnd() }

Write-Log "Inspection completed."
