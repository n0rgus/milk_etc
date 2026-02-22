param(
  [int]$Port = 8000
)

$ErrorActionPreference = "Stop"

$env:PRICEWATCH_HEADFUL = "0"
$env:PRICEWATCH_SLOWMO_MS = "0"
$env:PRICEWATCH_DEBUG_CAPTURE = "1"
$env:PRICEWATCH_SAVE_STATE = "1"
$env:PRICEWATCH_STATE_DIR = "state"
$env:PRICEWATCH_DEBUG_DIR = "scrape_debug"

Write-Host "Starting PriceWatch in STABLE mode on port $Port"
Write-Host "HEADFUL=$env:PRICEWATCH_HEADFUL  SLOWMO_MS=$env:PRICEWATCH_SLOWMO_MS"
Write-Host "DEBUG_CAPTURE=$env:PRICEWATCH_DEBUG_CAPTURE  SAVE_STATE=$env:PRICEWATCH_SAVE_STATE"

python -m uvicorn app.main:app `
  --host 127.0.0.1 `
  --port $Port `
  --workers 1 `
  --timeout-graceful-shutdown 60
