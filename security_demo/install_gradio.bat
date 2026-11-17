@echo off
setlocal
cd /d "%~dp0"
.venv\Scripts\python.exe -m pip install --timeout 30 --retries 1 -r requirements-ui.txt
if errorlevel 1 echo Gradio installation failed. The built-in browser interface remains available.
pause
