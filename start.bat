@echo off
setlocal
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  py -3.11 -m venv .venv
  if errorlevel 1 (
    echo Python 3.11 is required. Install it from python.org, then run this file again.
    pause
    exit /b 1
  )
)
.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
if errorlevel 1 (
  echo Dependency installation failed. Check your internet connection and try again.
  pause
  exit /b 1
)
echo.
echo Open http://127.0.0.1:8000 in your browser.
echo Keep this window open while using Clarity. Press Ctrl+C to stop.
.venv\Scripts\python.exe launch.py
pause
