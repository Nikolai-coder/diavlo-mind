@echo off
rem DIAVLO MIND - Windows setup: installs what DIAVLO MIND needs, then DIAVLO MIND itself.
rem Download this one file from the Releases page and double-click it, or run it from the repository folder.
rem
rem   DIAVLO-MIND-Setup.bat                 install in the AI tools found on this computer
rem   DIAVLO-MIND-Setup.bat --dry-run       show what the installer would write (Python and the download still happen)
rem   DIAVLO-MIND-Setup.bat --lang es       the rule in Spanish
rem   DIAVLO-MIND-Setup.bat --all           all four tools, found or not
rem   DIAVLO-MIND-Setup.bat --uninstall     remove the skills and the rule
rem   Any other option of install-all.bat / scripts\install_all.py is passed on unchanged.
rem
rem What it does, only inside your own user folder and without administrator rights:
rem   1. Looks for Python 3.9 or later. If there is none, installs Python 3.12 for your user only:
rem      with winget when it is available, otherwise the official python.org installer
rem      (its MD5 checksum and its Python Software Foundation signature are checked before it runs).
rem   2. Uses the DIAVLO MIND files next to this file. If there are none (you downloaded only this file),
rem      downloads the latest release from GitHub into %USERPROFILE%\.diavlo-mind\source.
rem   3. Runs scripts\install_all.py with the options you gave.
rem DIAVLO MIND itself needs nothing else: its scripts use the Python standard library only.
setlocal EnableExtensions

set "DM_REPO=Nikolai-coder/diavlo-mind"
set "DM_ZIP_URL=https://github.com/%DM_REPO%/releases/latest/download/DIAVLO-MIND-FABLE-EDITION.zip"
set "DM_ZIP_FALLBACK=https://github.com/%DM_REPO%/archive/refs/heads/main.zip"
set "PY_VER=3.12.10"
set "PY_WINGET_ID=Python.Python.3.12"
set "PY_ARCH=amd64"
set "PY_MD5=5eddb0b6f12c852725de071ae681dde4"
if /i "%PROCESSOR_ARCHITECTURE%"=="ARM64" set "PY_ARCH=arm64"
if /i "%PROCESSOR_ARCHITEW6432%"=="ARM64" set "PY_ARCH=arm64"
if "%PY_ARCH%"=="arm64" set "PY_MD5=37df52717faa6c514342b8d43cae7026"
set "PY_URL=https://www.python.org/ftp/python/%PY_VER%/python-%PY_VER%-%PY_ARCH%.exe"
set "PY_EXE=%TEMP%\python-%PY_VER%-%PY_ARCH%.exe"
set "RC=0"

echo.
echo  DIAVLO MIND setup
echo  -----------------

rem ---------------------------------------------------------------- 1. Python
echo.
echo [1/3] Python 3.9+ ...
call :findpy
if defined PYCMD goto havepython
echo       Not found / No encontrado. Installing Python %PY_VER% for this user / Instalando Python %PY_VER% para este usuario...
call :installpy
call :findpy
if defined PYCMD goto havepython
echo.
echo ERROR: Python could not be installed automatically / No se pudo instalar Python automaticamente.
echo        Install it from https://www.python.org/downloads/ (tick "Add python.exe to PATH")
echo        and run this file again / y vuelve a ejecutar este archivo.
set "RC=1"
goto finish

:havepython
%PYCMD% -c "import sys; print('      OK: Python', sys.version.split()[0], '-', sys.executable)"

rem ---------------------------------------------------------------- 2. DIAVLO MIND files
echo.
echo [2/3] DIAVLO MIND files / archivos ...
set "DM_SRC=%~dp0"
if exist "%~dp0SKILL.md" if exist "%~dp0scripts\install_all.py" goto havesource
set "DM_SRC=%USERPROFILE%\.diavlo-mind\source\"
echo       Downloading the latest release / Descargando la ultima version...
call :download "%DM_ZIP_URL%"
if errorlevel 1 (
  echo       The release download failed; trying the main branch / Fallo la release; probando la rama main...
  call :download "%DM_ZIP_FALLBACK%"
)
if errorlevel 1 (
  echo.
  echo ERROR: could not download DIAVLO MIND / no se pudo descargar DIAVLO MIND.
  echo        Check your internet connection, or download it from https://github.com/%DM_REPO%
  set "RC=1"
  goto finish
)

:havesource
echo       OK: %DM_SRC%

rem ---------------------------------------------------------------- 3. Install
echo.
echo [3/3] Installing / Instalando DIAVLO MIND ...
echo.
%PYCMD% "%DM_SRC%scripts\install_all.py" %*
set "RC=%ERRORLEVEL%"
goto finish

rem ================================================================ subroutines

:findpy
rem Sets PYCMD to a Python 3.9+ command, or leaves it empty.
set "PYCMD="
for %%C in ("py -3" "python" "python3") do (
  if not defined PYCMD (
    %%~C -c "import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)" >nul 2>nul
    if not errorlevel 1 set "PYCMD=%%~C"
  )
)
if defined PYCMD exit /b 0
rem A Python installed a moment ago is not on this window's PATH yet: look where the installers put it.
for %%P in ("%LOCALAPPDATA%\Programs\Python\Launcher\py.exe" "%WINDIR%\py.exe") do (
  if not defined PYCMD if exist "%%~P" (
    "%%~P" -3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)" >nul 2>nul
    if not errorlevel 1 set PYCMD="%%~P" -3
  )
)
if defined PYCMD exit /b 0
for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python3*" "%ProgramFiles%\Python3*") do (
  if not defined PYCMD if exist "%%~D\python.exe" (
    "%%~D\python.exe" -c "import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)" >nul 2>nul
    if not errorlevel 1 set PYCMD="%%~D\python.exe"
  )
)
exit /b 0

:installpy
where winget >nul 2>nul
if errorlevel 1 goto installpy_direct
echo       winget install %PY_WINGET_ID% ...
winget install --exact --id %PY_WINGET_ID% --scope user --silent --accept-package-agreements --accept-source-agreements
call :findpy
if defined PYCMD exit /b 0
echo       winget did not finish the job; using the python.org installer / winget no lo consiguio; uso el instalador de python.org
:installpy_direct
echo       Downloading / Descargando %PY_URL%
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; $ProgressPreference='SilentlyContinue'; [Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -UseBasicParsing -Uri $env:PY_URL -OutFile $env:PY_EXE; if ((Get-FileHash -Algorithm MD5 -LiteralPath $env:PY_EXE).Hash -ne $env:PY_MD5) { throw 'checksum mismatch' }; $s = Get-AuthenticodeSignature -LiteralPath $env:PY_EXE; if ($s.Status -ne 'Valid' -or $s.SignerCertificate.Subject -notmatch 'Python Software Foundation') { throw 'signature not valid' }"
if errorlevel 1 (
  echo       The download or its check failed / Fallo la descarga o su comprobacion.
  if exist "%PY_EXE%" del /q "%PY_EXE%" >nul 2>nul
  exit /b 1
)
echo       Running the installer quietly / Ejecutando el instalador en silencio (1-2 min)...
"%PY_EXE%" /quiet InstallAllUsers=0 InstallLauncherAllUsers=0 Include_launcher=1 PrependPath=1 Include_test=0
set "PY_RC=%ERRORLEVEL%"
del /q "%PY_EXE%" >nul 2>nul
if not "%PY_RC%"=="0" (
  echo       The Python installer ended with code %PY_RC% / El instalador de Python termino con el codigo %PY_RC%.
  exit /b 1
)
exit /b 0

:download
rem Downloads the ZIP at %1 and unpacks the folder that holds SKILL.md into %DM_SRC% (replacing an older copy).
set "DM_URL=%~1"
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; $ProgressPreference='SilentlyContinue'; [Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; $tmp = Join-Path $env:TEMP ('diavlo-mind-' + [guid]::NewGuid()); New-Item -ItemType Directory -Path $tmp | Out-Null; try { $zip = Join-Path $tmp 'dm.zip'; Invoke-WebRequest -UseBasicParsing -Uri $env:DM_URL -OutFile $zip; Expand-Archive -LiteralPath $zip -DestinationPath (Join-Path $tmp 'x'); $top = Get-ChildItem -LiteralPath (Join-Path $tmp 'x') -Directory | Where-Object { Test-Path -LiteralPath (Join-Path $_.FullName 'scripts\install_all.py') } | Select-Object -First 1; if (-not $top) { throw 'the archive has no DIAVLO MIND folder' }; $dest = $env:DM_SRC.TrimEnd('\'); if (Test-Path -LiteralPath $dest) { Remove-Item -LiteralPath $dest -Recurse -Force }; New-Item -ItemType Directory -Path (Split-Path -Parent $dest) -Force | Out-Null; Move-Item -LiteralPath $top.FullName -Destination $dest } finally { Remove-Item -LiteralPath $tmp -Recurse -Force -ErrorAction SilentlyContinue }"
exit /b %ERRORLEVEL%

:finish
echo.
if "%RC%"=="0" (echo Done / Hecho.) else (echo Finished with errors, code %RC% / Terminado con errores, codigo %RC%.)
if "%~1"=="" pause
exit /b %RC%
