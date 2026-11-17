@echo off
setlocal
cd /d "%~dp0"
py -3.12 -m pip download --only-binary=:all: --dest wheelhouse -r requirements-cpu.txt
if errorlevel 1 (
  echo Download failed. Use online setup.bat on the laptop instead.
  pause
  exit /b 1
)
echo Offline dependencies downloaded for this Python and Windows architecture.
pause
