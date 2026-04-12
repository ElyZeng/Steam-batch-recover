$ErrorActionPreference = "Stop"

$venvPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
$systemPython = "C:/Users/whoareyou/AppData/Local/Programs/Python/Python312/python.exe"
$python = if (Test-Path $venvPython) { $venvPython } else { $systemPython }

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
