from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import threading
import traceback
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk

from .models import BackupKind, GameBackup
from .scanner import scan_backups
from .steam_gui_automator import SteamGuiAutomationError, SteamGuiAutomator


def run_app() -> None:
    app = SteamBatchRecoverApp()
    app.mainloop()


LOCALE_DATA = {
    "zh-TW": {
        "title": "Steam 批次還原助手",
        "language": "語言",
        "source": "備份來源路徑",
        "browse": "瀏覽",
        "scan": "掃描",
        "select_all": "全選",
        "clear_selection": "清除選取",
        "steam_restore": "喚起 Steam 還原流程",
        "steam_restore_from_wizard": "從已開啟精靈繼續",
        "steam_restore_running": "Steam 自動還原中...",
        "steam_restore_done": "Steam 自動還原批次已完成。",
        "steam_restore_failed": "Steam 自動還原失敗: {error}",
        "steam_restore_started": "開始 Steam GUI 批次還原，共 {count} 筆。",
        "steam_restore_started_from_wizard": "從已開啟的 Steam 還原精靈接手，共 {count} 筆。",
        "lang_template_fallback": "目前僅內建英文模板，自動化將使用英文畫面辨識。",
        "copy_paths": "複製選取路徑",
        "open_paths": "開啟選取資料夾",
        "open_debug_folder": "開啟除錯資料夾",
        "open_debug_console": "開啟除錯視窗",
        "status_ready": "就緒",
        "status_scanning": "掃描中...",
        "status_scan_failed": "掃描失敗",
        "type": "類型",
        "app_id": "App ID",
        "game": "遊戲",
        "size": "備份大小",
        "source_col": "來源",
        "no_scan": "尚未掃描",
        "detected_summary": "已偵測 {count} 個備份 | 已選取 {selected}",
        "size_summary": "已選取大小估算: {size}",
        "missing_source_title": "缺少來源路徑",
        "missing_source": "請先選擇備份來源路徑。",
        "scan_failed_title": "掃描失敗",
        "scan_complete": "掃描完成，找到 {count} 筆備份資料。",
        "no_selection_title": "尚未選取",
        "no_selection": "請至少選擇一個 Steam 備份項目。",
        "no_steam_backup": "目前選取項目沒有 Steam 內建備份格式 (sku.sis / .csd / .csm)。",
        "copy_done": "已將 {count} 個路徑複製到剪貼簿。",
        "copy_fail": "複製到剪貼簿失敗。",
        "open_paths_done": "已嘗試開啟 {count} 個資料夾。",
        "steam_not_found_title": "找不到 Steam",
        "steam_not_found": "找不到 Steam.exe，請先安裝或啟動 Steam。",
        "steam_launch_fail": "無法啟動 Steam: {error}",
        "steam_guide_title": "Steam 還原操作指引",
        "steam_guide": "已嘗試啟動 Steam。\n\n請在 Steam 依序操作:\n1. 左上角 Steam -> 還原遊戲備份\n2. 按『瀏覽』並選擇下列備份路徑之一\n3. 使用 Steam 預設安裝路徑完成還原\n\n可還原路徑:\n{paths}",
        "backup_kind_snapshot": "資料庫快照",
        "backup_kind_package": "Steam 備份包",
        "folder_dialog": "選擇備份來源資料夾",
        "debug_console_title": "除錯主控台",
        "debug_folder_hint": "除錯輸出路徑: {path}",
    },
    "zh-CN": {
        "title": "Steam 批量还原助手",
        "language": "语言",
        "source": "备份来源路径",
        "browse": "浏览",
        "scan": "扫描",
        "select_all": "全选",
        "clear_selection": "清除选择",
        "steam_restore": "唤起 Steam 还原流程",
        "steam_restore_from_wizard": "从已打开向导继续",
        "steam_restore_running": "Steam 自动还原中...",
        "steam_restore_done": "Steam 自动还原批次已完成。",
        "steam_restore_failed": "Steam 自动还原失败: {error}",
        "steam_restore_started": "开始 Steam GUI 批次还原，共 {count} 项。",
        "steam_restore_started_from_wizard": "从已打开的 Steam 还原向导接手，共 {count} 项。",
        "lang_template_fallback": "当前仅内置英文模板，自动化将使用英文界面识别。",
        "copy_paths": "复制所选路径",
        "open_paths": "打开所选文件夹",
        "open_debug_folder": "打开调试文件夹",
        "open_debug_console": "打开调试窗口",
        "status_ready": "就绪",
        "status_scanning": "扫描中...",
        "status_scan_failed": "扫描失败",
        "type": "类型",
        "app_id": "App ID",
        "game": "游戏",
        "size": "备份大小",
        "source_col": "来源",
        "no_scan": "尚未扫描",
        "detected_summary": "已检测 {count} 个备份 | 已选择 {selected}",
        "size_summary": "已选大小估算: {size}",
        "missing_source_title": "缺少来源路径",
        "missing_source": "请先选择备份来源路径。",
        "scan_failed_title": "扫描失败",
        "scan_complete": "扫描完成，找到 {count} 条备份记录。",
        "no_selection_title": "尚未选择",
        "no_selection": "请至少选择一个 Steam 备份项。",
        "no_steam_backup": "当前选择中没有 Steam 内建备份格式 (sku.sis / .csd / .csm)。",
        "copy_done": "已将 {count} 个路径复制到剪贴板。",
        "copy_fail": "复制到剪贴板失败。",
        "open_paths_done": "已尝试打开 {count} 个文件夹。",
        "steam_not_found_title": "找不到 Steam",
        "steam_not_found": "找不到 Steam.exe，请先安装或启动 Steam。",
        "steam_launch_fail": "无法启动 Steam: {error}",
        "steam_guide_title": "Steam 还原操作指引",
        "steam_guide": "已尝试启动 Steam。\n\n请在 Steam 依次操作:\n1. 左上角 Steam -> Restore Game Backup...\n2. 点击“浏览”并选择下列备份路径之一\n3. 使用 Steam 默认安装路径完成还原\n\n可还原路径:\n{paths}",
        "backup_kind_snapshot": "库快照",
        "backup_kind_package": "Steam 备份包",
        "folder_dialog": "选择备份来源文件夹",
        "debug_console_title": "调试控制台",
        "debug_folder_hint": "调试输出路径: {path}",
    },
    "en": {
        "title": "Steam Batch Restore Assistant",
        "language": "Language",
        "source": "Backup source path",
        "browse": "Browse",
        "scan": "Scan",
        "select_all": "Select All",
        "clear_selection": "Clear Selection",
        "steam_restore": "Launch Steam Restore Flow",
        "steam_restore_from_wizard": "Resume From Open Wizard",
        "steam_restore_running": "Running Steam auto-restore...",
        "steam_restore_done": "Steam GUI batch restore completed.",
        "steam_restore_failed": "Steam GUI batch restore failed: {error}",
        "steam_restore_started": "Starting Steam GUI batch restore for {count} item(s).",
        "steam_restore_started_from_wizard": "Resuming from an already open Steam restore wizard for {count} item(s).",
        "lang_template_fallback": "Only English templates are currently bundled, so automation will use English UI matching.",
        "copy_paths": "Copy Selected Paths",
        "open_paths": "Open Selected Folders",
        "open_debug_folder": "Open Debug Folder",
        "open_debug_console": "Open Debug Console",
        "status_ready": "Ready",
        "status_scanning": "Scanning...",
        "status_scan_failed": "Scan failed",
        "type": "Type",
        "app_id": "App ID",
        "game": "Game",
        "size": "Backup Size",
        "source_col": "Source",
        "no_scan": "No scan yet",
        "detected_summary": "Detected {count} backups | Selected {selected}",
        "size_summary": "Selected backup size estimate: {size}",
        "missing_source_title": "Missing source path",
        "missing_source": "Choose a backup source path first.",
        "scan_failed_title": "Scan failed",
        "scan_complete": "Scan complete. Found {count} backup entries.",
        "no_selection_title": "No selection",
        "no_selection": "Select at least one Steam backup item.",
        "no_steam_backup": "No Steam backup package format found in current selection (sku.sis / .csd / .csm).",
        "copy_done": "Copied {count} path(s) to clipboard.",
        "copy_fail": "Failed to copy paths to clipboard.",
        "open_paths_done": "Attempted to open {count} folder(s).",
        "steam_not_found_title": "Steam not found",
        "steam_not_found": "Steam.exe was not found. Please install or start Steam first.",
        "steam_launch_fail": "Failed to launch Steam: {error}",
        "steam_guide_title": "Steam Restore Guide",
        "steam_guide": "Steam launch was requested.\n\nIn Steam, do:\n1. Top-left Steam -> Restore Game Backup...\n2. Click Browse and choose one of the backup paths below\n3. Finish restore with Steam default install location\n\nCandidate restore paths:\n{paths}",
        "backup_kind_snapshot": "Library snapshot",
        "backup_kind_package": "Steam backup package",
        "folder_dialog": "Choose backup source folder",
        "debug_console_title": "Debug Console",
        "debug_folder_hint": "Debug output path: {path}",
    },
}


class SteamBatchRecoverApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.geometry("1180x720")
        self.minsize(980, 620)

        self.locale_var = tk.StringVar(value="zh-TW")
        self.source_var = tk.StringVar()
        self.status_var = tk.StringVar()
        self.summary_var = tk.StringVar()
        self.space_var = tk.StringVar()
        self.debug_folder = Path(tempfile.gettempdir()) / "SteamBatchRecover_debug"
        self.debug_log_file = self.debug_folder / "session.log"
        self.debug_window: tk.Toplevel | None = None
        self.debug_text: scrolledtext.ScrolledText | None = None

        self.backups: list[GameBackup] = []
        self.debug_folder.mkdir(parents=True, exist_ok=True)

        self._build_layout()
        self._apply_locale()

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

        self.source_label = ttk.Label(controls)
        self.source_label.grid(row=1, column=0, sticky="w", pady=(0, 8))
        ttk.Entry(controls, textvariable=self.source_var).grid(row=1, column=1, sticky="ew", padx=8, pady=(0, 8))
        self.browse_button = ttk.Button(controls, command=self._browse_source)
        self.browse_button.grid(row=1, column=2, sticky="ew", pady=(0, 8))

        actions = ttk.Frame(controls)
        actions.grid(row=2, column=0, columnspan=3, sticky="ew")

        self.scan_button = ttk.Button(actions, command=self._scan)
        self.scan_button.grid(row=0, column=0, padx=(0, 8))
        self.select_all_button = ttk.Button(actions, command=self._select_all)
        self.select_all_button.grid(row=0, column=1, padx=(0, 8))
        self.clear_selection_button = ttk.Button(actions, command=self._clear_selection)
        self.clear_selection_button.grid(row=0, column=2, padx=(0, 8))
        self.steam_restore_button = ttk.Button(actions, command=self._launch_steam_restore)
        self.steam_restore_button.grid(row=0, column=3, padx=(0, 8))
        self.steam_restore_from_wizard_button = ttk.Button(actions, command=self._resume_from_restore_wizard)
        self.steam_restore_from_wizard_button.grid(row=0, column=4, padx=(0, 8))
        self.copy_paths_button = ttk.Button(actions, command=self._copy_selected_paths)
        self.copy_paths_button.grid(row=0, column=5, padx=(0, 8))
        self.open_paths_button = ttk.Button(actions, command=self._open_selected_paths)
        self.open_paths_button.grid(row=0, column=6, padx=(0, 8))
        self.open_debug_folder_button = ttk.Button(actions, command=self._open_debug_folder)
        self.open_debug_folder_button.grid(row=0, column=7, padx=(0, 8))
        self.open_debug_console_button = ttk.Button(actions, command=self._open_debug_console)
        self.open_debug_console_button.grid(row=0, column=8, padx=(0, 8))
        actions.columnconfigure(9, weight=1)

        ttk.Label(actions, textvariable=self.status_var).grid(row=0, column=9, sticky="e")

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
        self.tree.column("name", width=240)
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

        self.log_text = tk.Text(log_panel, height=20, wrap="word", state="disabled")
        self.log_text.grid(row=2, column=0, sticky="nsew", pady=(8, 0))

        self.progressbar = ttk.Progressbar(log_panel, mode="indeterminate")
        self.progressbar.grid(row=3, column=0, sticky="ew", pady=(8, 0))

    def _browse_source(self) -> None:
        selected = filedialog.askdirectory(title=self._t("folder_dialog"))
        if selected:
            self.source_var.set(selected)

    def _scan(self) -> None:
        source_text = self.source_var.get().strip()
        if not source_text:
            messagebox.showerror(self._t("missing_source_title"), self._t("missing_source"))
            return

        source_path = Path(source_text)
        self._set_busy(True, self._t("status_scanning"))
        threading.Thread(target=self._scan_worker, args=(source_path,), daemon=True).start()

    def _scan_worker(self, source_path: Path) -> None:
        try:
            backups = scan_backups(source_path)
        except Exception as exc:
            self.after(0, lambda: self._scan_failed(exc))
            return
        self.after(0, lambda: self._scan_completed(backups))

    def _scan_failed(self, exc: Exception) -> None:
        self._set_busy(False, self._t("status_scan_failed"))
        messagebox.showerror(self._t("scan_failed_title"), str(exc))

    def _scan_completed(self, backups: list[GameBackup]) -> None:
        self.backups = backups
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
        self._set_busy(False, self._t("status_ready"))

    def _select_all(self) -> None:
        item_ids = self.tree.get_children()
        self.tree.selection_set(item_ids)
        self._refresh_space_summary()

    def _clear_selection(self) -> None:
        self.tree.selection_remove(self.tree.selection())
        self._refresh_space_summary()

    def _launch_steam_restore(self) -> None:
        self._start_steam_restore(start_from_restore_wizard=False)

    def _resume_from_restore_wizard(self) -> None:
        self._start_steam_restore(start_from_restore_wizard=True)

    def _start_steam_restore(self, start_from_restore_wizard: bool) -> None:
        restore_paths = self._selected_restore_paths()
        if not restore_paths:
            messagebox.showinfo(self._t("no_selection_title"), self._t("no_steam_backup"))
            return

        steam_path = find_steam_executable()
        if steam_path is None:
            messagebox.showerror(self._t("steam_not_found_title"), self._t("steam_not_found"))
            return

        locale_code = self.locale_var.get().lower()
        template_language = "en" if locale_code == "en" else "en"
        if template_language != locale_code:
            self._append_log(self._t("lang_template_fallback"))

        templates_root = _resolve_templates_root(template_language)
        self._append_log(self._t("debug_folder_hint", path=self.debug_folder))
        self._append_log(f"Templates root: {templates_root}")
        if not templates_root.exists():
            messagebox.showerror(self._t("scan_failed_title"), f"Template folder not found: {templates_root}")
            return

        start_key = "steam_restore_started_from_wizard" if start_from_restore_wizard else "steam_restore_started"
        self._append_log(self._t(start_key, count=len(restore_paths)))
        self._set_busy(True, self._t("steam_restore_running"))
        threading.Thread(
            target=self._steam_restore_worker,
            args=(steam_path, restore_paths, templates_root, start_from_restore_wizard),
            daemon=True,
        ).start()

    def _steam_restore_worker(
        self,
        steam_path: Path,
        restore_paths: list[Path],
        templates_root: Path,
        start_from_restore_wizard: bool,
    ) -> None:
        self._queue_log(f"Steam restore worker started. steam={steam_path}")
        automator = SteamGuiAutomator(templates_root=templates_root)
        try:
            automator.run_batch_restore(
                steam_path,
                restore_paths,
                self._queue_log,
                steam_already_running=False,
                start_from_restore_wizard=start_from_restore_wizard,
            )
        except SteamGuiAutomationError as exc:
            self.after(0, lambda: self._steam_restore_failed(str(exc)))
            return
        except Exception as exc:  # noqa: BLE001
            tb = traceback.format_exc()
            self._queue_log(f"Unhandled automation exception: {exc!r}")
            self._queue_log(tb)
            self.after(0, lambda: self._steam_restore_failed(f"{exc!r}"))
            return
        self.after(0, self._steam_restore_done)

    def _steam_restore_done(self) -> None:
        self._set_busy(False, self._t("status_ready"))
        self._append_log(self._t("steam_restore_done"))
        messagebox.showinfo(self._t("steam_guide_title"), self._t("steam_restore_done"))

    def _steam_restore_failed(self, error: str) -> None:
        self._set_busy(False, self._t("status_ready"))
        self._append_log(self._t("steam_restore_failed", error=error))
        self._append_log(self._t("debug_folder_hint", path=self.debug_folder))
        messagebox.showerror(self._t("scan_failed_title"), self._t("steam_restore_failed", error=error))

    def _queue_log(self, message: str) -> None:
        self.after(0, lambda: self._append_log(message))

    def _copy_selected_paths(self) -> None:
        restore_paths = self._selected_restore_paths()
        if not restore_paths:
            messagebox.showinfo(self._t("no_selection_title"), self._t("no_selection"))
            return
        try:
            self.clipboard_clear()
            self.clipboard_append("\n".join(restore_paths))
            self.update_idletasks()
        except tk.TclError:
            messagebox.showerror(self._t("scan_failed_title"), self._t("copy_fail"))
            return
        self._append_log(self._t("copy_done", count=len(restore_paths)))

    def _open_selected_paths(self) -> None:
        restore_paths = self._selected_restore_paths()
        if not restore_paths:
            messagebox.showinfo(self._t("no_selection_title"), self._t("no_selection"))
            return
        opened = 0
        for path in restore_paths[:10]:
            try:
                os.startfile(path)
                opened += 1
            except OSError:
                continue
        self._append_log(self._t("open_paths_done", count=opened))

    def _open_debug_folder(self) -> None:
        try:
            self.debug_folder.mkdir(parents=True, exist_ok=True)
            os.startfile(str(self.debug_folder))
            self._append_log(self._t("debug_folder_hint", path=self.debug_folder))
        except OSError as exc:
            self._append_log(f"Failed to open debug folder: {exc}")

    def _open_debug_console(self) -> None:
        if self.debug_window is not None and self.debug_window.winfo_exists():
            self.debug_window.deiconify()
            self.debug_window.lift()
            self.debug_window.focus_force()
            return

        self.debug_window = tk.Toplevel(self)
        self.debug_window.title(self._t("debug_console_title"))
        self.debug_window.geometry("980x420")

        self.debug_text = scrolledtext.ScrolledText(self.debug_window, wrap="word", state="disabled")
        self.debug_text.pack(fill="both", expand=True, padx=8, pady=8)
        self._append_debug_window_line(self._t("debug_folder_hint", path=self.debug_folder))

    def _append_log(self, message: str) -> None:
        timestamped = f"[{datetime.now().strftime('%H:%M:%S')}] {message}"
        self.log_text.configure(state="normal")
        self.log_text.insert("end", timestamped + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")
        self._append_debug_window_line(timestamped)
        self._append_debug_file_line(timestamped)

    def _append_debug_window_line(self, message: str) -> None:
        if self.debug_text is None:
            return
        self.debug_text.configure(state="normal")
        self.debug_text.insert("end", message + "\n")
        self.debug_text.see("end")
        self.debug_text.configure(state="disabled")

    def _append_debug_file_line(self, message: str) -> None:
        try:
            self.debug_folder.mkdir(parents=True, exist_ok=True)
            with self.debug_log_file.open("a", encoding="utf-8") as handle:
                handle.write(message + "\n")
        except OSError:
            pass

    def _refresh_space_summary(self) -> None:
        selected = self._selected_backups()
        required_bytes = sum(item.required_bytes for item in selected)
        self.space_var.set(self._t("size_summary", size=format_bytes(required_bytes)))
        if self.backups:
            self.summary_var.set(self._t("detected_summary", count=len(self.backups), selected=len(selected)))
        else:
            self.summary_var.set(self._t("no_scan"))

    def _selected_backups(self) -> list[GameBackup]:
        selected_ids = set(self.tree.selection())
        return [backup for backup in self.backups if self._row_id(backup) in selected_ids]

    def _selected_restore_paths(self) -> list[Path]:
        paths: list[Path] = []
        seen: set[str] = set()
        for backup in self._selected_backups():
            if backup.kind is not BackupKind.STEAM_PACKAGE:
                continue
            path_str = str(backup.source_path)
            if path_str not in seen:
                paths.append(backup.source_path)
                seen.add(path_str)
        return paths

    def _kind_label(self, kind: BackupKind) -> str:
        if kind is BackupKind.STEAM_PACKAGE:
            return self._t("backup_kind_package")
        return self._t("backup_kind_snapshot")

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
        self.source_label.configure(text=self._t("source"))
        self.browse_button.configure(text=self._t("browse"))
        self.scan_button.configure(text=self._t("scan"))
        self.select_all_button.configure(text=self._t("select_all"))
        self.clear_selection_button.configure(text=self._t("clear_selection"))
        self.steam_restore_button.configure(text=self._t("steam_restore"))
        self.steam_restore_from_wizard_button.configure(text=self._t("steam_restore_from_wizard"))
        self.copy_paths_button.configure(text=self._t("copy_paths"))
        self.open_paths_button.configure(text=self._t("open_paths"))
        self.open_debug_folder_button.configure(text=self._t("open_debug_folder"))
        self.open_debug_console_button.configure(text=self._t("open_debug_console"))

        self.tree.heading("kind", text=self._t("type"))
        self.tree.heading("app_id", text=self._t("app_id"))
        self.tree.heading("name", text=self._t("game"))
        self.tree.heading("size", text=self._t("size"))
        self.tree.heading("source", text=self._t("source_col"))

        self.status_var.set(self._t("status_ready"))
        if not self.backups:
            self.summary_var.set(self._t("no_scan"))
            self.space_var.set(self._t("size_summary", size="0 B"))
        else:
            self._refresh_space_summary()

            selected_ids = set(self.tree.selection())
            for item_id in self.tree.get_children():
                values = self.tree.item(item_id, "values")
                if not values:
                    continue
                parts = item_id.split(":", 2)
                app_id = parts[0] if len(parts) > 0 else ""
                source = parts[2] if len(parts) > 2 else ""
                backup = next((b for b in self.backups if b.app_id == app_id and str(b.source_path) == source), None)
                if backup is None:
                    continue
                self.tree.item(item_id, values=(self._kind_label(backup.kind), *values[1:]))
            self.tree.selection_set(list(selected_ids))

    @staticmethod
    def _row_id(backup: GameBackup) -> str:
        return f"{backup.app_id}:{backup.kind.value}:{backup.source_path}"


def _resolve_templates_root(language: str) -> Path:
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    else:
        base = Path(__file__).resolve().parents[2]
    return base / "SteamGUI_material" / language


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
