@echo off
setlocal
cd /d "%~dp0"
set HF_HUB_OFFLINE=1
set TRANSFORMERS_OFFLINE=1
.venv\Scripts\python.exe local_ui.py
pause
