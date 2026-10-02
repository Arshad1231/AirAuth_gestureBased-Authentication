# Starts the three services in separate PowerShell windows.
#     powershell -ExecutionPolicy Bypass -File scripts\start-dev.ps1
# Requires MongoDB to be running (local service, Docker or Atlas URI in server\.env).

$root = Split-Path -Parent $PSScriptRoot

# Reload PATH from the system so tools installed after this terminal (or VS Code)
# was opened - e.g. Node.js - are found.  The child windows inherit it.
$env:Path = [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' +
            [Environment]::GetEnvironmentVariable('Path', 'User')

if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    Write-Error "npm not found. Install Node.js 18+ (winget install OpenJS.NodeJS.LTS)."
    exit 1
}

Start-Process powershell -ArgumentList '-NoExit', '-Command', `
    "cd '$root\ml-service'; .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000"

Start-Process powershell -ArgumentList '-NoExit', '-Command', "cd '$root\server'; npm run dev"

Start-Process powershell -ArgumentList '-NoExit', '-Command', "cd '$root\client'; npm run dev"

Write-Host "ML service : http://127.0.0.1:8000/docs"
Write-Host "API        : http://localhost:5000/api/system/health"
Write-Host "Web app    : http://localhost:5173"

# =============================================================================
# FILE SUMMARY
# -----------------------------------------------------------------------------
# start-dev.ps1 refreshes PATH from the system (so a freshly installed Node.js
# is found), then launches the development stack in three windows: the FastAPI
# ML service (port 8000), the Express API with nodemon (port 5000) and the
# Vite React dev server (port 5173), and prints their URLs.
# =============================================================================
