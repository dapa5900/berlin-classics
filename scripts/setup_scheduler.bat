@echo off
REM DEPRECATED (2026-10-08): do NOT register the legacy NewsletterGenerator task anymore.
REM Primary/failover scheme: DELL runs NewsletterDaily at 14:00, FORGE1 at 16:00 via
REM scripts\setup_failover_forge1.bat (imports scripts\task_failover_16h00.xml).
echo DEPRECATED: use setup_failover_forge1.bat instead. Aborting.
exit /b 1

echo Setting up newsletter task at 13:00...

schtasks /create /tn "NewsletterGenerator" /tr "cmd /c \"%~dp0run_scheduled.bat\"" /sc DAILY /mo 3 /st 13:00 /f

if %errorlevel% equ 0 (
    echo Task created successfully!
    echo It will run every 3 days at 13:00, performing a full scrape and deployment.
) else (
    echo Failed to create task. Check that you're running as administrator.
)
