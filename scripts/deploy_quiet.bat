@echo off
rem NOTE for future editors: NEVER put "exit /b <code>" inside a
rem parenthesized (...) block in this file. cmd loses non-zero exit codes
rem when exiting from nested blocks (observed: failures silently reported
rem as success). All failure exits live at flat :labels below, reached
rem via "goto". Flat "exit /b 0" after straight-line code is fine.
setlocal enabledelayedexpansion
cd /d "%~dp0.."

rem --- Non-interactive: never prompt for credentials or gc cleanup (headless scheduler) ---
set "GIT_TERMINAL_PROMPT=0"

for /f "delims=" %%i in ('powershell -NoProfile -Command Get-Date -Format yyyy-MM-dd') do set "_today=%%i"

set "output_dir=output"
set "docs_dir=docs"

for /f "delims=" %%f in ('dir /b /o-d "%output_dir%\newsletter_*.html" 2^>nul') do (
    set "latest=%%f"
    goto :found
)

echo No newsletter file found in %output_dir%/
exit /b 1

:found
echo Deploying: !latest!
copy /y "%output_dir%\!latest!" "%docs_dir%\index.html" >nul
if errorlevel 1 goto :copy_failed

git add docs/

rem --- Commit only if there is something to commit (a failed push earlier may have left a commit behind) ---
set "_dirty="
for /f "delims=" %%s in ('git status --porcelain -- docs/') do set "_dirty=1"
if defined _dirty (
    git -c gc.auto=0 commit -m "update newsletter"
    if errorlevel 1 goto :commit_failed
) else (
    echo Nothing to commit - already up to date.
)

rem --- Pull first: the other machine (primary/failover) may have pushed since our last sync ---
git -c gc.auto=0 pull --rebase
if errorlevel 1 goto :pull_failed

git -c gc.auto=0 push
if errorlevel 1 (
    echo Git push failed, retrying after pull --rebase...
    git -c gc.auto=0 pull --rebase
    if errorlevel 1 goto :pull_retry_failed
    git -c gc.auto=0 push
    if errorlevel 1 goto :push_failed
)

rem --- Deploy marker: tells the other machine (via OneDrive sync) that today is done ---
echo %COMPUTERNAME% %date% %time% > "cache\deployed_!_today!.txt"

echo Done! Newsletter deployed to docs/index.html
exit /b 0

:copy_failed
echo FAILED at copy step: could not copy %output_dir%\!latest! to %docs_dir%/index.html
exit /b 1

:commit_failed
echo FAILED at commit step: git commit for docs/ failed.
exit /b 1

:pull_failed
echo FAILED at pull step: git pull --rebase failed, aborting deploy.
exit /b 1

:pull_retry_failed
echo FAILED at pull-retry step: git pull --rebase ^(retry^) failed.
exit /b 1

:push_failed
echo FAILED at push step: git push failed even after pull --rebase retry.
exit /b 1
