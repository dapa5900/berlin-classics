@echo off
echo Setting up newsletter task at 13:00...

schtasks /create /tn "NewsletterGenerator" /tr "cmd /c \"%~dp0run_scheduled.bat\"" /sc DAILY /st 13:00 /f

if %errorlevel% equ 0 (
    echo Task created successfully!
    echo It will run every day at 13:00, performing a full scrape and deployment.
) else (
    echo Failed to create task. Check that you're running as administrator.
)
