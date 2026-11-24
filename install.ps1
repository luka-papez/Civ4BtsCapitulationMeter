# Installs Capitulation Meter into an existing BUG Mod installation.
param(
    [string]$CustomAssets = (Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'My Games\Beyond the Sword\CustomAssets')
)
$ErrorActionPreference = 'Stop'
$source = Join-Path $PSScriptRoot 'CustomAssets'
$init = Join-Path $CustomAssets 'Config\init.xml'

if (-not (Test-Path -LiteralPath $init)) {
    throw "BUG Mod not found: $init does not exist. Use -CustomAssets to give the right folder."
}

# Latin-1 keeps every byte of the file as it is
$encoding = [Text.Encoding]::GetEncoding(28591)
$text = [IO.File]::ReadAllText($init, $encoding)
$line = '<load mod="Capitulation Meter"/>'
$anchor = '<load mod="MoreCiv4lerts"/>'

$addLine = -not $text.Contains($line)
if ($addLine -and -not $text.Contains($anchor)) {
    throw "Cannot find $anchor in $init. Add $line to it by hand."
}

foreach ($file in 'Config\Capitulation Meter.xml', 'python\Contrib\CapitulationMeter.py') {
    Copy-Item -LiteralPath (Join-Path $source $file) -Destination (Join-Path $CustomAssets $file) -Force
}

if ($addLine) {
    $backup = "$init.bak"
    if (-not (Test-Path -LiteralPath $backup)) { Copy-Item -LiteralPath $init -Destination $backup }
    $at = $text.IndexOf($anchor) + $anchor.Length
    [IO.File]::WriteAllText($init, $text.Insert($at, "`r`n`t$line"), $encoding)
    "Installed, and registered in init.xml."
} else {
    "Installed. init.xml already had the line."
}
