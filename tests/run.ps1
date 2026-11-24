# Runs harness.py in the game's own Python 2.4. Needs 32-bit PowerShell.
param([string]$GameDir)
$ErrorActionPreference = 'Stop'
if ([IntPtr]::Size -ne 4) { throw 'Run this with 32-bit PowerShell (SysWOW64): python24.dll is 32-bit.' }
if (-not $GameDir) {
    $GameDir = (Get-ItemProperty "HKLM:\SOFTWARE\WOW6432Node\Firaxis Games\Sid Meier's Civilization 4").INSTALLDIR
}
$stdlib = Join-Path $GameDir 'Assets\Python\System'
$modDir = Join-Path (Split-Path $PSScriptRoot) 'CustomAssets\python\Contrib'
$out = Join-Path ([IO.Path]::GetTempPath()) "capmeter-$PID.txt"
Add-Type -TypeDefinition @'
using System; using System.Runtime.InteropServices;
public static class Py {
  [DllImport("kernel32", CharSet=CharSet.Unicode, SetLastError=true)] public static extern IntPtr LoadLibraryEx(string p, IntPtr h, uint f);
  [DllImport("python24.dll", CallingConvention=CallingConvention.Cdecl)] public static extern void Py_Initialize();
  [DllImport("python24.dll", CallingConvention=CallingConvention.Cdecl, CharSet=CharSet.Ansi)] public static extern int PyRun_SimpleString(string s);
}
'@
$env:PYTHONPATH = $stdlib
$env:PYTHONHOME = $stdlib
$dll = Join-Path $GameDir 'Beyond the Sword\python24.dll'
if ([Py]::LoadLibraryEx($dll, [IntPtr]::Zero, 8) -eq [IntPtr]::Zero) { throw "Cannot load $dll" }
[Py]::Py_Initialize()
function ConvertTo-PyPath($path) { "r'''" + ($path -replace '\\', '/') + "'''" }
$code = "import sys`nsys.path.insert(0, $(ConvertTo-PyPath $stdlib))`nOUTPATH = $(ConvertTo-PyPath $out)`nMODDIR = $(ConvertTo-PyPath $modDir)`nexec compile(open($(ConvertTo-PyPath (Join-Path $PSScriptRoot 'harness.py')), 'U').read(), 'harness.py', 'exec')`n"
$result = [Py]::PyRun_SimpleString($code)
$lines = @(Get-Content -LiteralPath $out)
Remove-Item -LiteralPath $out
$lines
$passed = @($lines -match '^PASS ').Count
$failed = @($lines -match '^(FAIL|HARNESS ERROR)').Count
"$passed passed, $failed failed"
if ($result -ne 0 -or $failed -or -not $passed) { exit 1 }
