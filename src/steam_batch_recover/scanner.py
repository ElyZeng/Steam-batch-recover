from __future__ import annotations

import json
import os
import re
from pathlib import Path

from .models import BackupKind, GameBackup

APP_ID_PATTERN = re.compile(r"\b(\d{3,})\b")
KV_PATTERN = re.compile(r'"(?P<key>[^"]+)"\s+"(?P<value>[^"]+)"')
TITLE_KEYS = ("name", "appname", "title", "gamename", "game")
INSTALL_DIR_KEYS = ("installdir", "install_dir")
SECTION_KEY_PATTERN = re.compile(r'^\s*"(?P<key>\d+)"\s*$')
PATH_LINE_PATTERN = re.compile(r'^\s*"path"\s+"(?P<path>[^"]+)"')


def scan_installed_games() -> list[GameBackup]:
    steam_root = find_steam_install_root()
    if steam_root is None:
        raise FileNotFoundError("Steam install path was not found on this machine.")

    backups: list[GameBackup] = []
    seen_keys: set[tuple[str, str]] = set()
    for library_root in find_steam_library_roots(steam_root):
        steamapps_dir = library_root / "steamapps"
        if not steamapps_dir.exists():
            continue

        for manifest_path in sorted(steamapps_dir.glob("appmanifest_*.acf")):
            game = _scan_installed_game(manifest_path, library_root)
            if game is None:
                continue
            key = (game.app_id, str(game.source_path))
            if key in seen_keys:
                continue
            backups.append(game)
            seen_keys.add(key)

    backups.sort(key=lambda item: (item.name.lower(), item.app_id))
    return backups


def scan_repository_backups(repository_root: Path) -> list[GameBackup]:
    if not repository_root.exists() or not repository_root.is_dir():
        raise FileNotFoundError(f"Repository path does not exist: {repository_root}")

    index_path = repository_root / "manifest.json"
    entries: list[dict[str, object]] = []
    if index_path.exists():
        try:
            payload = json.loads(index_path.read_text(encoding="utf-8"))
            entries = list(payload.get("entries", []))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"Failed to read repository manifest: {index_path}") from exc
    else:
        for backup_manifest in sorted(repository_root.glob("entries/*/backup_manifest.json")):
            try:
                entries.append(json.loads(backup_manifest.read_text(encoding="utf-8")))
            except (OSError, json.JSONDecodeError):
                continue

    backups: list[GameBackup] = []
    for entry in entries:
        backup = _scan_repository_entry(repository_root, entry)
        if backup is not None:
            backups.append(backup)

    backups.sort(key=lambda item: (item.name.lower(), item.app_id))
    return backups


def find_steam_executable() -> Path | None:
    registry_paths = [
        ("HKEY_CURRENT_USER", r"Software\\Valve\\Steam", "SteamExe"),
        ("HKEY_LOCAL_MACHINE", r"SOFTWARE\\WOW6432Node\\Valve\\Steam", "InstallPath"),
        ("HKEY_LOCAL_MACHINE", r"SOFTWARE\\Valve\\Steam", "InstallPath"),
    ]

    try:
        import winreg
    except ImportError:
        winreg = None  # type: ignore[assignment]

    if winreg is not None:
        hive_map = {
            "HKEY_CURRENT_USER": winreg.HKEY_CURRENT_USER,
            "HKEY_LOCAL_MACHINE": winreg.HKEY_LOCAL_MACHINE,
        }
        for hive_name, subkey, value_name in registry_paths:
            try:
                with winreg.OpenKey(hive_map[hive_name], subkey) as key:
                    value, _ = winreg.QueryValueEx(key, value_name)
            except OSError:
                continue
            candidate = Path(value)
            if candidate.name.lower() != "steam.exe":
                candidate = candidate / "Steam.exe"
            if candidate.exists():
                return candidate

    candidates = []
    for env_name in ("ProgramFiles(x86)", "ProgramFiles"):
        base = os.environ.get(env_name)
        if base:
            candidates.append(Path(base) / "Steam" / "Steam.exe")
    candidates.append(Path(r"C:\Program Files (x86)\Steam\Steam.exe"))
    candidates.append(Path(r"C:\Program Files\Steam\Steam.exe"))

    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def find_steam_install_root() -> Path | None:
    steam_executable = find_steam_executable()
    if steam_executable is not None:
        return steam_executable.parent
    return None


def find_steam_library_roots(steam_root: Path | None = None) -> list[Path]:
    root = steam_root or find_steam_install_root()
    if root is None:
        return []

    libraries = [root]
    libraryfolders_path = root / "steamapps" / "libraryfolders.vdf"
    if libraryfolders_path.exists():
        for library_path in _parse_libraryfolders(libraryfolders_path):
            if library_path not in libraries:
                libraries.append(library_path)
    return libraries


def _scan_installed_game(manifest_path: Path, library_root: Path) -> GameBackup | None:
    metadata = _parse_key_values(manifest_path.read_text(encoding="utf-8", errors="ignore"))
    raw_name = _pick_first(metadata, TITLE_KEYS) or manifest_path.stem
    app_id = _pick_app_id(metadata, [manifest_path.stem, raw_name])
    install_dir = _pick_first(metadata, INSTALL_DIR_KEYS) or raw_name

    game_folder = library_root / "steamapps" / "common" / install_dir
    if not game_folder.exists() or not game_folder.is_dir():
        return None

    required_bytes = manifest_path.stat().st_size + _directory_size(game_folder)
    return GameBackup(
        app_id=app_id,
        name=raw_name,
        kind=BackupKind.INSTALLED_GAME,
        source_path=game_folder,
        required_bytes=required_bytes,
        restore_subpath=install_dir,
        manifest_path=manifest_path,
        install_dir_name=install_dir,
        steam_library_path=library_root,
    )


def _scan_repository_entry(repository_root: Path, entry: dict[str, object]) -> GameBackup | None:
    entry_folder_rel = str(entry.get("entry_folder", "")).strip()
    install_dir = str(entry.get("install_dir_name", "")).strip()
    app_id = str(entry.get("app_id", "unknown")).strip() or "unknown"
    name = str(entry.get("name", app_id)).strip() or app_id
    manifest_rel = str(entry.get("manifest_path", "")).strip()
    game_rel = str(entry.get("game_path", "")).strip()
    required_bytes = int(entry.get("required_bytes", 0) or 0)

    if not entry_folder_rel or not install_dir or not manifest_rel or not game_rel:
        return None

    entry_folder = repository_root / entry_folder_rel
    manifest_path = repository_root / manifest_rel
    game_folder = repository_root / game_rel
    if not entry_folder.exists() or not manifest_path.exists() or not game_folder.exists():
        return None

    return GameBackup(
        app_id=app_id,
        name=name,
        kind=BackupKind.REPOSITORY_BACKUP,
        source_path=game_folder,
        required_bytes=required_bytes or _directory_size(game_folder),
        restore_subpath=install_dir,
        manifest_path=manifest_path,
        install_dir_name=install_dir,
        backup_folder=entry_folder,
    )


def _parse_libraryfolders(path: Path) -> list[Path]:
    libraries: list[Path] = []
    current_section: str | None = None
    for raw_line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw_line.strip()
        section_match = SECTION_KEY_PATTERN.match(line)
        if section_match:
            current_section = section_match.group("key")
            continue
        if line == "}":
            current_section = None
            continue
        if current_section is None:
            continue
        path_match = PATH_LINE_PATTERN.match(line)
        if not path_match:
            continue
        library_path = Path(path_match.group("path").replace("\\\\", "\\"))
        if library_path.exists():
            libraries.append(library_path)
    return libraries


def _parse_key_values(text: str) -> dict[str, str]:
    pairs = {}
    for match in KV_PATTERN.finditer(text):
        pairs[match.group("key").strip().lower()] = match.group("value").strip()
    if not pairs:
        for line in text.splitlines():
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            pairs[key.strip().lower()] = value.strip().strip('"')
    return pairs


def _pick_first(metadata: dict[str, str], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = metadata.get(key)
        if value:
            return value
    return None


def _pick_app_id(metadata: dict[str, str], fallbacks: list[str]) -> str:
    for key in ("appid", "app_id"):
        value = metadata.get(key)
        if value:
            return value
    for value in fallbacks:
        match = APP_ID_PATTERN.search(value)
        if match:
            return match.group(1)
    return "unknown"


def _directory_size(folder: Path) -> int:
    total = 0
    for current_root, _, file_names in os.walk(folder):
        for file_name in file_names:
            file_path = Path(current_root) / file_name
            try:
                total += file_path.stat().st_size
            except OSError:
                continue
    return total
