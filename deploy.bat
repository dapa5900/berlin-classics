@echo off
setlocal enabledelayedexpansion

set "output_dir=output"
set "docs_dir=docs"

for /f "delims=" %%f in ('dir /b /o-d "%output_dir%\newsletter_*.html" 2^>nul') do (
    set "latest=%%f"
    goto :found
)

echo No newsletter file found in %output_dir%/
echo Run run_process.bat first.
pause
exit /b 1

:found
echo Deploying: %latest%
copy /y "%output_dir%\%latest%" "%docs_dir%\index.html" >nul
if errorlevel 1 (
    echo Failed to copy newsletter to %docs_dir%/index.html
    pause
    exit /b 1
)

git add docs/
git commit -m "update newsletter"
git push

echo.
echo Done! Your newsletter is live at:
echo https://dapa5900.github.io/berlin-classics/
pause
