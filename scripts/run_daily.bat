@echo off
rem NOTE for future editors: NEVER put "exit /b <code>" inside a
rem parenthesized (...) block in this file. cmd loses non-zero exit codes
rem when exiting from nested blocks (observed: scrape/deploy failures
rem silently reported as success to Task Scheduler). All failure exits
rem live at flat :labels below, reached via "goto". Flat "exit /b 0"
rem after straight-line code is fine.
setlocal enabledelayedexpansion
cd /d "%~dp0.."

for /f "delims=" %%i in ('powershell -NoProfile -Command Get-Date -Format yyyy-MM-dd') do set "_today=%%i"
set "marker=cache\run_!_today!.txt"
set "deployed=cache\deployed_!_today!.txt"
set "scraped=cache\scraped_!_today!.txt"

rem --- Failover gate 1: fresh scrape + deploy already done today -> nothing to do ---
rem --- (Whoever runs second - primary 14:00 or failover 16:00 - skips here.) ---
rem --- A manual deploy alone does NOT skip: deployed without scraped means ---
rem --- no fresh scrape happened yet, so we proceed below. ---
if exist "!deployed!" if exist "!scraped!" (
    echo %date% %time% %COMPUTERNAME% - Already scraped and deployed today, skipping. >> "logs\scheduler.log"
    exit /b 0
)
if exist "!deployed!" (
    echo %date% %time% %COMPUTERNAME% - Deployed today but no fresh scrape yet, proceeding. >> "logs\scheduler.log"
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
    if errorlevel 1 goto :scrape_failed
    echo %COMPUTERNAME% %date% %time% > "!scraped!"
)

call scripts\deploy_quiet.bat
if errorlevel 1 goto :deploy_failed

echo %date% %time% %COMPUTERNAME% - Daily run completed. >> "logs\scheduler.log"

for /f "delims=" %%f in ('powershell -NoProfile -Command "Get-ChildItem 'cache\run_*.txt' | Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-14) } | Select-Object -ExpandProperty Name"') do (
    del "cache\%%f" >nul 2>&1
)
for /f "delims=" %%f in ('powershell -NoProfile -Command "Get-ChildItem 'cache\deployed_*.txt' | Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-14) } | Select-Object -ExpandProperty Name"') do (
    del "cache\%%f" >nul 2>&1
)
for /f "delims=" %%f in ('powershell -NoProfile -Command "Get-ChildItem 'cache\scraped_*.txt' | Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-14) } | Select-Object -ExpandProperty Name"') do (
    del "cache\%%f" >nul 2>&1
)
exit /b 0

:scrape_failed
del "!marker!" >nul 2>&1
echo %date% %time% %COMPUTERNAME% - Daily run FAILED, marker removed for retry. >> "logs\scheduler.log"
exit /b 1

:deploy_failed
echo %date% %time% %COMPUTERNAME% - Daily run ok, but DEPLOY FAILED. >> "logs\scheduler.log"
exit /b 1
