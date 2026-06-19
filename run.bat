@echo off
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo No .venv found. Run setup.bat first.
    exit /b 1
)

.venv\Scripts\python server.py
