@echo off
rem DIAVLO MIND - installs the skill and the "use it by default" rule in every AI tool found on this PC.
rem   install-all.bat                 tools found on this computer
rem   install-all.bat --dry-run       show everything, write nothing
rem   install-all.bat --lang es       the rule in Spanish
rem   install-all.bat --all           all four tools, found or not
rem   install-all.bat --uninstall     remove the skills and the rule
rem Needs Python 3.9 or later. Nothing is downloaded. Only your own user folder is changed.
setlocal

set "PYCMD="
for %%C in ("py -3" "python" "python3") do (
  if not defined PYCMD (
    %%~C -c "import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)" >nul 2>nul
    if not errorlevel 1 set "PYCMD=%%~C"
  )
)

if not defined PYCMD goto nopython
%PYCMD% "%~dp0scripts\install_all.py" %*
set "RC=%ERRORLEVEL%"
goto finish

:nopython
echo.
echo Python 3.9 or later was not found / No encuentro Python 3.9 o superior.
echo Install it from https://www.python.org/downloads/ and run this file again.
echo Or run DIAVLO-MIND-Setup.bat: it installs Python for you / o ejecuta DIAVLO-MIND-Setup.bat: instala Python por ti.
set "RC=1"

:finish
echo.
if "%~1"=="" pause
exit /b %RC%
