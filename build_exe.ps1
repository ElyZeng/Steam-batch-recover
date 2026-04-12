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

& $python -m PyInstaller `
  --noconfirm `
  --clean `
  --windowed `
  --name SteamGameBatchRecover `
  --paths src `
  main.py

if ($LASTEXITCODE -ne 0) {
  throw "PyInstaller failed with exit code $LASTEXITCODE"
}

Write-Host "Build finished. EXE path: dist/SteamGameBatchRecover/SteamGameBatchRecover.exe"
