@echo off
setlocal
cd /d "%~dp0"
.venv\Scripts\python.exe benchmark.py --pairs 1
pause
