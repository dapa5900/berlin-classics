@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0.."

for /f "delims=" %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd"') do set "_today=%%i"
set "marker=cache\run_!_today!.txt"
set "deployed=cache\deployed_!_today!.txt"

rem --- Failover gate 1: already deployed today -> nothing to do ---
rem --- (Whoever runs second - primary 14:00 or failover 16:00 - skips here.) ---
if exist "!deployed!" (
    echo %date% %time% %COMPUTERNAME% - Already deployed today, skipping. >> "logs\scheduler.log"
    exit /b 0
)

set "_need_scrape=1"
if exist "!marker!" (
    rem --- Run marker exists: the other machine ran today. ---
    rem --- Fresh marker (<30 min) = other run may still be in progress -> stay clear. ---
    set "_ageS=999999"
    for /f "delims=" %%a in ('powershell -NoProfile -Command "[int]((Get-Date) - (Get-Item '!marker!').LastWriteTime).TotalSeconds" 2^>nul') do set "_ageS=%%a"
    if !_ageS! LSS 1800 (
        echo %date% %time% %COMPUTERNAME% - Run marker fresh ^(!marker!^), other run may still be in progress. Skipping. >> "logs\scheduler.log"
        exit /b 0
    )
    echo %date% %time% %COMPUTERNAME% - Run marker exists, skipping scrape; trying deploy ^(failover^). >> "logs\scheduler.log"
    set "_need_scrape=0"
) else (
    echo %date% %time% %COMPUTERNAME% - Starting daily run. >> "logs\scheduler.log"
    echo %COMPUTERNAME% %date% %time% > "!marker!"
)

if "!_need_scrape!"=="1" (
    call scripts\run_timed.bat --no-cache
    if errorlevel 1 (
        del "!marker!" >nul 2>&1
        echo %date% %time% %COMPUTERNAME% - Daily run FAILED, marker removed for retry. >> "logs\scheduler.log"
        exit /b 1
    )
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
for /f "delims=" %%f in ('powershell -NoProfile -Command "Get-ChildItem 'cache\deployed_*.txt' | Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-14) } | Select-Object -ExpandProperty Name"') do (
    del "cache\%%f" >nul 2>&1
)
exit /b 0
