param(
    [string]$ModuleRoot = "C:\Program Files\CSoft\Model Studio CS\NANOWATER",
    [string]$ButtonText = "DMTX",
    [string]$MacroName = "Draw Pipeline",
    [string]$CommandString = "^C^C_pipe_draw_pipeline",
    [string]$SmallImage = "PipeDrawPipeline.png",
    [string]$LargeImage = "MS_PIPE32.png",
    [switch]$AddRibbonTab,
    [switch]$DryRun,
    [switch]$SkipMsMain
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if (-not $PSBoundParameters.ContainsKey("AddRibbonTab")) {
    $AddRibbonTab = $true
}

function Write-Info {
    param([string]$Message)
    Write-Host ("[{0}] {1}" -f (Get-Date -Format "HH:mm:ss"), $Message)
}

function New-UnicodeString {
    param([int[]]$CodePoints)
    return -join ($CodePoints | ForEach-Object { [char]$_ })
}

function New-Uid {
    param([string]$Prefix)
    return "{0}_{1}" -f $Prefix, ([guid]::NewGuid().ToString("N").Substring(0, 10).ToUpperInvariant())
}

function New-XmlElement {
    param(
        [xml]$Document,
        [string]$Name,
        [hashtable]$Attributes
    )

    $element = $Document.CreateElement($Name)
    if ($Attributes) {
        foreach ($key in $Attributes.Keys) {
            $attribute = $Document.CreateAttribute($key)
            $attribute.Value = [string]$Attributes[$key]
            [void]$element.Attributes.Append($attribute)
        }
    }

    return $element
}

function Add-ModifiedRev {
    param(
        [xml]$Document,
        [System.Xml.XmlElement]$Parent,
        [string]$MajorVersion = "24",
        [string]$MinorVersion = "1",
        [string]$UserVersion = "1"
    )

    $node = New-XmlElement -Document $Document -Name "ModifiedRev" -Attributes @{
        MajorVersion = $MajorVersion
        MinorVersion = $MinorVersion
        UserVersion = $UserVersion
    }
    [void]$Parent.AppendChild($node)
}

function Add-TextElement {
    param(
        [xml]$Document,
        [System.Xml.XmlElement]$Parent,
        [string]$Name,
        [string]$Text,
        [hashtable]$Attributes
    )

    $node = New-XmlElement -Document $Document -Name $Name -Attributes $Attributes
    if ($null -ne $Text) {
        $node.InnerText = $Text
    }
    [void]$Parent.AppendChild($node)
    return $node
}

function Load-CuixToTemp {
    param([string]$CuixPath)

    Add-Type -AssemblyName System.IO.Compression.FileSystem

    $tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("dtmxtest_cuix_" + [guid]::NewGuid().ToString("N"))
    [System.IO.Directory]::CreateDirectory($tempRoot) | Out-Null
    [System.IO.Compression.ZipFile]::ExtractToDirectory($CuixPath, $tempRoot)
    return $tempRoot
}

function Load-XmlDocument {
    param([string]$Path)

    $document = New-Object System.Xml.XmlDocument
    $document.PreserveWhitespace = $true
    $document.Load($Path)
    return $document
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

function Add-MenuMacroIfMissing {
    param(
        [xml]$Document,
        [string]$MacroId,
        [string]$MacroName,
        [string]$CommandString,
        [string]$SmallImage,
        [string]$LargeImage
    )

    $existing = $Document.SelectSingleNode("//MenuMacro[@UID='$MacroId']")
    if ($existing) {
        return $false
    }

    $macroGroup = $Document.SelectSingleNode("//MacroGroup")
    if (-not $macroGroup) {
        throw "MacroGroup node not found."
    }

    $menuMacro = New-XmlElement -Document $Document -Name "MenuMacro" -Attributes @{ UID = $MacroId }
    $macro = New-XmlElement -Document $Document -Name "Macro" -Attributes @{ type = "Any" }

    $revision = New-XmlElement -Document $Document -Name "Revision" -Attributes @{
        MajorVersion = "24"
        MinorVersion = "1"
        UserVersion = "1"
    }
    [void]$macro.AppendChild($revision)
    Add-ModifiedRev -Document $Document -Parent $macro
    Add-TextElement -Document $Document -Parent $macro -Name "Name" -Text $MacroName -Attributes @{
        xlate = "true"
        UID = (New-Uid "XLS_DTMX")
    } | Out-Null
    Add-TextElement -Document $Document -Parent $macro -Name "Command" -Text $CommandString -Attributes @{} | Out-Null
    Add-TextElement -Document $Document -Parent $macro -Name "HelpString" -Text "Runs pipe_draw_pipeline" -Attributes @{
        xlate = "true"
        UID = (New-Uid "XLS_DTMX")
    } | Out-Null
    Add-TextElement -Document $Document -Parent $macro -Name "SmallImage" -Text $null -Attributes @{ Name = $SmallImage } | Out-Null
    Add-TextElement -Document $Document -Parent $macro -Name "LargeImage" -Text $null -Attributes @{ Name = $LargeImage } | Out-Null

    [void]$menuMacro.AppendChild($macro)
    [void]$macroGroup.AppendChild($menuMacro)
    return $true
}

function Add-ToolbarButtonIfMissing {
    param(
        [xml]$Document,
        [string]$ToolbarAlias,
        [string]$ButtonText,
        [string]$MacroId
    )

    $toolbar = $Document.SelectSingleNode("//Toolbar[Alias='$ToolbarAlias']")
    if (-not $toolbar) {
        throw "Toolbar alias '$ToolbarAlias' not found."
    }

    $existing = $toolbar.SelectSingleNode(".//ToolbarButton[MenuItem/MacroRef/@MenuMacroID='$MacroId']")
    if ($existing) {
        return $false
    }

    $button = New-XmlElement -Document $Document -Name "ToolbarButton" -Attributes @{
        IsSeparator = "false"
        UID = (New-Uid "TBBU_DTMX")
    }
    Add-ModifiedRev -Document $Document -Parent $button
    Add-TextElement -Document $Document -Parent $button -Name "Name" -Text $ButtonText -Attributes @{
        xlate = "true"
        UID = (New-Uid "XLS_DTMX")
    } | Out-Null

    $menuItem = New-XmlElement -Document $Document -Name "MenuItem" -Attributes @{}
    $macroRef = New-XmlElement -Document $Document -Name "MacroRef" -Attributes @{ MenuMacroID = $MacroId }
    [void]$menuItem.AppendChild($macroRef)
    [void]$button.AppendChild($menuItem)
    [void]$toolbar.AppendChild($button)
    return $true
}

function Add-RibbonButtonToSplitIfMissing {
    param(
        [xml]$Document,
        [string]$SplitText,
        [string]$ButtonText,
        [string]$MacroId
    )

    $split = $Document.SelectSingleNode("//RibbonSplitButton[@Text='$SplitText']")
    if (-not $split) {
        throw "RibbonSplitButton '$SplitText' not found."
    }

    $existing = $split.SelectSingleNode(".//RibbonCommandButton[@MenuMacroID='$MacroId']")
    if ($existing) {
        return $false
    }

    $button = New-XmlElement -Document $Document -Name "RibbonCommandButton" -Attributes @{
        UID = (New-Uid "RBNU_DTMX")
        Id = "AcRibbonCommandButton"
        Text = $ButtonText
        ButtonStyle = "LargeWithText"
        MenuMacroID = $MacroId
        KeyTip = ""
    }
    Add-TextElement -Document $Document -Parent $button -Name "TooltipTitle" -Text $ButtonText -Attributes @{
        xlate = "true"
        UID = (New-Uid "XLS_DTMX")
    } | Out-Null
    Add-ModifiedRev -Document $Document -Parent $button
    [void]$split.AppendChild($button)
    return $true
}

function Add-RibbonTabIfMissing {
    param(
        [xml]$Document,
        [string]$TabText,
        [string]$ButtonText,
        [string]$MacroId
    )

    $existingTab = $Document.SelectSingleNode("//RibbonTabSource[@Text='$TabText']")
    if ($existingTab) {
        return $false
    }

    $panelCollection = $Document.SelectSingleNode("//RibbonPanelSourceCollection")
    $tabCollection = $Document.SelectSingleNode("//RibbonTabSourceCollection")
    if (-not $panelCollection -or -not $tabCollection) {
        throw "Ribbon collections not found."
    }

    $panelId = New-Uid "RBNU_DTMX_PANEL"
    $panel = New-XmlElement -Document $Document -Name "RibbonPanelSource" -Attributes @{
        UID = $panelId
        Text = $TabText
        HiddenInEditor = "false"
    }
    Add-ModifiedRev -Document $Document -Parent $panel
    Add-TextElement -Document $Document -Parent $panel -Name "Name" -Text $TabText -Attributes @{
        xlate = "true"
        UID = (New-Uid "XLS_DTMX")
    } | Out-Null

    $row = New-XmlElement -Document $Document -Name "RibbonRow" -Attributes @{ UID = (New-Uid "RBNU_DTMX_ROW") }
    Add-ModifiedRev -Document $Document -Parent $row
    $rowPanel = New-XmlElement -Document $Document -Name "RibbonRowPanel" -Attributes @{
        UID = (New-Uid "RBNU_DTMX_RP")
        ResizeStyle = "None"
        ResizePriority = "100"
        TopJustify = "True"
    }
    Add-ModifiedRev -Document $Document -Parent $rowPanel
    $innerRow = New-XmlElement -Document $Document -Name "RibbonRow" -Attributes @{ UID = (New-Uid "RBNU_DTMX_INROW") }
    Add-ModifiedRev -Document $Document -Parent $innerRow
    $button = New-XmlElement -Document $Document -Name "RibbonCommandButton" -Attributes @{
        UID = (New-Uid "RBNU_DTMX_BTN")
        Id = "AcRibbonCommandButton"
        Text = $ButtonText
        ButtonStyle = "LargeWithText"
        MenuMacroID = $MacroId
        KeyTip = ""
    }
    Add-TextElement -Document $Document -Parent $button -Name "TooltipTitle" -Text $ButtonText -Attributes @{
        xlate = "true"
        UID = (New-Uid "XLS_DTMX")
    } | Out-Null
    Add-ModifiedRev -Document $Document -Parent $button

    [void]$innerRow.AppendChild($button)
    [void]$rowPanel.AppendChild($innerRow)
    [void]$row.AppendChild($rowPanel)
    [void]$panel.AppendChild($row)
    [void]$panelCollection.AppendChild($panel)

    $tab = New-XmlElement -Document $Document -Name "RibbonTabSource" -Attributes @{
        Text = $TabText
        UID = (New-Uid "RBNU_DTMX_TAB")
    }
    Add-ModifiedRev -Document $Document -Parent $tab
    Add-TextElement -Document $Document -Parent $tab -Name "Name" -Text $TabText -Attributes @{
        xlate = "true"
        UID = (New-Uid "XLS_DTMX")
    } | Out-Null
    $panelRef = New-XmlElement -Document $Document -Name "RibbonPanelSourceReference" -Attributes @{
        UID = (New-Uid "RBNU_DTMX_PREF")
        PanelId = $panelId
        ResizeStyle = "Default"
    }
    Add-ModifiedRev -Document $Document -Parent $panelRef
    [void]$tab.AppendChild($panelRef)
    [void]$tabCollection.AppendChild($tab)

    return $true
}

function Save-XmlUtf8Bom {
    param(
        [xml]$Document,
        [string]$Path
    )

    $settings = New-Object System.Xml.XmlWriterSettings
    $settings.Indent = $true
    $settings.Encoding = New-Object System.Text.UTF8Encoding($true)
    $writer = [System.Xml.XmlWriter]::Create($Path, $settings)
    try {
        $Document.Save($writer)
    }
    finally {
        $writer.Dispose()
    }
}

$supportRoot = Join-Path $ModuleRoot "Support\WATER"
$msMainPath = Join-Path $supportRoot "MSMAIN.cuix"
$waterPath = Join-Path $supportRoot "water.cuix"
$backupRoot = Join-Path $supportRoot "DTMXtest-backup"
$miscText = New-UnicodeString -CodePoints @(0x0420,0x0430,0x0437,0x043D,0x043E,0x0435)
$waterRibbonText = New-UnicodeString -CodePoints @(0x0412,0x043E,0x0434,0x043E,0x0441,0x043D,0x0430,0x0431,0x0436,0x0435,0x043D,0x0438,0x0435,0x0020,0x0438,0x0020,0x043A,0x0430,0x043D,0x0430,0x043B,0x0438,0x0437,0x0430,0x0446,0x0438,0x044F)

if (-not (Test-Path -LiteralPath $msMainPath)) {
    throw "MSMAIN.cuix not found at $msMainPath"
}
if (-not (Test-Path -LiteralPath $waterPath)) {
    throw "water.cuix not found at $waterPath"
}

$msMainMacroId = "DTMX_MS_OTHER_BUTTON"
$waterMacroId = "DTMX_WATER_BUTTON"
$waterBuiltInMacroId = "pipe_draw_pipeline"

$summary = New-Object System.Collections.Generic.List[string]

function Patch-Cuix {
    param(
        [string]$CuixPath,
        [scriptblock]$ApplyChanges
    )

    Write-Info "Preparing $CuixPath"
    $tempRoot = Load-CuixToTemp -CuixPath $CuixPath
    try {
        & $ApplyChanges $tempRoot
        if ($DryRun) {
            Write-Info "DryRun: no write for $CuixPath"
            return
        }

        $backupPath = Backup-File -FilePath $CuixPath -BackupRoot $backupRoot
        Write-Info "Backup created: $backupPath"
        Save-TempToCuix -TempRoot $tempRoot -DestinationCuixPath $CuixPath
        Write-Info "Updated: $CuixPath"
    }
    finally {
        if (Test-Path -LiteralPath $tempRoot) {
            Remove-Item -LiteralPath $tempRoot -Recurse -Force
        }
    }
}

if (-not $SkipMsMain) {
    Patch-Cuix -CuixPath $msMainPath -ApplyChanges {
        param($tempRoot)

        $menuGroupPath = Join-Path $tempRoot "MenuGroup.cui"
        $toolbarRootPath = Join-Path $tempRoot "ToolbarRoot.cui"

        $menuGroup = Load-XmlDocument -Path $menuGroupPath
        $toolbarRoot = Load-XmlDocument -Path $toolbarRootPath

        if (Add-MenuMacroIfMissing -Document $menuGroup -MacroId $msMainMacroId -MacroName $MacroName -CommandString $CommandString -SmallImage $SmallImage -LargeImage $LargeImage) {
            $summary.Add("MSMAIN: added menu macro $msMainMacroId")
        }
        else {
            $summary.Add("MSMAIN: menu macro already exists")
        }

        if (Add-ToolbarButtonIfMissing -Document $toolbarRoot -ToolbarAlias "MS_OTHER" -ButtonText $ButtonText -MacroId $msMainMacroId) {
            $summary.Add("MSMAIN: added toolbar button to MS_OTHER")
        }
        else {
            $summary.Add("MSMAIN: toolbar button already exists in MS_OTHER")
        }

        Save-XmlUtf8Bom -Document $menuGroup -Path $menuGroupPath
        Save-XmlUtf8Bom -Document $toolbarRoot -Path $toolbarRootPath
    }
}

Patch-Cuix -CuixPath $waterPath -ApplyChanges {
    param($tempRoot)

    $menuGroupPath = Join-Path $tempRoot "MenuGroup.cui"
    $ribbonRootPath = Join-Path $tempRoot "RibbonRoot.cui"

    $menuGroup = Load-XmlDocument -Path $menuGroupPath
    $ribbonRoot = Load-XmlDocument -Path $ribbonRootPath

    if (Add-MenuMacroIfMissing -Document $menuGroup -MacroId $waterMacroId -MacroName $MacroName -CommandString $CommandString -SmallImage $SmallImage -LargeImage $LargeImage) {
        $summary.Add("water: added menu macro $waterMacroId")
    }
    else {
        $summary.Add("water: menu macro already exists")
    }

    if (Add-RibbonButtonToSplitIfMissing -Document $ribbonRoot -SplitText $miscText -ButtonText $ButtonText -MacroId $waterBuiltInMacroId) {
        $summary.Add("water: added ribbon button to split 'Р Р°Р·РЅРѕРµ'")
    }
    else {
        $summary.Add("water: ribbon button already exists in split 'Р Р°Р·РЅРѕРµ'")
    }

    if ($AddRibbonTab) {
        if (Add-RibbonTabIfMissing -Document $ribbonRoot -TabText "DTMXtest" -ButtonText $ButtonText -MacroId $waterBuiltInMacroId) {
            $summary.Add("water: added ribbon tab DTMXtest")
        }
        else {
            $summary.Add("water: ribbon tab DTMXtest already exists")
        }
    }

    Save-XmlUtf8Bom -Document $menuGroup -Path $menuGroupPath
    Save-XmlUtf8Bom -Document $ribbonRoot -Path $ribbonRootPath
}

Write-Info "Patch summary:"
$summary | ForEach-Object { Write-Info " - $_" }

if ($DryRun) {
    Write-Info "DryRun completed. No files were changed."
}
else {
    Write-Info "Patch completed. Restart Model Studio CS WATER to verify ribbon changes."
}

