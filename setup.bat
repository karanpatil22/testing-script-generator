@echo off
cd /d "%~dp0"

echo =^> Creating virtual environment (.venv)
python -m venv .venv

echo =^> Upgrading pip
.venv\Scripts\python -m pip install --upgrade pip

echo =^> Installing Playwright + pytest
.venv\Scripts\python -m pip install playwright pytest pytest-playwright pytest-asyncio

echo =^> Installing Chromium browser
.venv\Scripts\python -m playwright install chromium

echo.
echo Setup complete. Start the recorder with: run.bat
