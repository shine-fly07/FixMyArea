@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Virtual environment was not found.
    echo Run this from the original FixMyArea project folder, or create the venv first:
    echo python -m venv .venv
    echo .venv\Scripts\python.exe -m pip install -r requirements.txt
    pause
    exit /b 1
)

set PORT=5000
echo Starting FixMyArea on http://127.0.0.1:%PORT%
echo.
echo Admin login:
echo   Email: admin@fixmyarea.local
echo   Password: Admin@123
echo.
echo Keep this window open while using the website.
echo Press Ctrl+C to stop the server.
echo.
".venv\Scripts\python.exe" app.py
pause
