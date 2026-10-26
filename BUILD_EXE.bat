@echo off
setlocal
REM Builds spoutyPreview.exe (one portable file) from spoutyPreview.py.
REM SpoutGL has no build for Python 3.14 yet, so this uses Python 3.13 (or 3.12)
REM in a private build folder (.build-venv). Your normal Python is not touched.
cd /d "%~dp0"

set "PYV="
py -3.13 -c "import sys" >nul 2>&1 && set "PYV=-3.13"
if not defined PYV py -3.12 -c "import sys" >nul 2>&1 && set "PYV=-3.12"

if not defined PYV (
  echo Python 3.13 not found - installing it alongside your current Python...
  winget install --id Python.Python.3.13 -e --scope user --silent --accept-package-agreements --accept-source-agreements
  py -3.13 -c "import sys" >nul 2>&1 && set "PYV=-3.13"
)
if not defined PYV (
  echo.
  echo Could not find or install Python 3.13.
  echo Install it from https://www.python.org/downloads/release/python-3139/ then run this again.
  goto :fail
)

echo Using Python %PYV%
if not exist .build-venv\Scripts\python.exe py %PYV% -m venv .build-venv || goto :fail
set "VPY=.build-venv\Scripts\python.exe"

echo Installing build tools...
"%VPY%" -m pip install --upgrade pip >nul
"%VPY%" -m pip install --only-binary=:all: pygame-ce PyOpenGL SpoutGL pyinstaller || goto :fail

echo Building...
"%VPY%" -m PyInstaller --noconfirm --clean --onefile --windowed ^
  --name spoutyPreview ^
  --collect-all SpoutGL ^
  --hidden-import OpenGL.platform.win32 ^
  spoutyPreview.py || goto :fail

copy /y dist\spoutyPreview.exe . >nul
echo.
echo Done: spoutyPreview.exe is in this folder. Copy it anywhere; it makes spoutyPreview.ini next to itself.
pause
exit /b 0

:fail
echo.
echo Build failed - copy the messages above and send them to Claude.
pause
exit /b 1
