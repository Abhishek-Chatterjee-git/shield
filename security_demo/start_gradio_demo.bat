@echo off
setlocal
cd /d "%~dp0"
set HF_HUB_OFFLINE=1
set TRANSFORMERS_OFFLINE=1
set GRADIO_ANALYTICS_ENABLED=False
.venv\Scripts\python.exe app.py
pause
