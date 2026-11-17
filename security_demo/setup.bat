@echo off
setlocal
cd /d "%~dp0"
py -3.12 -m venv .venv
if errorlevel 1 goto fail
if exist wheelhouse\*.whl (
  .venv\Scripts\python.exe -m pip install --no-index --find-links wheelhouse -r requirements-cpu.txt
) else (
  .venv\Scripts\python.exe -m pip install -r requirements-cpu.txt
)
if errorlevel 1 goto fail
.venv\Scripts\python.exe verify_package.py
if errorlevel 1 goto fail
echo Setup complete. Run start_demo.bat.
pause
exit /b 0
:fail
echo Setup failed. Read the error above. Python 3.12 x64 is required.
pause
exit /b 1
