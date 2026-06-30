param(
    [string]$ModuleRoot = "C:\Program Files\CSoft\Model Studio CS\NANOWATER",
    [string]$ButtonText = "DMTX",
    [string]$MacroName = "Draw Pipeline",
    [string]$CommandString = "^C^C_pipe_draw_pipeline",
    [string]$SmallImage = "PipeDrawPipeline.png",
    [string]$LargeImage = "MS_PIPE32.png",
    [switch]$AddRibbonTab,
    [switch]$AddSplitButton,
    [switch]$AddPipelineButton,
    [switch]$DryRun,
    [switch]$SkipMsMain
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if (-not $PSBoundParameters.ContainsKey("AddRibbonTab")) {
    $AddRibbonTab = $true
}
if (-not $PSBoundParameters.ContainsKey("AddSplitButton")) {
    $AddSplitButton = $false
}
if (-not $PSBoundParameters.ContainsKey("AddPipelineButton")) {
    $AddPipelineButton = $false
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

    # IMPORTANT: ZipFile::CreateFromDirectory uses backslash in entry names on Windows
    # (_rels\.rels instead of _rels/.rels), which breaks nanoCAD icon loading.
    # Instead, we update the existing ZIP in-place, preserving original entry names.
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    Add-Type -AssemblyName System.IO.Compression

    $zipMode = [System.IO.Compression.ZipArchiveMode]::Update
    $archive = [System.IO.Compression.ZipFile]::Open($DestinationCuixPath, $zipMode)
    try {
        # Build a map of temp files: relative path (with forward slashes) -> full path
        $tempFiles = [System.Collections.Generic.Dictionary[string,string]]::new([System.StringComparer]::OrdinalIgnoreCase)
        Get-ChildItem $TempRoot -Recurse -File | ForEach-Object {
            $rel = $_.FullName.Substring($TempRoot.Length).TrimStart('\', '/')
            $rel = $rel.Replace('\', '/')
            $tempFiles[$rel] = $_.FullName
        }

        # Update or add entries
        $existingEntries = @($archive.Entries)
        foreach ($entry in $existingEntries) {
            $name = $entry.FullName
            if ($tempFiles.ContainsKey($name)) {
                # Overwrite with modified content
                $entryStream = $entry.Open()
                $entryStream.SetLength(0)
                $fileBytes = [System.IO.File]::ReadAllBytes($tempFiles[$name])
                $entryStream.Write($fileBytes, 0, $fileBytes.Length)
                $entryStream.Dispose()
                $tempFiles.Remove($name) | Out-Null
            }
        }

        # Add brand-new files (not in original ZIP)
        foreach ($rel in @($tempFiles.Keys)) {
            $newEntry = $archive.CreateEntry($rel)
            $entryStream = $newEntry.Open()
            $fileBytes = [System.IO.File]::ReadAllBytes($tempFiles[$rel])
            $entryStream.Write($fileBytes, 0, $fileBytes.Length)
            $entryStream.Dispose()
        }
    }
    finally {
        $archive.Dispose()
    }
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

function Set-MenuMacroValues {
    param(
        [xml]$Document,
        [string]$MacroId,
        [string]$MacroName,
        [string]$CommandString,
        [string]$SmallImage,
        [string]$LargeImage,
        [string]$HelpString = $null
    )

    $menuMacro = $Document.SelectSingleNode("//MenuMacro[@UID='$MacroId']")
    if (-not $menuMacro) {
        return $false
    }

    $macro = $menuMacro.SelectSingleNode("Macro")
    if (-not $macro) {
        return $false
    }

    $nameNode = $macro.SelectSingleNode("Name")
    if ($nameNode) { $nameNode.InnerText = $MacroName }

    $cmdNode = $macro.SelectSingleNode("Command")
    if ($cmdNode) { $cmdNode.InnerText = $CommandString }

    if ($HelpString) {
        $helpNode = $macro.SelectSingleNode("HelpString")
        if ($helpNode) { $helpNode.InnerText = $HelpString }
    }

    $smallNode = $macro.SelectSingleNode("SmallImage")
    if ($smallNode -and $smallNode.Attributes["Name"]) { $smallNode.Attributes["Name"].Value = $SmallImage }

    $largeNode = $macro.SelectSingleNode("LargeImage")
    if ($largeNode -and $largeNode.Attributes["Name"]) { $largeNode.Attributes["Name"].Value = $LargeImage }

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

function Add-RibbonButtonToPipelineRowIfMissing {
    param(
        [xml]$Document,
        [string]$ButtonText,
        [string]$MacroId
    )

    $row = $Document.SelectSingleNode("//RibbonPanelSource[@Text='Трубопровод']/RibbonRow/RibbonRowPanel[RibbonRow/RibbonSplitButton[@CommandID='pipe_draw_pipeline']]/RibbonRow")
    if (-not $row) {
        throw "Pipeline ribbon row not found."
    }

    $existing = $row.SelectSingleNode("RibbonCommandButton[@Text='$ButtonText' and @MenuMacroID='$MacroId']")
    if ($existing) {
        return $false
    }

    $button = New-XmlElement -Document $Document -Name "RibbonCommandButton" -Attributes @{
        UID = (New-Uid "RBNU_DTMX_STANDALONE")
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
    [void]$row.AppendChild($button)
    return $true
}

function Remove-RibbonButtonFromSplitIfPresent {
    param(
        [xml]$Document,
        [string]$SplitText,
        [string]$ButtonText,
        [string]$MacroId
    )

    $split = $Document.SelectSingleNode("//RibbonSplitButton[@Text='$SplitText']")
    if (-not $split) {
        return $false
    }

    $button = $split.SelectSingleNode(".//RibbonCommandButton[@Text='$ButtonText' and @MenuMacroID='$MacroId']")
    if (-not $button) {
        return $false
    }

    [void]$split.RemoveChild($button)
    return $true
}

function Remove-RibbonButtonFromPipelineRowIfPresent {
    param(
        [xml]$Document,
        [string]$ButtonText,
        [string]$MacroId
    )

    $row = $Document.SelectSingleNode("//RibbonPanelSource[@Text='Трубопровод']/RibbonRow/RibbonRowPanel[RibbonRow/RibbonSplitButton[@CommandID='pipe_draw_pipeline']]/RibbonRow")
    if (-not $row) {
        return $false
    }

    $button = $row.SelectSingleNode("RibbonCommandButton[@Text='$ButtonText' and @MenuMacroID='$MacroId']")
    if (-not $button) {
        return $false
    }

    [void]$row.RemoveChild($button)
    return $true
}

function Add-RibbonCommandButtonIfMissing {
    param(
        [xml]$Document,
        [System.Xml.XmlElement]$ParentRow,
        [string]$ButtonText,
        [string]$MacroId
    )

    $existing = $ParentRow.SelectSingleNode("RibbonCommandButton[@MenuMacroID='$MacroId']")
    if ($existing) {
        return $false
    }

    $button = New-XmlElement -Document $Document -Name "RibbonCommandButton" -Attributes @{
        UID = (New-Uid "RBNU_DTMX_CMD")
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
    [void]$ParentRow.AppendChild($button)
    return $true
}

function Set-RibbonCommandButtonText {
    param(
        [xml]$Document,
        [System.Xml.XmlElement]$ParentRow,
        [string]$MacroId,
        [string]$ButtonText
    )

    $button = $ParentRow.SelectSingleNode("RibbonCommandButton[@MenuMacroID='$MacroId']")
    if (-not $button) {
        return $false
    }

    if ($button.Attributes["Text"]) {
        $button.Attributes["Text"].Value = $ButtonText
    }

    $tooltip = $button.SelectSingleNode("TooltipTitle")
    if ($tooltip) {
        $tooltip.InnerText = $ButtonText
    }
    return $true
}

function Ensure-DtmxTabButtons {
    param(
        [xml]$Document,
        [object[]]$Buttons
    )

    $tab = $Document.SelectSingleNode("//RibbonTabSource[@Text='DTMXtest']")
    if (-not $tab) {
        throw "Ribbon tab 'DTMXtest' not found. Create tab first."
    }

    $panelId = $null
    $panelRef = $tab.SelectSingleNode("RibbonPanelSourceReference[1]")
    if ($panelRef -and $panelRef.Attributes["PanelId"]) {
        $panelId = $panelRef.Attributes["PanelId"].Value
    }

    $panel = $null
    if ($panelId) {
        $panel = $Document.SelectSingleNode("//RibbonPanelSource[@UID='$panelId']")
    }
    if (-not $panel) {
        $panel = $Document.SelectSingleNode("//RibbonPanelSource[@Text='DTMXtest']")
    }
    if (-not $panel) {
        throw "Ribbon panel for tab 'DTMXtest' not found."
    }

    $row = $panel.SelectSingleNode("RibbonRow")
    if (-not $row) {
        $row = New-XmlElement -Document $Document -Name "RibbonRow" -Attributes @{ UID = (New-Uid "RBNU_DTMX_ROW") }
        Add-ModifiedRev -Document $Document -Parent $row
        [void]$panel.AppendChild($row)
    }

    $rowPanel = $row.SelectSingleNode("RibbonRowPanel")
    if (-not $rowPanel) {
        $rowPanel = New-XmlElement -Document $Document -Name "RibbonRowPanel" -Attributes @{
            UID = (New-Uid "RBNU_DTMX_RP")
            ResizeStyle = "None"
            ResizePriority = "100"
            TopJustify = "True"
        }
        Add-ModifiedRev -Document $Document -Parent $rowPanel
        [void]$row.AppendChild($rowPanel)
    }

    $innerRow = $rowPanel.SelectSingleNode("RibbonRow")
    if (-not $innerRow) {
        $innerRow = New-XmlElement -Document $Document -Name "RibbonRow" -Attributes @{ UID = (New-Uid "RBNU_DTMX_INROW") }
        Add-ModifiedRev -Document $Document -Parent $innerRow
        [void]$rowPanel.AppendChild($innerRow)
    }

    $added = New-Object System.Collections.Generic.List[string]
    $updated = New-Object System.Collections.Generic.List[string]
    foreach ($buttonDef in $Buttons) {
        if (Add-RibbonCommandButtonIfMissing -Document $Document -ParentRow $innerRow -ButtonText $buttonDef.ButtonText -MacroId $buttonDef.MacroId) {
            $added.Add([string]$buttonDef.ButtonText)
        }
        elseif (Set-RibbonCommandButtonText -Document $Document -ParentRow $innerRow -MacroId $buttonDef.MacroId -ButtonText $buttonDef.ButtonText) {
            $updated.Add([string]$buttonDef.ButtonText)
        }
    }
    return @{
        Added = $added.ToArray()
        Updated = $updated.ToArray()
    }
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

function Save-XmlUtf8NoBom {
    param(
        [xml]$Document,
        [string]$Path
    )

    $settings = New-Object System.Xml.XmlWriterSettings
    $settings.Indent = $true
    $settings.Encoding = New-Object System.Text.UTF8Encoding($false)
    $writer = [System.Xml.XmlWriter]::Create($Path, $settings)
    try {
        $Document.Save($writer)
    }
    finally {
        $writer.Dispose()
    }
}

function Ensure-ImageRelationships {
    param(
        [xml]$Document,
        [string[]]$ImageNames
    )

    $ns = "http://schemas.openxmlformats.org/package/2006/relationships"
    $nsmgr = New-Object System.Xml.XmlNamespaceManager($Document.NameTable)
    $nsmgr.AddNamespace("rel", $ns)

    $root = $Document.SelectSingleNode("/rel:Relationships", $nsmgr)
    if (-not $root) {
        throw "Relationships root node not found."
    }

    $added = New-Object System.Collections.Generic.List[string]
    foreach ($imageName in $ImageNames) {
        $target = "/$imageName"
        $existing = $Document.SelectSingleNode("/rel:Relationships/rel:Relationship[@Type='Image' and @Target='$target']", $nsmgr)
        if ($existing) {
            continue
        }

        $relationship = $Document.CreateElement("Relationship", $ns)
        $typeAttr = $Document.CreateAttribute("Type")
        $typeAttr.Value = "Image"
        [void]$relationship.Attributes.Append($typeAttr)

        $targetAttr = $Document.CreateAttribute("Target")
        $targetAttr.Value = $target
        [void]$relationship.Attributes.Append($targetAttr)

        $idAttr = $Document.CreateAttribute("Id")
        $idAttr.Value = "R" + [guid]::NewGuid().ToString("N")
        [void]$relationship.Attributes.Append($idAttr)

        [void]$root.AppendChild($relationship)
        $added.Add($imageName)
    }

    return $added.ToArray()
}

function Ensure-PngContentTypeOverrides {
    param(
        [xml]$Document,
        [string[]]$ImageNames
    )

    $ns = "http://schemas.openxmlformats.org/package/2006/content-types"
    $nsmgr = New-Object System.Xml.XmlNamespaceManager($Document.NameTable)
    $nsmgr.AddNamespace("ct", $ns)

    $root = $Document.SelectSingleNode("/ct:Types", $nsmgr)
    if (-not $root) {
        throw "Content types root node not found."
    }

    $added = New-Object System.Collections.Generic.List[string]
    foreach ($imageName in $ImageNames) {
        $partName = "/$imageName"
        $existing = $Document.SelectSingleNode("/ct:Types/ct:Override[@PartName='$partName']", $nsmgr)
        if ($existing) {
            if ($existing.Attributes["ContentType"] -and $existing.Attributes["ContentType"].Value -ne "image/png") {
                $existing.Attributes["ContentType"].Value = "image/png"
                $added.Add("$imageName (updated)")
            }
            continue
        }

        $override = $Document.CreateElement("Override", $ns)

        $partAttr = $Document.CreateAttribute("PartName")
        $partAttr.Value = $partName
        [void]$override.Attributes.Append($partAttr)

        $typeAttr = $Document.CreateAttribute("ContentType")
        $typeAttr.Value = "image/png"
        [void]$override.Attributes.Append($typeAttr)

        [void]$root.AppendChild($override)
        $added.Add($imageName)
    }

    return $added.ToArray()
}

function Ensure-MenuPackageParts {
    param(
        [xml]$Document,
        [string[]]$PartNames
    )

    $root = $Document.SelectSingleNode("/MenuPackageParts")
    if (-not $root) {
        throw "MenuPackageParts root node not found."
    }

    $added = New-Object System.Collections.Generic.List[string]
    $timestamp = [DateTimeOffset]::Now.ToString("yyyy-MM-ddTHH:mm:ss.fffffffzzz")

    foreach ($partName in $PartNames) {
        $packagePartName = "/" + $partName
        $existing = $root.SelectSingleNode("PartData[@PartData_Name='$packagePartName']")
        if ($existing) {
            if ($existing.Attributes["PartData_Modified"]) {
                $existing.Attributes["PartData_Modified"].Value = $timestamp
            }
            continue
        }

        $partData = $Document.CreateElement("PartData")
        $nameAttr = $Document.CreateAttribute("PartData_Name")
        $nameAttr.Value = $packagePartName
        [void]$partData.Attributes.Append($nameAttr)

        $modifiedAttr = $Document.CreateAttribute("PartData_Modified")
        $modifiedAttr.Value = $timestamp
        [void]$partData.Attributes.Append($modifiedAttr)

        [void]$root.AppendChild($partData)
        $added.Add($partName)
    }

    return $added.ToArray()
}

function Add-OrUpdate-RibbonCmd {
    param(
        [xml]$Document,
        [string]$CommandId,
        [string]$CommandString,
        [string]$Resolved = "1"
    )

    $root = $Document.SelectSingleNode("/Ribboncmds")
    if (-not $root) {
        throw "Ribboncmds root node not found."
    }

    $node = $Document.SelectSingleNode("//Ribboncmd[@UID='$CommandId']")
    $changed = $false
    if (-not $node) {
        $node = New-XmlElement -Document $Document -Name "Ribboncmd" -Attributes @{
            UID = $CommandId
            resolved = $Resolved
        }
        Add-TextElement -Document $Document -Parent $node -Name "Command" -Text $CommandString -Attributes @{} | Out-Null
        [void]$root.AppendChild($node)
        return "added"
    }

    if (-not $node.Attributes["resolved"]) {
        $attr = $Document.CreateAttribute("resolved")
        $attr.Value = $Resolved
        [void]$node.Attributes.Append($attr)
        $changed = $true
    }
    elseif ($node.Attributes["resolved"].Value -ne $Resolved) {
        $node.Attributes["resolved"].Value = $Resolved
        $changed = $true
    }

    $commandNode = $node.SelectSingleNode("Command")
    if (-not $commandNode) {
        Add-TextElement -Document $Document -Parent $node -Name "Command" -Text $CommandString -Attributes @{} | Out-Null
        $changed = $true
    }
    elseif ($commandNode.InnerText -ne $CommandString) {
        $commandNode.InnerText = $CommandString
        $changed = $true
    }

    if ($changed) {
        return "updated"
    }

    return "unchanged"
}

function Set-RibbonButtonResolved {
    param(
        [xml]$Document,
        [string]$MacroId
    )

    $changed = $false
    $buttons = $Document.SelectNodes("//RibbonCommandButton[@MenuMacroID='$MacroId']")
    foreach ($button in $buttons) {
        if (-not $button.Attributes["resolved"]) {
            $attr = $Document.CreateAttribute("resolved")
            $attr.Value = "1"
            [void]$button.Attributes.Append($attr)
            $changed = $true
        }
        elseif ($button.Attributes["resolved"].Value -ne "1") {
            $button.Attributes["resolved"].Value = "1"
            $changed = $true
        }
    }

    return $changed
}

function Ensure-XmlChild {
    param(
        [xml]$Document,
        [System.Xml.XmlElement]$Parent,
        [string]$Name
    )

    $node = $Parent.SelectSingleNode($Name)
    if ($node) { return $node }
    $node = $Document.CreateElement($Name)
    [void]$Parent.AppendChild($node)
    return $node
}

function Ensure-NconfigModule {
    param(
        [xml]$Document,
        [string]$ModuleName
    )

    $root = $Document.SelectSingleNode("/Application")
    if (-not $root) {
        throw "Application root not found in nconfig."
    }

    $modules = Ensure-XmlChild -Document $Document -Parent $root -Name "Modules"
    $existing = $modules.SelectSingleNode("Module[@name='$ModuleName']")
    if ($existing) {
        return $false
    }

    $module = $Document.CreateElement("Module")
    $attr = $Document.CreateAttribute("name")
    $attr.Value = $ModuleName
    [void]$module.Attributes.Append($attr)
    [void]$modules.AppendChild($module)
    return $true
}

function Ensure-CfgCommandBlocks {
    param(
        [string]$CfgPath,
        [array]$Commands
    )

    $encoding = [System.Text.Encoding]::GetEncoding(1251)
    $text = [System.IO.File]::ReadAllText($CfgPath, $encoding)
    $changed = $false

    foreach ($cmd in $Commands) {
        $header = "[\configman\commands\$($cmd.CommandId)]"
        $blockLines = @(
            $header,
            "weight=i10 |cmdtype=i1",
            "intername=s$($cmd.InterName)",
            "DispName=s$($cmd.DisplayName)",
            "ToolTipText=s$($cmd.DisplayName)",
            "StatusText=s$($cmd.StatusText)"
        )
        $hasBitmapDll = ($cmd -is [hashtable] -and $cmd.ContainsKey("BitmapDll")) -or ($cmd -isnot [hashtable] -and $null -ne $cmd.PSObject.Properties["BitmapDll"])
        $hasIcon = ($cmd -is [hashtable] -and $cmd.ContainsKey("Icon")) -or ($cmd -isnot [hashtable] -and $null -ne $cmd.PSObject.Properties["Icon"])
        if ($hasBitmapDll -and $hasIcon -and $cmd.BitmapDll -and $cmd.Icon) {
            $blockLines += "BitmapDll=s$($cmd.BitmapDll) |Icon=s$($cmd.Icon)"
        }
        $block = $blockLines -join "`r`n"

        $escapedHeader = [regex]::Escape($header)
        $pattern = "(?ms)(^|\r?\n)$escapedHeader\r?\n.*?(?=(\r?\n\[[^\]]+\])|\z)"
        $updated = [regex]::Replace($text, $pattern, "`r`n`r`n$block`r`n", 1)
        if ($updated -ne $text) {
            $text = $updated
            $changed = $true
            continue
        }

        $text += "`r`n`r`n$block`r`n"
        $changed = $true
    }

    if ($changed) {
        [System.IO.File]::WriteAllText($CfgPath, $text, $encoding)
    }

    return $changed
}

$supportRoot = Join-Path $ModuleRoot "Support\WATER"
$moduleBinRoot = Join-Path $ModuleRoot "bin\nanoCAD241"
$waterNconfigPath = Join-Path $ModuleRoot "Settings\WATER.nconfig"
$waterCfgPath = Join-Path $supportRoot "water.cfg"
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
if (-not (Test-Path -LiteralPath $waterCfgPath)) {
    throw "water.cfg not found at $waterCfgPath"
}

$msMainMacroId = "DTMX_MS_OTHER_BUTTON"
$waterMacroId = "DTMX_WATER_BUTTON"
$waterBuiltInMacroId = "pipe_draw_pipeline"
$dtmxNrxFileName = "DtmxNrx45.nrx"
$dtmxNrxSourcePath = "C:\pdf_ingest\DTMXtest\Scripts\DtmxNrx45.nrx"
$dtmxNrxInstalledPath = Join-Path $moduleBinRoot $dtmxNrxFileName
$dtmxMenuResFileName = "DtmxMenuRes.dll"
$dtmxMenuResSourcePath = "C:\pdf_ingest\DTMXtest\DtmxMenuRes\bin\x64\Release\DtmxMenuRes.dll"
$dtmxMenuResInstalledPath = Join-Path $supportRoot $dtmxMenuResFileName
$dtmxCommandButtons = @(
    @{ MacroId = "DTMX_CMD_EDIT";    MacroName = "DTMX Edit";    ButtonText = "Правка";    CommandString = "^C^C_DTMXEDIT";          SmallImage = "MStudioPipelineSettings.png"; LargeImage = "MS_EDITPIPE32.png";     SmallImageSource = "dtmx_edit_16.png";        LargeImageSource = "dtmx_edit_32.png";        HelpString = "Правка параметров" },
    @{ MacroId = "DTMX_CMD_EXPLORE"; MacroName = "DTMX Explore"; ButtonText = "Свойства";  CommandString = "^C^C_DTMXNRX22EXPLORE"; SmallImage = "MStudioInlineSettings.png";   LargeImage = "MS_EDITVALV32.png";     SmallImageSource = "dtmx_properties_16.png";  LargeImageSource = "dtmx_properties_32.png";  HelpString = "Проводник свойств элемента" },
    @{ MacroId = "DTMX_CMD_PATHS";   MacroName = "DTMX Paths";   ButtonText = "Связи";     CommandString = "^C^C_DTMXNRX23PATHS";   SmallImage = "Connector.png";              LargeImage = "MS_PIPE_ROUTE32.png";   SmallImageSource = "dtmx_connections_16.png"; LargeImageSource = "dtmx_connections_32.png"; HelpString = "Маршруты и связи объекта" },
    @{ MacroId = "DTMX_CMD_PING";    MacroName = "DTMX Ping";    ButtonText = "Тест";      CommandString = "^C^C_DTMXPING";         SmallImage = "WarningToUse16.png";         LargeImage = "MS_WARNING32.png";      SmallImageSource = "dtmx_test_16.png";        LargeImageSource = "dtmx_test_32.png";        HelpString = "Диагностика ribbon-кнопки" }
)

$dtmxCfgCommands = @(
    @{ CommandId = "DTMX_CMD_EDIT";    InterName = "DTMXEDIT";         DisplayName = "Правка";    StatusText = "Правка параметров";               BitmapDll = "DtmxMenuRes.dll"; Icon = "DTMX_EDIT" },
    @{ CommandId = "DTMX_CMD_EXPLORE"; InterName = "DTMXNRX22EXPLORE"; DisplayName = "Свойства";  StatusText = "Проводник свойств элемента";      BitmapDll = "DtmxMenuRes.dll"; Icon = "DTMX_EXPLORE" },
    @{ CommandId = "DTMX_CMD_PATHS";   InterName = "DTMXNRX23PATHS";   DisplayName = "Связи";     StatusText = "Маршруты и связи объекта";        BitmapDll = "DtmxMenuRes.dll"; Icon = "DTMX_PATHS" },
    @{ CommandId = "DTMX_CMD_PING";    InterName = "DTMXPING";         DisplayName = "Тест";      StatusText = "Диагностика ribbon-кнопки";       BitmapDll = "DtmxMenuRes.dll"; Icon = "DTMX_PING" }
)

$userConfigRoot = Join-Path $env:APPDATA "Nanosoft\nanoCAD x64 24.1\Config"
$userRibbonCmdsPath = Join-Path $userConfigRoot "RibbonCmds.xml"
$userRibbonTabsPath = Join-Path $userConfigRoot "RibbonTabsAndPanels.xml"
$userDataCacheRoot = "C:\Program Files\Nanosoft\nanoCAD x64 24.1\UserDataCache\Config"
$userDataCacheRibbonCmdsPath = Join-Path $userDataCacheRoot "RibbonCmds.xml"
$userDataCacheRibbonTabsPath = Join-Path $userDataCacheRoot "RibbonTabsAndPanels.xml"

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

function Copy-IconAssetIfNeeded {
    param(
        [string]$SourcePath,
        [string]$DestinationPath
    )

    if (-not (Test-Path -LiteralPath $SourcePath)) {
        throw "Icon asset not found at $SourcePath"
    }

    $srcBytes = [System.IO.File]::ReadAllBytes($SourcePath)
    if (Test-Path -LiteralPath $DestinationPath) {
        $dstBytes = [System.IO.File]::ReadAllBytes($DestinationPath)
        if ($srcBytes.Length -eq $dstBytes.Length) {
            $isSame = $true
            for ($i = 0; $i -lt $srcBytes.Length; $i++) {
                if ($srcBytes[$i] -ne $dstBytes[$i]) {
                    $isSame = $false
                    break
                }
            }
            if ($isSame) {
                return $false
            }
        }
    }

    [System.IO.File]::WriteAllBytes($DestinationPath, $srcBytes)
    return $true
}

if (-not (Test-Path -LiteralPath $dtmxNrxSourcePath)) {
    throw "DTMX NRX source not found at $dtmxNrxSourcePath"
}
if (-not (Test-Path -LiteralPath $dtmxMenuResSourcePath)) {
    throw "DTMX menu resource DLL not found at $dtmxMenuResSourcePath"
}
if (-not (Test-Path -LiteralPath $waterNconfigPath)) {
    throw "WATER.nconfig not found at $waterNconfigPath"
}

if (-not $DryRun) {
    try {
        [System.IO.Directory]::CreateDirectory($moduleBinRoot) | Out-Null
        if (Test-Path -LiteralPath $dtmxNrxInstalledPath) {
            $backupPath = Backup-File -FilePath $dtmxNrxInstalledPath -BackupRoot $backupRoot
            $summary.Add("module: backup $dtmxNrxFileName -> $backupPath")
        }
        Copy-Item -LiteralPath $dtmxNrxSourcePath -Destination $dtmxNrxInstalledPath -Force
        $summary.Add("module: copied $dtmxNrxFileName to $moduleBinRoot")
    }
    catch {
        $summary.Add("module: copy skipped ($($_.Exception.Message))")
    }
}

if (-not $DryRun) {
    try {
        [System.IO.Directory]::CreateDirectory($supportRoot) | Out-Null
        if (Test-Path -LiteralPath $dtmxMenuResInstalledPath) {
            $backupPath = Backup-File -FilePath $dtmxMenuResInstalledPath -BackupRoot $backupRoot
            $summary.Add("module: backup $dtmxMenuResFileName -> $backupPath")
        }
        Copy-Item -LiteralPath $dtmxMenuResSourcePath -Destination $dtmxMenuResInstalledPath -Force
        $summary.Add("module: copied $dtmxMenuResFileName to $supportRoot")
    }
    catch {
        $summary.Add("module: resource DLL copy skipped ($($_.Exception.Message))")
    }
}

$waterNconfig = Load-XmlDocument -Path $waterNconfigPath
if (Ensure-NconfigModule -Document $waterNconfig -ModuleName $dtmxNrxFileName) {
    if (-not $DryRun) {
        $backupPath = Backup-File -FilePath $waterNconfigPath -BackupRoot $backupRoot
        $summary.Add("module: backup WATER.nconfig -> $backupPath")
        Save-XmlUtf8NoBom -Document $waterNconfig -Path $waterNconfigPath
        Write-Info "Updated: $waterNconfigPath"
    }
    $summary.Add("module: added $dtmxNrxFileName to WATER.nconfig")
}
else {
    $summary.Add("module: $dtmxNrxFileName already present in WATER.nconfig")
}

if (-not $DryRun) {
    $backupPath = Backup-File -FilePath $waterCfgPath -BackupRoot $backupRoot
    $summary.Add("module: backup water.cfg -> $backupPath")
    if (Ensure-CfgCommandBlocks -CfgPath $waterCfgPath -Commands $dtmxCfgCommands) {
        $summary.Add("module: added DTMX configman commands to water.cfg")
    }
    else {
        $summary.Add("module: DTMX configman commands already present in water.cfg")
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
    # NOTE: Do NOT modify _rels/.rels, [Content_Types].xml, or Menu_Package_Info.xml.
    # Our DTMX macros reference only existing water images that already have
    # proper relationships and content-type entries in the original CUIX.

    if (Add-MenuMacroIfMissing -Document $menuGroup -MacroId $waterMacroId -MacroName $MacroName -CommandString $CommandString -SmallImage $SmallImage -LargeImage $LargeImage) {
        $summary.Add("water: added menu macro $waterMacroId")
    }
    else {
        $summary.Add("water: menu macro already exists")
    }

    if ($AddSplitButton) {
        if (Add-RibbonButtonToSplitIfMissing -Document $ribbonRoot -SplitText $miscText -ButtonText $ButtonText -MacroId $waterBuiltInMacroId) {
            $summary.Add("water: added ribbon button to split 'Разное'")
        }
        else {
            $summary.Add("water: ribbon button already exists in split 'Разное'")
        }
    }
    else {
        if (Remove-RibbonButtonFromSplitIfPresent -Document $ribbonRoot -SplitText $miscText -ButtonText $ButtonText -MacroId $waterBuiltInMacroId) {
            $summary.Add("water: removed ribbon button from split 'Разное'")
        }
    }

    if ($AddPipelineButton) {
        if (Add-RibbonButtonToPipelineRowIfMissing -Document $ribbonRoot -ButtonText $ButtonText -MacroId $waterBuiltInMacroId) {
            $summary.Add("water: added standalone ribbon button in pipeline panel")
        }
        else {
            $summary.Add("water: standalone ribbon button already exists in pipeline panel")
        }
    }
    else {
        if (Remove-RibbonButtonFromPipelineRowIfPresent -Document $ribbonRoot -ButtonText $ButtonText -MacroId $waterBuiltInMacroId) {
            $summary.Add("water: removed standalone ribbon button from pipeline panel")
        }
    }

    if ($AddRibbonTab) {
        if (Add-RibbonTabIfMissing -Document $ribbonRoot -TabText "DTMXtest" -ButtonText $ButtonText -MacroId $waterBuiltInMacroId) {
            $summary.Add("water: added ribbon tab DTMXtest")
        }
        else {
            $summary.Add("water: ribbon tab DTMXtest already exists")
        }
    }

    foreach ($cmdButton in $dtmxCommandButtons) {
        if (Add-MenuMacroIfMissing -Document $menuGroup -MacroId $cmdButton.MacroId -MacroName $cmdButton.MacroName -CommandString $cmdButton.CommandString -SmallImage $cmdButton.SmallImage -LargeImage $cmdButton.LargeImage) {
            $summary.Add("water: added menu macro $($cmdButton.MacroId)")
        }
        else {
            $summary.Add("water: menu macro already exists $($cmdButton.MacroId)")
        }

        [void](Set-MenuMacroValues -Document $menuGroup -MacroId $cmdButton.MacroId -MacroName $cmdButton.MacroName -CommandString $cmdButton.CommandString -SmallImage $cmdButton.SmallImage -LargeImage $cmdButton.LargeImage -HelpString $cmdButton.HelpString)
    }

    $buttonResult = Ensure-DtmxTabButtons -Document $ribbonRoot -Buttons $dtmxCommandButtons
    if ($buttonResult.Added.Count -gt 0) {
        $summary.Add("water: added DTMXtest tab buttons: $($buttonResult.Added -join ', ')")
    }
    if ($buttonResult.Updated.Count -gt 0) {
        $summary.Add("water: updated DTMXtest tab button labels: $($buttonResult.Updated -join ', ')")
    }
    if ($buttonResult.Added.Count -eq 0 -and $buttonResult.Updated.Count -eq 0) {
        $summary.Add("water: DTMXtest tab buttons already exist")
    }

    Save-XmlUtf8Bom -Document $menuGroup -Path $menuGroupPath
    Save-XmlUtf8Bom -Document $ribbonRoot -Path $ribbonRootPath
}

foreach ($target in @(
    @{ Prefix = "user"; Cmds = $userRibbonCmdsPath; Tabs = $userRibbonTabsPath },
    @{ Prefix = "cache"; Cmds = $userDataCacheRibbonCmdsPath; Tabs = $userDataCacheRibbonTabsPath }
)) {
    if (Test-Path -LiteralPath $target.Cmds) {
        try {
            if (-not $DryRun) {
                $backupPath = Backup-File -FilePath $target.Cmds -BackupRoot $backupRoot
                $summary.Add("$($target.Prefix): backup RibbonCmds.xml -> $backupPath")
            }

            $ribbonCmds = Load-XmlDocument -Path $target.Cmds
            foreach ($cmdButton in $dtmxCommandButtons) {
                $result = Add-OrUpdate-RibbonCmd -Document $ribbonCmds -CommandId $cmdButton.MacroId -CommandString $cmdButton.CommandString -Resolved "1"
                switch ($result) {
                    "added"   { $summary.Add("$($target.Prefix): added ribbon command $($cmdButton.MacroId)") }
                    "updated" { $summary.Add("$($target.Prefix): updated ribbon command $($cmdButton.MacroId)") }
                }
            }

            if (-not $DryRun) {
                Save-XmlUtf8Bom -Document $ribbonCmds -Path $target.Cmds
                Write-Info "Updated: $($target.Cmds)"
            }
        }
        catch {
            $summary.Add("$($target.Prefix): RibbonCmds.xml skipped ($($_.Exception.Message))")
        }
    }
    else {
        $summary.Add("$($target.Prefix): RibbonCmds.xml not found")
    }

    if (Test-Path -LiteralPath $target.Tabs) {
        try {
            if (-not $DryRun) {
                $backupPath = Backup-File -FilePath $target.Tabs -BackupRoot $backupRoot
                $summary.Add("$($target.Prefix): backup RibbonTabsAndPanels.xml -> $backupPath")
            }

            $ribbonTabs = Load-XmlDocument -Path $target.Tabs
            foreach ($cmdButton in $dtmxCommandButtons) {
                if (Set-RibbonButtonResolved -Document $ribbonTabs -MacroId $cmdButton.MacroId) {
                    $summary.Add("$($target.Prefix): resolved ribbon buttons for $($cmdButton.MacroId)")
                }
            }

            if (-not $DryRun) {
                Save-XmlUtf8Bom -Document $ribbonTabs -Path $target.Tabs
                Write-Info "Updated: $($target.Tabs)"
            }
        }
        catch {
            $summary.Add("$($target.Prefix): RibbonTabsAndPanels.xml skipped ($($_.Exception.Message))")
        }
    }
    else {
        $summary.Add("$($target.Prefix): RibbonTabsAndPanels.xml not found")
    }
}

Write-Info "Patch summary:"
$summary | ForEach-Object { Write-Info " - $_" }

if ($DryRun) {
    Write-Info "DryRun completed. No files were changed."
}
else {
    Write-Info "Patch completed. Restart Model Studio CS WATER to verify ribbon changes."
}

