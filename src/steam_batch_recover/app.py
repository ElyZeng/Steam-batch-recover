from __future__ import annotations

import os
import threading
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk

from .models import BackupKind, GameBackup
from .restorer import backup_games_to_repository, get_free_space_bytes, restore_repository_backups
from .scanner import find_steam_library_roots, scan_installed_games, scan_repository_backups


def run_app() -> None:
    app = SteamBatchRecoverApp()
    app.mainloop()


LOCALE_DATA = {
    "zh-TW": {
        "title": "Steam 遊戲備份與還原助手",
        "language": "語言",
        "repository": "備份倉庫路徑",
        "target_library": "還原目標 Steam Library",
        "browse": "瀏覽",
        "scan_installed": "掃描本機已安裝遊戲",
        "scan_repository": "掃描備份倉庫",
        "backup_selected": "備份選取項目",
        "restore_selected": "還原選取項目",
        "select_all": "全選",
        "clear_selection": "清除選取",
        "open_paths": "開啟選取資料夾",
        "copy_paths": "複製選取路徑",
        "status_ready": "就緒",
        "status_scanning": "掃描中...",
        "status_processing": "處理中...",
        "scan_complete": "掃描完成，找到 {count} 筆資料。",
        "backup_complete": "備份完成，共處理 {count} 筆。",
        "restore_complete": "還原完成，共處理 {count} 筆。",
        "processing_failed": "處理失敗: {error}",
        "missing_repository_title": "缺少備份倉庫路徑",
        "missing_repository": "請先選擇備份倉庫路徑。",
        "missing_target_title": "缺少還原目標",
        "missing_target": "請先選擇還原目標 Steam Library 路徑。",
        "no_selection_title": "尚未選取",
        "no_installed_selection": "請至少選擇一個本機已安裝遊戲來備份。",
        "no_repository_selection": "請至少選擇一個倉庫備份來還原。",
        "space_summary": "已選取大小: {size} | 目標剩餘空間: {free}",
        "type": "類型",
        "app_id": "App ID",
        "game": "遊戲",
        "size": "大小",
        "source_col": "來源",
        "no_scan": "尚未掃描",
        "detected_summary": "已偵測 {count} 筆 | 已選取 {selected}",
        "backup_kind_installed": "本機已安裝",
        "backup_kind_repository": "倉庫備份",
        "folder_dialog_repository": "選擇備份倉庫資料夾",
        "folder_dialog_target": "選擇目標 Steam Library",
        "copy_done": "已將 {count} 個路徑複製到剪貼簿。",
        "copy_fail": "複製到剪貼簿失敗。",
        "open_paths_done": "已嘗試開啟 {count} 個資料夾。",
        "free_space_warning": "目標空間不足。需要 {required}，目前剩餘 {free}。",
        "using_target_library": "目前目標還原路徑: {path}",
        "repository_manifest_hint": "備份倉庫將使用 manifest.json 與 entries/*/backup_manifest.json 管理。",
    },
    "zh-CN": {
        "title": "Steam 游戏备份与还原助手",
        "language": "语言",
        "repository": "备份仓库路径",
        "target_library": "还原目标 Steam Library",
        "browse": "浏览",
        "scan_installed": "扫描本机已安装游戏",
        "scan_repository": "扫描备份仓库",
        "backup_selected": "备份所选项目",
        "restore_selected": "还原所选项目",
        "select_all": "全选",
        "clear_selection": "清除选择",
        "open_paths": "打开所选文件夹",
        "copy_paths": "复制所选路径",
        "status_ready": "就绪",
        "status_scanning": "扫描中...",
        "status_processing": "处理中...",
        "scan_complete": "扫描完成，找到 {count} 条记录。",
        "backup_complete": "备份完成，共处理 {count} 项。",
        "restore_complete": "还原完成，共处理 {count} 项。",
        "processing_failed": "处理失败: {error}",
        "missing_repository_title": "缺少备份仓库路径",
        "missing_repository": "请先选择备份仓库路径。",
        "missing_target_title": "缺少还原目标",
        "missing_target": "请先选择还原目标 Steam Library 路径。",
        "no_selection_title": "尚未选择",
        "no_installed_selection": "请至少选择一个本机已安装游戏进行备份。",
        "no_repository_selection": "请至少选择一个仓库备份进行还原。",
        "space_summary": "已选大小: {size} | 目标剩余空间: {free}",
        "type": "类型",
        "app_id": "App ID",
        "game": "游戏",
        "size": "大小",
        "source_col": "来源",
        "no_scan": "尚未扫描",
        "detected_summary": "已检测 {count} 项 | 已选择 {selected}",
        "backup_kind_installed": "本机已安装",
        "backup_kind_repository": "仓库备份",
        "folder_dialog_repository": "选择备份仓库文件夹",
        "folder_dialog_target": "选择目标 Steam Library",
        "copy_done": "已将 {count} 个路径复制到剪贴板。",
        "copy_fail": "复制到剪贴板失败。",
        "open_paths_done": "已尝试打开 {count} 个文件夹。",
        "free_space_warning": "目标空间不足。需要 {required}，当前剩余 {free}。",
        "using_target_library": "当前目标还原路径: {path}",
        "repository_manifest_hint": "备份仓库会使用 manifest.json 与 entries/*/backup_manifest.json 进行管理。",
    },
    "en": {
        "title": "Steam Game Backup and Restore Assistant",
        "language": "Language",
        "repository": "Backup repository path",
        "target_library": "Target Steam library",
        "browse": "Browse",
        "scan_installed": "Scan Installed Games",
        "scan_repository": "Scan Backup Repository",
        "backup_selected": "Backup Selected",
        "restore_selected": "Restore Selected",
        "select_all": "Select All",
        "clear_selection": "Clear Selection",
        "open_paths": "Open Selected Folders",
        "copy_paths": "Copy Selected Paths",
        "status_ready": "Ready",
        "status_scanning": "Scanning...",
        "status_processing": "Processing...",
        "scan_complete": "Scan complete. Found {count} entries.",
        "backup_complete": "Backup complete. Processed {count} item(s).",
        "restore_complete": "Restore complete. Processed {count} item(s).",
        "processing_failed": "Operation failed: {error}",
        "missing_repository_title": "Missing repository path",
        "missing_repository": "Choose a backup repository path first.",
        "missing_target_title": "Missing target library",
        "missing_target": "Choose a target Steam library path first.",
        "no_selection_title": "No selection",
        "no_installed_selection": "Select at least one installed game to back up.",
        "no_repository_selection": "Select at least one repository backup to restore.",
        "space_summary": "Selected size: {size} | Free space at target: {free}",
        "type": "Type",
        "app_id": "App ID",
        "game": "Game",
        "size": "Size",
        "source_col": "Source",
        "no_scan": "No scan yet",
        "detected_summary": "Detected {count} entries | Selected {selected}",
        "backup_kind_installed": "Installed game",
        "backup_kind_repository": "Repository backup",
        "folder_dialog_repository": "Choose backup repository folder",
        "folder_dialog_target": "Choose target Steam library",
        "copy_done": "Copied {count} path(s) to clipboard.",
        "copy_fail": "Failed to copy paths to clipboard.",
        "open_paths_done": "Attempted to open {count} folder(s).",
        "free_space_warning": "Not enough free space. Need {required}, only {free} available.",
        "using_target_library": "Current restore target: {path}",
        "repository_manifest_hint": "The repository uses manifest.json and entries/*/backup_manifest.json.",
    },
}


class SteamBatchRecoverApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.geometry("1220x760")
        self.minsize(1040, 660)

        self.locale_var = tk.StringVar(value="zh-TW")
        self.repository_var = tk.StringVar()
        self.target_library_var = tk.StringVar(value=self._detect_default_target_library())
        self.status_var = tk.StringVar()
        self.summary_var = tk.StringVar()
        self.space_var = tk.StringVar()
        self.backups: list[GameBackup] = []
        self.current_view = "none"

        self._build_layout()
        self._apply_locale()
        if self.target_library_var.get().strip():
            self._append_log(self._t("using_target_library", path=self.target_library_var.get().strip()))

    def _build_layout(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        controls = ttk.Frame(self, padding=12)
        controls.grid(row=0, column=0, sticky="ew")
        controls.columnconfigure(1, weight=1)

        self.language_label = ttk.Label(controls)
        self.language_label.grid(row=0, column=0, sticky="w", pady=(0, 8))
        self.language_combo = ttk.Combobox(
            controls,
            textvariable=self.locale_var,
            state="readonly",
            values=("zh-TW", "zh-CN", "en"),
            width=14,
        )
        self.language_combo.grid(row=0, column=1, sticky="w", pady=(0, 8))
        self.language_combo.bind("<<ComboboxSelected>>", lambda _: self._apply_locale())

        self.repository_label = ttk.Label(controls)
        self.repository_label.grid(row=1, column=0, sticky="w", pady=(0, 8))
        ttk.Entry(controls, textvariable=self.repository_var).grid(row=1, column=1, sticky="ew", padx=8, pady=(0, 8))
        self.repository_browse_button = ttk.Button(controls, command=self._browse_repository)
        self.repository_browse_button.grid(row=1, column=2, sticky="ew", pady=(0, 8))

        self.target_label = ttk.Label(controls)
        self.target_label.grid(row=2, column=0, sticky="w", pady=(0, 8))
        ttk.Entry(controls, textvariable=self.target_library_var).grid(row=2, column=1, sticky="ew", padx=8, pady=(0, 8))
        self.target_browse_button = ttk.Button(controls, command=self._browse_target_library)
        self.target_browse_button.grid(row=2, column=2, sticky="ew", pady=(0, 8))

        actions = ttk.Frame(controls)
        actions.grid(row=3, column=0, columnspan=3, sticky="ew")

        self.scan_installed_button = ttk.Button(actions, command=self._scan_installed)
        self.scan_installed_button.grid(row=0, column=0, padx=(0, 8))
        self.scan_repository_button = ttk.Button(actions, command=self._scan_repository)
        self.scan_repository_button.grid(row=0, column=1, padx=(0, 8))
        self.select_all_button = ttk.Button(actions, command=self._select_all)
        self.select_all_button.grid(row=0, column=2, padx=(0, 8))
        self.clear_selection_button = ttk.Button(actions, command=self._clear_selection)
        self.clear_selection_button.grid(row=0, column=3, padx=(0, 8))
        self.backup_selected_button = ttk.Button(actions, command=self._backup_selected)
        self.backup_selected_button.grid(row=0, column=4, padx=(0, 8))
        self.restore_selected_button = ttk.Button(actions, command=self._restore_selected)
        self.restore_selected_button.grid(row=0, column=5, padx=(0, 8))
        self.copy_paths_button = ttk.Button(actions, command=self._copy_selected_paths)
        self.copy_paths_button.grid(row=0, column=6, padx=(0, 8))
        self.open_paths_button = ttk.Button(actions, command=self._open_selected_paths)
        self.open_paths_button.grid(row=0, column=7, padx=(0, 8))
        actions.columnconfigure(8, weight=1)
        ttk.Label(actions, textvariable=self.status_var).grid(row=0, column=8, sticky="e")

        center = ttk.Frame(self, padding=(12, 0, 12, 12))
        center.grid(row=1, column=0, sticky="nsew")
        center.columnconfigure(0, weight=3)
        center.columnconfigure(1, weight=2)
        center.rowconfigure(0, weight=1)

        columns = ("kind", "app_id", "name", "size", "source")
        self.tree = ttk.Treeview(center, columns=columns, show="headings", selectmode="extended")
        self.tree.grid(row=0, column=0, sticky="nsew")
        self.tree.column("kind", width=160, anchor="center")
        self.tree.column("app_id", width=90, anchor="center")
        self.tree.column("name", width=260)
        self.tree.column("size", width=120, anchor="e")
        self.tree.column("source", width=520)
        self.tree.bind("<<TreeviewSelect>>", lambda _: self._refresh_space_summary())

        scrollbar = ttk.Scrollbar(center, orient="vertical", command=self.tree.yview)
        scrollbar.grid(row=0, column=0, sticky="nse")
        self.tree.configure(yscrollcommand=scrollbar.set)

        log_panel = ttk.Frame(center)
        log_panel.grid(row=0, column=1, sticky="nsew", padx=(12, 0))
        log_panel.columnconfigure(0, weight=1)
        log_panel.rowconfigure(1, weight=1)

        ttk.Label(log_panel, textvariable=self.summary_var).grid(row=0, column=0, sticky="w", pady=(0, 8))
        ttk.Label(log_panel, textvariable=self.space_var).grid(row=1, column=0, sticky="nw")

        self.log_text = scrolledtext.ScrolledText(log_panel, height=20, wrap="word", state="disabled")
        self.log_text.grid(row=2, column=0, sticky="nsew", pady=(8, 0))

        self.progressbar = ttk.Progressbar(log_panel, mode="indeterminate")
        self.progressbar.grid(row=3, column=0, sticky="ew", pady=(8, 0))

    def _browse_repository(self) -> None:
        selected = filedialog.askdirectory(title=self._t("folder_dialog_repository"))
        if selected:
            self.repository_var.set(selected)

    def _browse_target_library(self) -> None:
        selected = filedialog.askdirectory(title=self._t("folder_dialog_target"))
        if selected:
            self.target_library_var.set(selected)
            self._append_log(self._t("using_target_library", path=selected))
            self._refresh_space_summary()

    def _scan_installed(self) -> None:
        self._set_busy(True, self._t("status_scanning"))
        threading.Thread(target=self._scan_installed_worker, daemon=True).start()

    def _scan_installed_worker(self) -> None:
        try:
            backups = scan_installed_games()
        except Exception as exc:  # noqa: BLE001
            self.after(0, lambda: self._operation_failed(exc))
            return
        self.after(0, lambda: self._scan_completed(backups, view="installed"))

    def _scan_repository(self) -> None:
        repository_text = self.repository_var.get().strip()
        if not repository_text:
            messagebox.showerror(self._t("missing_repository_title"), self._t("missing_repository"))
            return
        self._set_busy(True, self._t("status_scanning"))
        threading.Thread(target=self._scan_repository_worker, args=(Path(repository_text),), daemon=True).start()

    def _scan_repository_worker(self, repository_root: Path) -> None:
        try:
            backups = scan_repository_backups(repository_root)
        except Exception as exc:  # noqa: BLE001
            self.after(0, lambda: self._operation_failed(exc))
            return
        self.after(0, lambda: self._scan_completed(backups, view="repository"))

    def _scan_completed(self, backups: list[GameBackup], view: str) -> None:
        self.backups = backups
        self.current_view = view
        for item_id in self.tree.get_children():
            self.tree.delete(item_id)

        for backup in backups:
            self.tree.insert(
                "",
                "end",
                iid=self._row_id(backup),
                values=(
                    self._kind_label(backup.kind),
                    backup.app_id,
                    backup.name,
                    format_bytes(backup.required_bytes),
                    str(backup.source_path),
                ),
            )

        self.summary_var.set(self._t("detected_summary", count=len(backups), selected=0))
        self._refresh_space_summary()
        self._append_log(self._t("scan_complete", count=len(backups)))
        if view == "repository":
            self._append_log(self._t("repository_manifest_hint"))
        self._set_busy(False, self._t("status_ready"))

    def _backup_selected(self) -> None:
        repository_text = self.repository_var.get().strip()
        if not repository_text:
            messagebox.showerror(self._t("missing_repository_title"), self._t("missing_repository"))
            return
        selected = [item for item in self._selected_backups() if item.kind is BackupKind.INSTALLED_GAME]
        if not selected:
            messagebox.showinfo(self._t("no_selection_title"), self._t("no_installed_selection"))
            return
        repository_root = Path(repository_text)
        self._ensure_free_space(repository_root, selected)
        self._set_busy(True, self._t("status_processing"))
        threading.Thread(target=self._backup_worker, args=(selected, repository_root), daemon=True).start()

    def _backup_worker(self, selected: list[GameBackup], repository_root: Path) -> None:
        try:
            backup_games_to_repository(selected, repository_root, overwrite=True, on_progress=self._queue_log)
        except Exception as exc:  # noqa: BLE001
            self.after(0, lambda: self._operation_failed(exc))
            return
        self.after(0, lambda: self._operation_completed("backup", len(selected)))

    def _restore_selected(self) -> None:
        target_text = self.target_library_var.get().strip()
        if not target_text:
            messagebox.showerror(self._t("missing_target_title"), self._t("missing_target"))
            return
        selected = [item for item in self._selected_backups() if item.kind is BackupKind.REPOSITORY_BACKUP]
        if not selected:
            messagebox.showinfo(self._t("no_selection_title"), self._t("no_repository_selection"))
            return
        target_root = Path(target_text)
        self._ensure_free_space(target_root, selected)
        self._set_busy(True, self._t("status_processing"))
        threading.Thread(target=self._restore_worker, args=(selected, target_root), daemon=True).start()

    def _restore_worker(self, selected: list[GameBackup], target_root: Path) -> None:
        try:
            restore_repository_backups(selected, target_root, overwrite=True, on_progress=self._queue_log)
        except Exception as exc:  # noqa: BLE001
            self.after(0, lambda: self._operation_failed(exc))
            return
        self.after(0, lambda: self._operation_completed("restore", len(selected)))

    def _operation_completed(self, operation: str, count: int) -> None:
        self._set_busy(False, self._t("status_ready"))
        key = "backup_complete" if operation == "backup" else "restore_complete"
        self._append_log(self._t(key, count=count))
        if operation == "restore":
            self._append_log(self._t("using_target_library", path=self.target_library_var.get().strip()))
        messagebox.showinfo(self._t("title"), self._t(key, count=count))

    def _operation_failed(self, exc: Exception) -> None:
        self._set_busy(False, self._t("status_ready"))
        self._append_log(self._t("processing_failed", error=str(exc)))
        messagebox.showerror(self._t("title"), self._t("processing_failed", error=str(exc)))

    def _select_all(self) -> None:
        self.tree.selection_set(self.tree.get_children())
        self._refresh_space_summary()

    def _clear_selection(self) -> None:
        self.tree.selection_remove(self.tree.selection())
        self._refresh_space_summary()

    def _selected_backups(self) -> list[GameBackup]:
        selected_ids = set(self.tree.selection())
        return [backup for backup in self.backups if self._row_id(backup) in selected_ids]

    def _copy_selected_paths(self) -> None:
        selected = self._selected_backups()
        if not selected:
            messagebox.showinfo(self._t("no_selection_title"), self._t("no_installed_selection"))
            return
        try:
            self.clipboard_clear()
            self.clipboard_append("\n".join(str(item.source_path) for item in selected))
            self.update_idletasks()
        except tk.TclError:
            messagebox.showerror(self._t("title"), self._t("copy_fail"))
            return
        self._append_log(self._t("copy_done", count=len(selected)))

    def _open_selected_paths(self) -> None:
        selected = self._selected_backups()
        if not selected:
            messagebox.showinfo(self._t("no_selection_title"), self._t("no_installed_selection"))
            return
        opened = 0
        for item in selected[:10]:
            try:
                os.startfile(str(item.source_path))
                opened += 1
            except OSError:
                continue
        self._append_log(self._t("open_paths_done", count=opened))

    def _ensure_free_space(self, target_path: Path, selected: list[GameBackup]) -> None:
        required = sum(item.required_bytes for item in selected)
        free = get_free_space_bytes(target_path)
        if required > free:
            messagebox.showwarning(
                self._t("title"),
                self._t("free_space_warning", required=format_bytes(required), free=format_bytes(free)),
            )

    def _queue_log(self, message: str) -> None:
        self.after(0, lambda: self._append_log(message))

    def _append_log(self, message: str) -> None:
        timestamped = f"[{datetime.now().strftime('%H:%M:%S')}] {message}"
        self.log_text.configure(state="normal")
        self.log_text.insert("end", timestamped + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _refresh_space_summary(self) -> None:
        selected = self._selected_backups()
        required_bytes = sum(item.required_bytes for item in selected)
        free_target = self.repository_var.get().strip()
        if any(item.kind is BackupKind.REPOSITORY_BACKUP for item in selected):
            free_target = self.target_library_var.get().strip()
        free_bytes = get_free_space_bytes(Path(free_target)) if free_target else 0
        self.space_var.set(self._t("space_summary", size=format_bytes(required_bytes), free=format_bytes(free_bytes)))
        if self.backups:
            self.summary_var.set(self._t("detected_summary", count=len(self.backups), selected=len(selected)))
        else:
            self.summary_var.set(self._t("no_scan"))

    def _kind_label(self, kind: BackupKind) -> str:
        if kind is BackupKind.INSTALLED_GAME:
            return self._t("backup_kind_installed")
        return self._t("backup_kind_repository")

    def _set_busy(self, busy: bool, status: str) -> None:
        self.status_var.set(status)
        if busy:
            self.progressbar.start(10)
        else:
            self.progressbar.stop()

    def _t(self, key: str, **kwargs: object) -> str:
        template = LOCALE_DATA[self.locale_var.get()][key]
        if kwargs:
            return template.format(**kwargs)
        return template

    def _apply_locale(self) -> None:
        self.title(self._t("title"))
        self.language_label.configure(text=self._t("language"))
        self.repository_label.configure(text=self._t("repository"))
        self.target_label.configure(text=self._t("target_library"))
        self.repository_browse_button.configure(text=self._t("browse"))
        self.target_browse_button.configure(text=self._t("browse"))
        self.scan_installed_button.configure(text=self._t("scan_installed"))
        self.scan_repository_button.configure(text=self._t("scan_repository"))
        self.select_all_button.configure(text=self._t("select_all"))
        self.clear_selection_button.configure(text=self._t("clear_selection"))
        self.backup_selected_button.configure(text=self._t("backup_selected"))
        self.restore_selected_button.configure(text=self._t("restore_selected"))
        self.copy_paths_button.configure(text=self._t("copy_paths"))
        self.open_paths_button.configure(text=self._t("open_paths"))
        self.tree.heading("kind", text=self._t("type"))
        self.tree.heading("app_id", text=self._t("app_id"))
        self.tree.heading("name", text=self._t("game"))
        self.tree.heading("size", text=self._t("size"))
        self.tree.heading("source", text=self._t("source_col"))
        self.status_var.set(self._t("status_ready"))
        if not self.backups:
            self.summary_var.set(self._t("no_scan"))
            self.space_var.set(self._t("space_summary", size="0 B", free="0 B"))
        else:
            self._refresh_space_summary()
            selected_ids = set(self.tree.selection())
            for item_id in self.tree.get_children():
                parts = item_id.split(":", 2)
                app_id = parts[0] if len(parts) > 0 else ""
                source = parts[2] if len(parts) > 2 else ""
                backup = next((b for b in self.backups if b.app_id == app_id and str(b.source_path) == source), None)
                if backup is None:
                    continue
                self.tree.item(
                    item_id,
                    values=(
                        self._kind_label(backup.kind),
                        backup.app_id,
                        backup.name,
                        format_bytes(backup.required_bytes),
                        str(backup.source_path),
                    ),
                )
            self.tree.selection_set(list(selected_ids))

    def _detect_default_target_library(self) -> str:
        libraries = find_steam_library_roots()
        if not libraries:
            return ""
        return str(libraries[0])

    @staticmethod
    def _row_id(backup: GameBackup) -> str:
        return f"{backup.app_id}:{backup.kind.value}:{backup.source_path}"


def format_bytes(size: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    value = float(size)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(value)} {unit}"
            return f"{value:.2f} {unit}"
        value /= 1024
    return f"{value:.2f} PB"
