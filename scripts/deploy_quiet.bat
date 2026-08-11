@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0.."

set "output_dir=output"
set "docs_dir=docs"

for /f "delims=" %%f in ('dir /b /o-d "%output_dir%\newsletter_*.html" 2^>nul') do (
    set "latest=%%f"
    goto :found
)

echo No newsletter file found in %output_dir%/
exit /b 1

:found
echo Deploying: %latest%
copy /y "%output_dir%\%latest%" "%docs_dir%\index.html" >nul
if errorlevel 1 (
    echo Failed to copy newsletter to %docs_dir%/index.html
    exit /b 1
)

git add docs/
git commit -m "update newsletter"
if errorlevel 1 (
    echo Nothing to commit - already up to date.
) else (
    git push
    if errorlevel 1 (
        echo Git push failed.
        exit /b 1
    )
)

echo Done! Newsletter deployed to docs/index.html
exit /b 0
