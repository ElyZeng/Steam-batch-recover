# Steam Game Batch Recover

A Windows desktop tool for backing up installed Steam games into a portable repository and restoring them on another machine by reading repository manifest files.

## New Workflow

1. Detect installed Steam games from local Steam library folders.
2. Back up selected games to a repository path such as an external drive.
3. Write manifest files into that repository so another machine can discover what is available.
4. On another machine, scan the same repository and list restorable games.
5. Restore selected games into that machine's Steam library path.

## What The App Does

- Scans local Steam libraries by reading `appmanifest_*.acf` and matching installed game folders.
- Backs up selected installed games into a repository structure under `entries/`.
- Writes repository metadata into:
  - `manifest.json`
  - `entries/<app_id>_<name>/backup_manifest.json`
  - each manifest entry now includes `backup_time` so backup recency is visible on other machines
- Restores backed-up games by copying:
  - game files into `steamapps/common/<installdir>`
  - app manifests into `steamapps/appmanifest_<appid>.acf`

## Repository Layout

```text
<repository>/
  manifest.json
  entries/
    1091500_Cyberpunk 2077/
      backup_manifest.json
      appmanifest_1091500.acf
      common/
        Cyberpunk 2077/
          ...game files...
```

## Run

```powershell
python main.py
```

## UI Flow

### To create backups

1. Choose a backup repository path.
2. Click `Scan Installed Games`.
3. Select one or more installed games.
4. Click `Backup Selected`.

### To restore on another machine

1. Choose the same backup repository path.
2. Set the target Steam library path for that machine.
3. Click `Scan Backup Repository`.
4. Select one or more repository backups.
5. Click `Restore Selected`.

## Notes

- The repository path can be an external drive.
- The app checks free space before backup or restore and warns when space looks insufficient.
- The target restore path should be a Steam library root, not the `steamapps/common` folder itself.
- Steam may need a restart to refresh restored games after files and app manifests are copied.

## Build Windows EXE

```powershell
pip install -r requirements.txt
powershell -ExecutionPolicy Bypass -File .\build_exe.ps1
```

## Current Scope

This version no longer relies on Steam GUI automation for normal backup and restore flow. Existing Steam GUI automation files remain in the repository for prior experimentation, but the main app now uses the manifest-based repository architecture.
