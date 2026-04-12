# Steam Game Batch Recover

A Windows-friendly desktop tool that scans Steam backup assets, supports Traditional Chinese / Simplified Chinese / English UI, and helps you run Steam's built-in restore flow in batch-oriented steps.

## What It Supports

- Steam backup package detection:
  - Detects `sku.sis` plus `*.csd` and `*.csm`.
  - Lets you select multiple backup entries and prepare restore paths.
- Three UI languages:
  - `zh-TW` (Traditional Chinese)
  - `zh-CN` (Simplified Chinese)
  - `en` (English)
- Steam built-in restore assistant flow:
  - Launches `Steam.exe`.
  - Shows step-by-step restore instructions in the selected language.
  - Copies selected backup paths to clipboard.
  - Opens selected backup folders for quick browse in Steam restore dialog.

## Important Limitation

Steam does not expose a stable public API/CLI for direct backup restore automation. This tool does not move backup files and does not install games by itself; it assists batch operation around Steam's official restore UI.

## Run

```powershell
python main.py
```

## Build Windows EXE

```powershell
pip install -r requirements.txt
powershell -ExecutionPolicy Bypass -File .\build_exe.ps1
```

After build completes, two versions are available:

**Multi-file version** (faster startup):
```powershell
.\dist\SteamGameBatchRecover\SteamGameBatchRecover.exe
```
- Requires folder structure: `SteamGameBatchRecover/` + `_internal/`
- First run: ~1-2 seconds startup time
- Best for: development, testing on same machine

**Single-file version** (fully portable):
```powershell
.\dist\SteamGameBatchRecover-standalone.exe
```
- Completely self-contained, no dependencies
- First run: ~3-5 seconds (unpacks temporary files)
- Subsequent runs: ~1-2 seconds
- Best for: distribution, testing on different machines

Packaging notes:
- Build output folders are `build/` and `dist/`.
- If SmartScreen appears on another machine, choose More info > Run anyway for internal testing.

## Build EXE via GitHub Actions

This repository includes workflow [build-windows-exe.yml](.github/workflows/build-windows-exe.yml).

Trigger options:
- Manual trigger: Actions > Build Windows EXE > Run workflow
- Tag trigger: push a tag like `v1.0.0`

After workflow completes, two artifacts are available from the workflow run page:
- `SteamGameBatchRecover-multifile`: Faster startup version (requires _internal folder)
- `SteamGameBatchRecover-standalone`: Single EXE, fully portable

## Local EXE Build vs GitHub Actions EXE Artifact

- Build environment:
  - Local: uses your current machine and Python setup.
  - Actions: uses clean `windows-latest` runner with Python 3.12.
- Reproducibility:
  - Local: can vary by your installed tools and system state.
  - Actions: more consistent across runs due to fixed CI steps.
- Speed and convenience:
  - Local: faster for quick iteration and immediate testing.
  - Actions: better for sharing test artifacts with other devices/users.
- Trust and security prompts:
  - Local: usually fewer unknown publisher prompts on your own machine.
  - Actions: downloaded exe may trigger SmartScreen on first run.
- Typical use case:
  - Local: development and debugging.
  - Actions: release candidate packaging and cross-device verification.

## Workflow

1. Choose the UI language (`zh-TW`, `zh-CN`, or `en`).
2. Choose a source folder that contains your backup files (including external drives).
3. Click `Scan`.
4. Select one or more Steam backup package entries.
5. Click `Launch Steam Restore Flow`.
6. In Steam, go to `Steam -> Restore Game Backup...` and browse to one selected path.

## Notes

- Backup files can stay on external storage.
- Steam itself decides final install location (you can use Steam defaults).
- Runtime does not require extra packages beyond Python standard library.
- Packaging requires `PyInstaller` (already listed in `requirements.txt`).
