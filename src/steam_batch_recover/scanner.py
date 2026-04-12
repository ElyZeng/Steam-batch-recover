from __future__ import annotations

import os
import re
from pathlib import Path

from .models import BackupKind, GameBackup

APP_ID_PATTERN = re.compile(r"\b(\d{3,})\b")
KV_PATTERN = re.compile(r'"(?P<key>[^"]+)"\s+"(?P<value>[^"]+)"')
TITLE_KEYS = ("name", "appname", "title", "gamename", "game")
INSTALL_DIR_KEYS = ("installdir", "install_dir")


def scan_backups(root: Path) -> list[GameBackup]:
    if not root.exists() or not root.is_dir():
        raise FileNotFoundError(f"Source path does not exist: {root}")

    backups: list[GameBackup] = []
    seen_keys: set[tuple[str, str]] = set()

    for current_root, dir_names, file_names in os.walk(root):
        current_path = Path(current_root)
        lower_names = {name.lower() for name in file_names}

        if "sku.sis" in lower_names:
            package = _scan_steam_package(current_path)
            if package:
                key = (package.app_id, str(package.source_path))
                if key not in seen_keys:
                    backups.append(package)
                    seen_keys.add(key)
                dir_names[:] = []
                continue

        manifest_names = [name for name in file_names if name.lower().startswith("appmanifest_") and name.lower().endswith(".acf")]
        for manifest_name in manifest_names:
            manifest_path = current_path / manifest_name
            snapshot = _scan_library_snapshot(manifest_path)
            if snapshot:
                key = (snapshot.app_id, str(snapshot.source_path))
                if key not in seen_keys:
                    backups.append(snapshot)
                    seen_keys.add(key)

    backups.sort(key=lambda item: (item.name.lower(), item.app_id))
    return backups


def _scan_steam_package(folder: Path) -> GameBackup | None:
    sku_path = folder / "sku.sis"
    metadata = _parse_key_values(sku_path.read_text(encoding="utf-8", errors="ignore"))
    all_files = [path for path in folder.iterdir() if path.is_file()]
    package_files = [path for path in all_files if path.suffix.lower() in {".csm", ".csd", ".sis"}]
    if not package_files:
        return None

    raw_name = _pick_first(metadata, TITLE_KEYS) or folder.name
    app_id = _pick_app_id(metadata, [folder.name, raw_name])
    required_bytes = sum(path.stat().st_size for path in package_files)
    restore_subpath = _safe_name(f"{raw_name}_{app_id}")

    return GameBackup(
        app_id=app_id,
        name=raw_name,
        kind=BackupKind.STEAM_PACKAGE,
        source_path=folder,
        required_bytes=required_bytes,
        restore_subpath=restore_subpath,
    )


def _scan_library_snapshot(manifest_path: Path) -> GameBackup | None:
    metadata = _parse_key_values(manifest_path.read_text(encoding="utf-8", errors="ignore"))
    raw_name = _pick_first(metadata, TITLE_KEYS) or manifest_path.stem
    app_id = _pick_app_id(metadata, [manifest_path.stem, raw_name])
    install_dir = _pick_first(metadata, INSTALL_DIR_KEYS) or raw_name

    candidate_roots = [manifest_path.parent.parent / "common", manifest_path.parent / "common", manifest_path.parent.parent, manifest_path.parent]
    game_folder = None
    for candidate_root in candidate_roots:
        candidate = candidate_root / install_dir
        if candidate.exists() and candidate.is_dir():
            game_folder = candidate
            break

    if game_folder is None:
        return None

    required_bytes = manifest_path.stat().st_size + _directory_size(game_folder)

    return GameBackup(
        app_id=app_id,
        name=raw_name,
        kind=BackupKind.LIBRARY_SNAPSHOT,
        source_path=game_folder,
        required_bytes=required_bytes,
        restore_subpath=install_dir,
        manifest_path=manifest_path,
        install_dir_name=install_dir,
    )


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


def _safe_name(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._ -]+", "_", value).strip()
    return cleaned or "steam_backup"
