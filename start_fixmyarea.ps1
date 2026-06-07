$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (!(Test-Path ".\.venv\Scripts\python.exe")) {
    Write-Host "Virtual environment was not found." -ForegroundColor Red
    Write-Host "Create it with: python -m venv .venv"
    Write-Host "Then install dependencies with: .\.venv\Scripts\python.exe -m pip install -r requirements.txt"
    Read-Host "Press Enter to exit"
    exit 1
}

$env:PORT = "5000"
Write-Host "Starting FixMyArea on http://127.0.0.1:$env:PORT" -ForegroundColor Green
Write-Host ""
Write-Host "Admin login:"
Write-Host "  Email: admin@fixmyarea.local"
Write-Host "  Password: Admin@123"
Write-Host ""
Write-Host "Keep this window open while using the website. Press Ctrl+C to stop."
Write-Host ""
& ".\.venv\Scripts\python.exe" app.py
