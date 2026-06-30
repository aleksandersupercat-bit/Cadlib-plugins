param(
  [string]$Source = "C:\pdf_ingest\DTMXtest\Scripts\DtmxNrx45.nrx",
  [string]$Destination = "C:\Program Files\CSoft\Model Studio CS\NANOWATER\bin\nanoCAD241\DtmxNrx45.nrx",
  [string]$LogPath = "C:\Users\atsarkov\Desktop\dtmx_install_helper_log.txt",
  [int]$MaxMinutes = 60
)
function Log([string]$Text) {
  $line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') | $Text"
  Add-Content -LiteralPath $LogPath -Value $line -Encoding UTF8
}
Log "helper restart"
$deadline = (Get-Date).AddMinutes($MaxMinutes)
while ((Get-Date) -lt $deadline) {
  try {
    Copy-Item -LiteralPath $Source -Destination $Destination -Force
    Log "copy OK"
    exit 0
  }
  catch {
    Log ("copy wait: " + $_.Exception.Message)
    Start-Sleep -Seconds 5
  }
}
Log "timeout"
exit 1
