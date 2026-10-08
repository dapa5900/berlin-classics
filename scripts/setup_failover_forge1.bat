@echo off
REM === Berlin Classics: Failover-Setup - EINMALIG auf FORGE1 ausfuehren ===
REM Loescht den alten NewsletterGenerator-Task (alle 3 Tage 13:00, ohne Marker-Guard)
REM und registriert NewsletterDaily taeglich um 16:00 als Failover zum DELL-Primary (14:00).
REM Die Skripte + XML-Datei kommen per OneDrive-Sync automatisch auf diese Maschine.
cd /d "%~dp0.."

echo [1/2] Removing legacy task "NewsletterGenerator" (if present)...
schtasks /delete /tn "NewsletterGenerator" /f

echo [2/2] Registering "NewsletterDaily" at 16:00...
schtasks /create /tn NewsletterDaily /xml "%~dp0task_failover_16h00.xml" /f
if errorlevel 1 (
    echo.
    echo Import failed. Fallback: re-run this window as administrator, or register with explicit user:
    echo   schtasks /create /tn NewsletterDaily /xml "%~dp0task_failover_16h00.xml" /ru "%USERNAME%" /f
    pause
    exit /b 1
)

echo.
echo OK. Current registration:
schtasks /query /tn NewsletterDaily /v /fo LIST | findstr /i /c:"HostName" /c:"TaskName" /c:"Next Run Time" /c:"Status" /c:"Start Time"
pause
