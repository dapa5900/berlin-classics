@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0.."

REM === Berlin Classics: scheduler-Abschaltung - EINMALIG auf FORGE1 ausfuehren ===
REM Loescht HIER auf dieser Maschine den Task "NewsletterDaily" (und den Legacy-
REM "NewsletterGenerator"). Tasks sind pro Maschine lokal, der Loeschvorgang
REM ist NICHT ueber OneDrive syncbar. Die DELL-Primary-Registrierung bleibt
REM unberuehrt, solange dieses Skript nicht auf DELL bestaetigt wird.
REM Re-Aktivierung spaeter: FORGE1-Guard in run_daily.bat entfernen und
REM scripts\setup_failover_forge1.bat auf FORGE1 ausfuehren.

if /i "%COMPUTERNAME%"=="FORGE1" goto :do_delete

echo.
echo WARNING: this computer is "%COMPUTERNAME%", not FORGE1.
echo Running this here would delete the scheduler task on THIS machine.
echo.
set /p "_go=Delete NewsletterDaily on %COMPUTERNAME% anyway? [y/N] "
if /i "!_go!"=="y" goto :do_delete

echo Aborted. Nothing deleted.
pause
exit /b 0

:do_delete
echo Deleting task "NewsletterDaily" ...
schtasks /delete /tn "NewsletterDaily" /f
echo Deleting legacy task "NewsletterGenerator" (if present) ...
schtasks /delete /tn "NewsletterGenerator" /f

echo.
echo Verification (both should report "cannot find"):
schtasks /query /tn NewsletterDaily
schtasks /query /tn NewsletterGenerator

echo.
echo %date% %time% %COMPUTERNAME% - Scheduler task disabled via disable_forge_task.bat >> "logs\scheduler.log"
echo Done. Close this window.
pause
exit /b 0
