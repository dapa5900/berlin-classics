@echo off
echo Setting up newsletter task at 18:00...

schtasks /create /tn "NewsletterGenerator" /tr "cmd /c \"%~dp0run_scheduled.bat\"" /sc DAILY /st 18:00 /f

if %errorlevel% equ 0 (
    echo Task created successfully!
    echo It will run every day at 18:00.
    echo To switch to Thursday only, run:
    echo   scripts\unscheduler.bat
    echo Then re-run this script with: schtasks /change /tn "NewsletterGenerator" /sc WEEKLY /d THU
) else (
    echo Failed to create task. Check that you're running as administrator.
)
