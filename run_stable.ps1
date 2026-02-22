param(
  [int]$Port = 8000
)

$ErrorActionPreference = "Stop"

# Always run from repo root (where this script lives)
Set-Location $PSScriptRoot

# Ensure we run using the repo virtual environment Python
$venvPy = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (Test-Path $venvPy) {
  $python = $venvPy
} else {
  throw "Virtualenv python not found at $venvPy. Create it with: py -m venv .venv"
}

# Stable operational defaults (avoid fragile dev modes)
$env:PRICEWATCH_HEADFUL = "0"
$env:PRICEWATCH_SLOWMO_MS = "0"
$env:PRICEWATCH_DEBUG_CAPTURE = "1"   # keep artifacts ON; set to 0 if too noisy
$env:PRICEWATCH_SAVE_STATE = "1"
$env:PRICEWATCH_STATE_DIR = "state"
$env:PRICEWATCH_DEBUG_DIR = "scrape_debug"

Write-Host "Starting PriceWatch in STABLE mode on port $Port"
Write-Host "HEADFUL=$env:PRICEWATCH_HEADFUL  SLOWMO_MS=$env:PRICEWATCH_SLOWMO_MS"
Write-Host "DEBUG_CAPTURE=$env:PRICEWATCH_DEBUG_CAPTURE  SAVE_STATE=$env:PRICEWATCH_SAVE_STATE"
Write-Host "Using Python: $python"

# No --reload (more stable), single worker, longer graceful shutdown
& $python -m uvicorn app.main:app `
  --host 127.0.0.1 `
  --port $Port `
  --workers 1 `
  --timeout-graceful-shutdown 60
