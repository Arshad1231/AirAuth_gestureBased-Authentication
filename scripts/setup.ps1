# One-time setup of all three tiers.  Run from the project root:
#     powershell -ExecutionPolicy Bypass -File scripts\setup.ps1

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot

# Pick up tools installed after this terminal was opened (e.g. Node.js).
$env:Path = [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' +
            [Environment]::GetEnvironmentVariable('Path', 'User')

Write-Host "== ML service (Python) ==" -ForegroundColor Cyan
Push-Location "$root\ml-service"
if (-not (Test-Path .venv)) { python -m venv .venv }
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
Pop-Location

if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    Write-Warning "Node.js was not found. Install Node 18+ (winget install OpenJS.NodeJS.LTS) and re-run."
    exit 1
}

Write-Host "== Backend (Express) ==" -ForegroundColor Cyan
Push-Location "$root\server"
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
npm install
Pop-Location

Write-Host "== Client (React) ==" -ForegroundColor Cyan
Push-Location "$root\client"
npm install
Pop-Location

Write-Host "Setup complete. Train the models with:" -ForegroundColor Green
Write-Host "  cd ml-service; .\.venv\Scripts\python.exe -m pipelines.run_full_pipeline"
Write-Host "Then start everything with scripts\start-dev.ps1"

# =============================================================================
# FILE SUMMARY
# -----------------------------------------------------------------------------
# setup.ps1 prepares a fresh checkout on Windows: creates the ML service's
# Python virtual environment and installs its requirements, checks for
# Node.js, creates server/.env from the example and installs the npm
# dependencies of the backend and the React client.
# =============================================================================
