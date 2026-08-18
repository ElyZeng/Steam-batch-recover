from __future__ import annotations

import json
import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Callable

from .models import BackupKind, GameBackup

ProgressCallback = Callable[[str], None]
SAFE_NAME_PATTERN = re.compile(r"[^A-Za-z0-9._ -]+")
MAX_REPOSITORY_NAME_LENGTH = 80


def get_free_space_bytes(path: Path) -> int:
    target = path if path.exists() else path.parent
    if not target.exists():
        target = Path(path.anchor) if path.anchor else Path.cwd()
    return shutil.disk_usage(target).free


def get_repository_name(repository_root: Path) -> str:
    manifest_path = repository_root / "manifest.json"
    fallback_name = repository_root.name or str(repository_root)
    if not manifest_path.exists():
        return fallback_name

    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return fallback_name

    if not isinstance(payload, dict):
        return fallback_name
    repository_name = payload.get("repository_name")
    if not isinstance(repository_name, str):
        return fallback_name
    return repository_name.strip() or fallback_name


def set_repository_name(repository_root: Path, repository_name: str) -> str:
    normalized_name = " ".join(repository_name.split())
    if not normalized_name:
        raise ValueError("Repository name cannot be empty.")
    if len(normalized_name) > MAX_REPOSITORY_NAME_LENGTH:
        raise ValueError(f"Repository name cannot exceed {MAX_REPOSITORY_NAME_LENGTH} characters.")

    repository_root.mkdir(parents=True, exist_ok=True)
    manifest_path = repository_root / "manifest.json"
    payload: dict[str, object] = {"version": 1, "entries": []}
    if manifest_path.exists():
        try:
            existing_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"Failed to read repository manifest: {manifest_path}") from exc
        if not isinstance(existing_payload, dict):
            raise ValueError(f"Repository manifest must contain a JSON object: {manifest_path}")
        payload = existing_payload

    payload["repository_name"] = normalized_name
    payload.setdefault("version", 1)
    payload.setdefault("entries", [])
    manifest_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return normalized_name


def backup_games_to_repository(
    games: list[GameBackup],
    repository_root: Path,
    overwrite: bool,
    on_progress: ProgressCallback | None = None,
) -> None:
    repository_root.mkdir(parents=True, exist_ok=True)
    entries_dir = repository_root / "entries"
    entries_dir.mkdir(parents=True, exist_ok=True)

    valid_games = [game for game in games if game.kind is BackupKind.INSTALLED_GAME]
    total_games = len(valid_games)
    manifest_entries: list[dict[str, object]] = []
    completed_games = 0
    for game in valid_games:
        if game.manifest_path is None:
            raise ValueError(f"Missing appmanifest for {game.name}")

        backup_time = datetime.now().astimezone().isoformat(timespec="seconds")

        folder_name = f"{game.app_id}_{_safe_name(game.name)}"
        entry_dir = entries_dir / folder_name
        game_target = entry_dir / "common" / (game.install_dir_name or game.restore_subpath)
        manifest_target = entry_dir / game.manifest_path.name

        _emit(on_progress, f"Backing up {game.name} ({game.app_id})")
        _copy_path(game.source_path, game_target, overwrite, on_progress)
        _copy_file(game.manifest_path, manifest_target, overwrite, on_progress)

        backup_manifest = {
            "app_id": game.app_id,
            "name": game.name,
            "install_dir_name": game.install_dir_name or game.restore_subpath,
            "required_bytes": game.required_bytes,
            "entry_folder": str(entry_dir.relative_to(repository_root)).replace("\\", "/"),
            "game_path": str(game_target.relative_to(repository_root)).replace("\\", "/"),
            "manifest_path": str(manifest_target.relative_to(repository_root)).replace("\\", "/"),
            "source_library_path": str(game.steam_library_path) if game.steam_library_path else "",
            "backup_time": backup_time,
        }
        (entry_dir / "backup_manifest.json").write_text(json.dumps(backup_manifest, indent=2), encoding="utf-8")
        manifest_entries.append(backup_manifest)

        completed_games += 1
        _emit_progress(on_progress, completed_games, total_games, "backup", game.name)

    _write_repository_manifest(repository_root, manifest_entries)


def restore_repository_backups(
    backups: list[GameBackup],
    steam_library_root: Path,
    overwrite: bool,
    on_progress: ProgressCallback | None = None,
) -> None:
    steamapps_dir = steam_library_root / "steamapps"
    common_dir = steamapps_dir / "common"
    common_dir.mkdir(parents=True, exist_ok=True)

    valid_backups = [backup for backup in backups if backup.kind is BackupKind.REPOSITORY_BACKUP]
    total_backups = len(valid_backups)
    completed_backups = 0

    for backup in valid_backups:
        if backup.manifest_path is None:
            raise ValueError(f"Missing manifest for {backup.name}")

        game_destination = common_dir / (backup.install_dir_name or backup.restore_subpath)
        manifest_destination = steamapps_dir / backup.manifest_path.name
        _emit(on_progress, f"Restoring {backup.name} ({backup.app_id})")
        _copy_path(backup.source_path, game_destination, overwrite, on_progress)
        _copy_file(backup.manifest_path, manifest_destination, overwrite, on_progress)

        completed_backups += 1
        _emit_progress(on_progress, completed_backups, total_backups, "restore", backup.name)


def _write_repository_manifest(repository_root: Path, new_entries: list[dict[str, object]]) -> None:
    manifest_path = repository_root / "manifest.json"
    existing_entries: dict[str, dict[str, object]] = {}
    repository_name: str | None = None
    if manifest_path.exists():
        try:
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
            for entry in payload.get("entries", []):
                key = f"{entry.get('app_id', '')}:{entry.get('entry_folder', '')}"
                existing_entries[key] = entry
            stored_name = payload.get("repository_name")
            if isinstance(stored_name, str) and stored_name.strip():
                repository_name = stored_name.strip()
        except (OSError, json.JSONDecodeError):
            existing_entries = {}

    for entry in new_entries:
        key = f"{entry.get('app_id', '')}:{entry.get('entry_folder', '')}"
        existing_entries[key] = entry

    payload = {
        "version": 1,
        "entries": sorted(existing_entries.values(), key=lambda item: (str(item.get("name", "")).lower(), str(item.get("app_id", "")))),
    }
    if repository_name is not None:
        payload["repository_name"] = repository_name
    manifest_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _copy_path(
    source: Path,
    destination: Path,
    overwrite: bool,
    on_progress: ProgressCallback | None,
) -> None:
    if source.is_dir():
        for current_root, dir_names, file_names in os.walk(source):
            current_path = Path(current_root)
            relative_root = current_path.relative_to(source)
            destination_dir = destination / relative_root
            destination_dir.mkdir(parents=True, exist_ok=True)
            for dir_name in dir_names:
                (destination_dir / dir_name).mkdir(parents=True, exist_ok=True)
            for file_name in file_names:
                _copy_file(current_path / file_name, destination_dir / file_name, overwrite, on_progress)
        return

    _copy_file(source, destination, overwrite, on_progress)


def _copy_file(
    source: Path,
    destination: Path,
    overwrite: bool,
    on_progress: ProgressCallback | None,
) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and not overwrite:
        _emit(on_progress, f"Skipped existing file: {destination}")
        return

    shutil.copy2(source, destination)
    _emit(on_progress, f"Copied: {destination}")


def _safe_name(value: str) -> str:
    cleaned = SAFE_NAME_PATTERN.sub("_", value).strip()
    return cleaned or "steam_game"


def _emit(callback: ProgressCallback | None, message: str) -> None:
    if callback:
        callback(message)


def _emit_progress(
    callback: ProgressCallback | None,
    current: int,
    total: int,
    operation: str,
    item_name: str,
) -> None:
    if not callback:
        return
    safe_total = max(1, total)
    callback(f"__PROGRESS__|{current}|{safe_total}|{operation}|{item_name}")
