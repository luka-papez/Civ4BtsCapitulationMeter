# Installs or uninstalls Capitulation Meter in an existing BUG Mod installation.
# Normally run through install.bat / uninstall.bat.
param(
    # the folder that holds BUG's Config and python folders
    [string]$CustomAssets,
    [switch]$Uninstall
)
$ErrorActionPreference = 'Stop'
if (-not $CustomAssets) {
    $CustomAssets = Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'My Games\Beyond the Sword\CustomAssets'
}
$source = Join-Path $PSScriptRoot 'CustomAssets'
$init = Join-Path $CustomAssets 'Config\init.xml'
$files = 'Config\Capitulation Meter.xml', 'python\Contrib\CapitulationMeter.py'
$line = '<load mod="Capitulation Meter"/>'
$anchor = '<load mod="MoreCiv4lerts"/>'

function Stop-Install([string]$Message) {
    Write-Host "ERROR: $Message" -ForegroundColor Red
    exit 1
}

try {
    if (Get-Process -Name 'Civ4BeyondSword' -ErrorAction SilentlyContinue) {
        Stop-Install 'Civilization IV is running. Close it and try again.'
    }
    if (-not (Test-Path -LiteralPath $init)) {
        Stop-Install ("BUG Mod was not found in:`n  $CustomAssets`n" +
            "Install BUG first. If it is somewhere else, drag the folder that holds its`n" +
            "'Config' and 'python' folders onto the .bat file.")
    }

    # Latin-1 keeps every byte of the file as it is
    $encoding = [Text.Encoding]::GetEncoding(28591)
    $text = [IO.File]::ReadAllText($init, $encoding)

    if ($Uninstall) {
        [IO.File]::WriteAllText($init, [regex]::Replace($text, '[ \t]*' + [regex]::Escape($line) + '[ \t]*(\r?\n)?', ''), $encoding)
        foreach ($file in $files) {
            $target = Join-Path $CustomAssets $file
            if (Test-Path -LiteralPath $target) { Remove-Item -LiteralPath $target }
        }
        Write-Host "Capitulation Meter was removed from:`n  $CustomAssets" -ForegroundColor Green
        exit 0
    }

    $addLine = -not $text.Contains($line)
    if ($addLine -and -not $text.Contains($anchor)) {
        Stop-Install "Cannot find $anchor in`n  $init`nThis BUG version is not supported by the installer. See the manual steps in README.md."
    }
    foreach ($file in $files) {
        Copy-Item -LiteralPath (Join-Path $source $file) -Destination (Join-Path $CustomAssets $file) -Force
    }
    if ($addLine) {
        $backup = "$init.bak"
        if (-not (Test-Path -LiteralPath $backup)) { Copy-Item -LiteralPath $init -Destination $backup }
        $at = $text.IndexOf($anchor) + $anchor.Length
        [IO.File]::WriteAllText($init, $text.Insert($at, "`r`n`t$line"), $encoding)
    }
    Write-Host "Capitulation Meter is installed in:`n  $CustomAssets`nStart the game and load a save where you are at war." -ForegroundColor Green
} catch {
    Stop-Install $_.Exception.Message
}
