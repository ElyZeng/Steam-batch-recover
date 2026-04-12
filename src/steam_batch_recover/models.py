from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class BackupKind(str, Enum):
    LIBRARY_SNAPSHOT = "Library snapshot"
    STEAM_PACKAGE = "Steam backup package"


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

    @property
    def destination_hint(self) -> str:
        if self.kind is BackupKind.LIBRARY_SNAPSHOT:
            return f"steamapps/common/{self.install_dir_name or self.restore_subpath}"
        return self.restore_subpath
