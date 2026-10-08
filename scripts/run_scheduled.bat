@echo off
REM DEPRECATED (2026-10-08): use scripts\run_daily.bat via the NewsletterDaily task instead.
REM run_scheduled.bat has no once-per-day guard and breaks the primary/failover scheme
REM (see scripts\setup_failover_forge1.bat). Kept functional as a manual fallback only.
echo WARNING: run_scheduled.bat is deprecated, use run_daily.bat instead.
cd /d "S:\OneDrive - ProSiebenSat.1 Media SE\FileExchange\VibeCoding\newsletter-berlin-classic-cinema"
call scripts\run_timed.bat --no-cache
if not errorlevel 1 (
    call deploy.bat
)
