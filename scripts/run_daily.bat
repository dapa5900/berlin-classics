@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0.."

for /f "delims=" %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd"') do set "_today=%%i"
set "marker=cache\run_%_today%.txt"

if exist "%marker%" (
    echo %date% %time% %COMPUTERNAME% - Already run today, skipping. >> "logs\scheduler.log"
    exit /b 0
)

echo %date% %time% %COMPUTERNAME% - Starting daily run. >> "logs\scheduler.log"
type nul > "%marker%"

call scripts\run_timed.bat --no-cache
if errorlevel 1 (
    del "%marker%" >nul 2>&1
    echo %date% %time% %COMPUTERNAME% - Daily run FAILED, marker removed for retry. >> "logs\scheduler.log"
    exit /b 1
)

call scripts\deploy_quiet.bat
if errorlevel 1 (
    echo %date% %time% %COMPUTERNAME% - Daily run ok, but DEPLOY FAILED. >> "logs\scheduler.log"
    exit /b 1
)

echo %date% %time% %COMPUTERNAME% - Daily run completed. >> "logs\scheduler.log"

for /f "delims=" %%f in ('powershell -NoProfile -Command "Get-ChildItem 'cache\run_*.txt' | Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-14) } | Select-Object -ExpandProperty Name"') do (
    del "cache\%%f" >nul 2>&1
)
exit /b 0
