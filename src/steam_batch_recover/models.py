from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class BackupKind(str, Enum):
    INSTALLED_GAME = "Installed game"
    REPOSITORY_BACKUP = "Repository backup"


@dataclass(slots=True)
class GameBackup:
    app_id: str
    name: str
    kind: BackupKind
    source_path: Path
    required_bytes: int
    restore_subpath: str
    manifest_path: Path | None = None
    install_dir_name: str | None = None
    steam_library_path: Path | None = None
    backup_folder: Path | None = None
    backup_time: str | None = None
    last_updated_time: str | None = None

    @property
    def destination_hint(self) -> str:
        return f"steamapps/common/{self.install_dir_name or self.restore_subpath}"
