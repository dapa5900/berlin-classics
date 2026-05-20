@echo off
schtasks /delete /tn "NewsletterGenerator" /f
if %errorlevel% equ 0 (
    echo Scheduled task removed.
) else (
    echo No task with that name found.
)
