# Steam Batch Recover Skill

## Scope
This skill captures stable development logic for the Steam Batch Recover desktop app and should be treated as the default implementation guide for future changes.

## Core Product Rules
- Keep two data modes separate:
  - Installed mode: scan local Steam libraries and operate on installed games.
  - Repository mode: scan backup repository and operate on repository backups.
- Backup and restore actions must be mutually exclusive by mode:
  - Installed mode: Backup enabled, Restore disabled.
  - Repository mode: Restore enabled, Backup disabled.
  - Busy state: both disabled.
- Preserve simple click toggle selection behavior in TreeView (no Ctrl required).

## Scan Caching Rules
- Cache installed scan results in memory.
- Cache repository scan results by repository path in memory.
- Switching between modes should reuse cache and avoid rescanning.
- Invalidate cache when data can change:
  - After backup completes: clear repository cache.
  - After restore completes: clear installed cache.

## Window and Layout Rules
- Use Windows work area (exclude taskbar) for geometry decisions.
- Initial placement should be work-area aware and centered.
- Maximize should fill work area, not full physical screen.
- Dragging should clamp window inside work area and support edge snap.
- Keep content area usable on lower resolutions:
  - Avoid bottom overflow beyond taskbar.
  - Ensure TreeView remains operable with small item counts.

## Styling and UX Rules
- Default language is English.
- Disabled button text must stay readable on dark theme.
- Keep backup and restore buttons grouped together.

## CI and Build Rules
- Workflow conditions must avoid unsupported direct `secrets.*` usage in `if` contexts where parsing can fail.
- Prefer env-based checks for optional signing input.
- Run build script with explicit execution policy bypass in CI:
  - `powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File .\\build_exe.ps1`
- Keep PyInstaller build behavior aligned between local and CI environments.

## Change Safety Checklist
- Verify app startup after UI/geometry changes.
- Check diagnostics for `src/steam_batch_recover/app.py` after edits.
- Commit only intended files; do not include unrelated generated/debug artifacts.
- Update changelog entry when behavior or CI logic changes.
