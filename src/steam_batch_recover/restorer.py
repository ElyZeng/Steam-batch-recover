from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Callable

from .models import BackupKind, GameBackup

ProgressCallback = Callable[[str], None]


def get_free_space_bytes(path: Path) -> int:
    target = path if path.exists() else path.parent
    if not target.exists():
        target = Path(path.anchor) if path.anchor else Path.cwd()
    return shutil.disk_usage(target).free


def restore_backups(
    backups: list[GameBackup],
    destination_root: Path,
    overwrite: bool,
    on_progress: ProgressCallback | None = None,
) -> None:
    destination_root.mkdir(parents=True, exist_ok=True)

    for backup in backups:
        _emit(on_progress, f"Processing {backup.name} ({backup.app_id})")
        if backup.kind is BackupKind.LIBRARY_SNAPSHOT:
            _restore_library_snapshot(backup, destination_root, overwrite, on_progress)
        else:
            _stage_steam_package(backup, destination_root, overwrite, on_progress)


def _restore_library_snapshot(
    backup: GameBackup,
    destination_root: Path,
    overwrite: bool,
    on_progress: ProgressCallback | None,
) -> None:
    steamapps_dir = destination_root / "steamapps"
    common_dir = steamapps_dir / "common"
    common_dir.mkdir(parents=True, exist_ok=True)

    if backup.manifest_path is None:
        raise ValueError(f"Missing manifest for {backup.name}")

    game_destination = common_dir / (backup.install_dir_name or backup.restore_subpath)
    manifest_destination = steamapps_dir / backup.manifest_path.name

    _copy_path(backup.source_path, game_destination, overwrite, on_progress)
    _copy_file(backup.manifest_path, manifest_destination, overwrite, on_progress)


def _stage_steam_package(
    backup: GameBackup,
    destination_root: Path,
    overwrite: bool,
    on_progress: ProgressCallback | None,
) -> None:
    package_destination = destination_root / backup.restore_subpath
    _copy_path(backup.source_path, package_destination, overwrite, on_progress)


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


def _emit(callback: ProgressCallback | None, message: str) -> None:
    if callback:
        callback(message)
