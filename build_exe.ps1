$ErrorActionPreference = "Stop"

function Get-SignToolPath {
  $candidate = Get-Command signtool.exe -ErrorAction SilentlyContinue
  if ($candidate) {
    return $candidate.Source
  }

  $roots = @(
    "$env:ProgramFiles (x86)\Windows Kits\10\bin",
    "$env:ProgramFiles\Windows Kits\10\bin"
  )

  foreach ($root in $roots) {
    if (-not (Test-Path $root)) {
      continue
    }

    $found = Get-ChildItem -Path $root -Recurse -Filter signtool.exe -ErrorAction SilentlyContinue |
      Sort-Object FullName -Descending |
      Select-Object -First 1
    if ($found) {
      return $found.FullName
    }
  }

  return $null
}

function Sign-Executable {
  param(
    [Parameter(Mandatory = $true)]
    [string]$ExePath
  )

  $certPath = $env:CODESIGN_CERT_PATH
  $certPassword = $env:CODESIGN_CERT_PASSWORD
  $timestampUrl = if ($env:CODESIGN_TIMESTAMP_URL) { $env:CODESIGN_TIMESTAMP_URL } else { "http://timestamp.digicert.com" }

  if ([string]::IsNullOrWhiteSpace($certPath)) {
    Write-Host "Skipping code signing for $ExePath (CODESIGN_CERT_PATH not set)."
    return
  }

  if (-not (Test-Path $certPath)) {
    throw "Code signing certificate not found at: $certPath"
  }

  if ([string]::IsNullOrWhiteSpace($certPassword)) {
    throw "CODESIGN_CERT_PASSWORD must be set when CODESIGN_CERT_PATH is provided."
  }

  $signTool = Get-SignToolPath
  if (-not $signTool) {
    throw "signtool.exe not found. Install Windows SDK Signing Tools."
  }

  Write-Host "Signing $ExePath"
  & $signTool sign /fd SHA256 /f $certPath /p $certPassword /tr $timestampUrl /td SHA256 $ExePath
  if ($LASTEXITCODE -ne 0) {
    throw "Code signing failed for $ExePath with exit code $LASTEXITCODE"
  }

  Write-Host "Verifying signature: $ExePath"
  & $signTool verify /pa $ExePath
  if ($LASTEXITCODE -ne 0) {
    throw "Signature verification failed for $ExePath with exit code $LASTEXITCODE"
  }
}

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
  --hidden-import pyscreeze `
  --hidden-import PIL `
  --hidden-import PIL.Image `
  --hidden-import PIL.ImageGrab `
  --hidden-import pygetwindow `
  --hidden-import mouseinfo `
  --add-data "SteamGUI_material:SteamGUI_material" `
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
  --hidden-import pyscreeze `
  --hidden-import PIL `
  --hidden-import PIL.Image `
  --hidden-import PIL.ImageGrab `
  --hidden-import pygetwindow `
  --hidden-import mouseinfo `
  --add-data "SteamGUI_material:SteamGUI_material" `
  main.py

if ($LASTEXITCODE -ne 0) {
  throw "PyInstaller single-file build failed with exit code $LASTEXITCODE"
}


$multiFileExe = Join-Path $PSScriptRoot "dist\SteamGameBatchRecover\SteamGameBatchRecover.exe"
$singleFileExe = Join-Path $PSScriptRoot "dist\SteamGameBatchRecover-standalone.exe"

if (Test-Path $multiFileExe) {
  Sign-Executable -ExePath $multiFileExe
}
else {
  Write-Host "Multi-file EXE not found at expected path: $multiFileExe"
}

if (Test-Path $singleFileExe) {
  Sign-Executable -ExePath $singleFileExe
}
else {
  Write-Host "Single-file EXE not found at expected path: $singleFileExe"
}

Write-Host "Build finished."
Write-Host "Multi-file version: dist/SteamGameBatchRecover/ (faster, requires _internal folder)"
Write-Host "Single-file version: dist/SteamGameBatchRecover-standalone.exe (portable, self-contained)"
