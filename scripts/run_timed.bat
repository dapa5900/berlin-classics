@echo off
setlocal enabledelayedexpansion
set _start=%time%
call venv\Scripts\activate
python main.py %*
set _end=%time%
for /f "tokens=1-3 delims=:., " %%a in ("!_start!") do set _sh=%%a& set _sm=%%b& set _ss=%%c
for /f "tokens=1-3 delims=:., " %%a in ("!_end!") do set _eh=%%a& set _em=%%b& set _es=%%c
if "!_sh:~1!"=="" set _sh=0!_sh!
if "!_eh:~1!"=="" set _eh=0!_eh!
set /a _start_s = 1!_sh! * 3600 + 1!_sm! * 60 + 1!_ss! - 366100
set /a _end_s = 1!_eh! * 3600 + 1!_em! * 60 + 1!_es! - 366100
if !_end_s! LSS !_start_s! set /a _end_s += 86400
set /a _elapsed = !_end_s! - !_start_s!
set /a _h = !_elapsed! / 3600
set /a _m = ( !_elapsed! - 3600 * _h ) / 60
set /a _s = !_elapsed! - 3600 * _h - 60 * _m
set "_output=!_s!s"
if !_m! GTR 0 set "_output=!_m!m !_s!s"
if !_h! GTR 0 set "_output=!_h!h !_m!m !_s!s"
echo Elapsed: !_output!
