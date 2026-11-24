@echo off
rem Double-click to install. Or drag BUG's folder (the one with Config and python) onto this file.
if not exist "%~dp0install.ps1" (
    echo ERROR: Extract the whole zip first, then run install.bat from the extracted folder.
    pause
    exit /b 1
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1" -CustomAssets "%~1"
set result=%errorlevel%
echo.
pause
exit /b %result%
