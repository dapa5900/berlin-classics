@echo off
cd /d "S:\OneDrive - ProSiebenSat.1 Media SE\FileExchange\VibeCoding\newsletter-berlin-classic-cinema"
call scripts\run_timed.bat --no-cache
if not errorlevel 1 (
    call deploy.bat
)
