# Steam Game Batch Recover

A small Windows-friendly desktop tool that scans a folder for Steam backup assets, lets you select multiple games, estimates required disk space, and restores or stages them in batch.

## What It Supports

- Steam library snapshot backups:
  - Detects `appmanifest_*.acf` files and matching game folders.
  - Restores them directly into a Steam library folder.
- Steam backup packages created by Steam Backup/Restore:
  - Detects `sku.sis` plus `*.csd` and `*.csm` files.
  - Stages the selected packages into a destination folder so Steam can import them from there.

## Important Limitation

Steam does not expose a stable public restore API for official backup packages. For those backups, this tool copies the selected package files into a staging folder and verifies free space, but the final import still needs to be completed through Steam's restore flow.

## Run

```powershell
python main.py
```

## Build Windows EXE

```powershell
pip install -r requirements.txt
powershell -ExecutionPolicy Bypass -File .\build_exe.ps1
```

After build completes, run:

```powershell
.\dist\SteamGameBatchRecover\SteamGameBatchRecover.exe
```

Packaging notes:
- The generated EXE is for Windows only.
- Build output folders are `build/` and `dist/`.
- If SmartScreen appears on another machine, choose More info > Run anyway for internal testing.

## Build EXE via GitHub Actions

This repository includes workflow [build-windows-exe.yml](.github/workflows/build-windows-exe.yml).

Trigger options:
- Manual trigger: Actions > Build Windows EXE > Run workflow
- Tag trigger: push a tag like `v1.0.0`

After workflow completes, download artifact `SteamGameBatchRecover-windows-exe` from the workflow run page.

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

1. Choose a source folder that contains your backup files.
2. Choose a destination path:
   - For library snapshots, use the Steam library root.
   - For Steam backup packages, use any folder where you want to stage the restore sources.
3. Click `Scan`.
4. Select one or more detected games.
5. Review required space and free space.
6. Click `Restore Selected`.

## Notes

- The app checks free space on the destination drive before copying.
- Existing files are skipped by default unless `Overwrite existing files` is enabled.
- Runtime does not require extra packages beyond Python standard library.
- Packaging requires `PyInstaller` (already listed in `requirements.txt`).
