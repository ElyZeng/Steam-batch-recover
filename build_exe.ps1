$ErrorActionPreference = "Stop"

$venvPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"

if (Test-Path $venvPython) {
  $python = $venvPython
}
elseif (Get-Command python -ErrorAction SilentlyContinue) {
  $python = (Get-Command python).Source
}
else {
  throw "Python executable not found. Install Python or create .venv first."
}

& $python -m pip install --upgrade pip
& $python -m pip install -r (Join-Path $PSScriptRoot "requirements.txt")

if ($LASTEXITCODE -ne 0) {
  throw "Dependency installation failed with exit code $LASTEXITCODE"
}

# Build multi-file version (faster startup, requires _internal folder)
Write-Host "Building multi-file version..."
& $python -m PyInstaller `
  --noconfirm `
  --clean `
  --windowed `
  --name SteamGameBatchRecover `
  --paths src `
  main.py

if ($LASTEXITCODE -ne 0) {
  throw "PyInstaller multi-file build failed with exit code $LASTEXITCODE"
}

# Build single-file version (portable, slower startup)
Write-Host "Building single-file version..."
& $python -m PyInstaller `
  --noconfirm `
  --windowed `
  --onefile `
  --name SteamGameBatchRecover-standalone `
  --paths src `
  main.py

if ($LASTEXITCODE -ne 0) {
  throw "PyInstaller single-file build failed with exit code $LASTEXITCODE"
}

Write-Host "Build finished."
Write-Host "Multi-file version: dist/SteamGameBatchRecover/ (faster, requires _internal folder)"
Write-Host "Single-file version: dist/SteamGameBatchRecover-standalone.exe (portable, self-contained)"
