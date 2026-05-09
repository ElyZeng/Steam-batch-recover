from __future__ import annotations

import os
import threading
import tkinter as tk
from ctypes import Structure, byref, windll
from ctypes import wintypes
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
        "subtitle": "以倉庫與 manifest 管理跨機備份與還原流程",
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
        "backup_time": "備份時間",
        "updated_time": "上次更新",
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
        "free_space_warning": "目標空間不足。需要 {required}，目前剩餘 {free}。\n是否仍要繼續?",
        "free_space_warning_title": "空間不足警告",
        "using_target_library": "目前目標還原路徑: {path}",
        "repository_manifest_hint": "備份倉庫將使用 manifest.json 與 entries/*/backup_manifest.json 管理。",
        "mode_installed": "本機來源",
        "mode_repository": "倉庫內容",
        "hero_primary": "Steam Backup Repository",
        "hero_secondary": "建立可攜式遊戲倉庫，並在另一台電腦直接還原到 Steam Library。",
        "stat_entries": "清單項目",
        "stat_selected": "目前選取",
        "stat_target": "目標路徑",
        "operation_log": "操作紀錄",
        "content_title": "遊戲與備份清單",
        "paths_title": "倉庫與目標",
        "actions_title": "操作中心",
    },
    "zh-CN": {
        "title": "Steam 游戏备份与还原助手",
        "subtitle": "以仓库与 manifest 管理跨机备份与还原流程",
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
        "backup_time": "备份时间",
        "updated_time": "上次更新",
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
        "free_space_warning": "目标空间不足。需要 {required}，当前剩余 {free}。\n是否仍要继续?",
        "free_space_warning_title": "空间不足警告",
        "using_target_library": "当前目标还原路径: {path}",
        "repository_manifest_hint": "备份仓库会使用 manifest.json 与 entries/*/backup_manifest.json 进行管理。",
        "mode_installed": "本机来源",
        "mode_repository": "仓库内容",
        "hero_primary": "Steam Backup Repository",
        "hero_secondary": "建立可携式游戏仓库，并在另一台电脑直接还原到 Steam Library。",
        "stat_entries": "列表项目",
        "stat_selected": "当前选择",
        "stat_target": "目标路径",
        "operation_log": "操作日志",
        "content_title": "游戏与备份列表",
        "paths_title": "仓库与目标",
        "actions_title": "操作中心",
    },
    "en": {
        "title": "Steam Game Backup and Restore Assistant",
        "subtitle": "A manifest-driven repository workflow for cross-machine backup and restore.",
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
        "backup_time": "Backup Time",
        "updated_time": "Last Updated",
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
        "free_space_warning": "Not enough free space. Need {required}, only {free} available.\nContinue anyway?",
        "free_space_warning_title": "Insufficient Space",
        "using_target_library": "Current restore target: {path}",
        "repository_manifest_hint": "The repository uses manifest.json and entries/*/backup_manifest.json.",
        "mode_installed": "Installed Source",
        "mode_repository": "Repository View",
        "hero_primary": "Steam Backup Repository",
        "hero_secondary": "Build a portable game archive and restore it directly into another Steam library.",
        "stat_entries": "Entries",
        "stat_selected": "Selected",
        "stat_target": "Target",
        "operation_log": "Operation Log",
        "content_title": "Games and Repository Entries",
        "paths_title": "Repository and Target",
        "actions_title": "Operations",
    },
}


class SteamBatchRecoverApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.minsize(980, 640)
        self.configure(bg="#0a1423")
        self.overrideredirect(True)
        self._restore_geometry = ""
        self._is_maximized = False
        self._drag_offset_x = 0
        self._drag_offset_y = 0

        self.locale_var = tk.StringVar(value="en")
        self.repository_var = tk.StringVar()
        self.target_library_var = tk.StringVar(value=self._detect_default_target_library())
        self.status_var = tk.StringVar()
        self.summary_var = tk.StringVar()
        self.space_var = tk.StringVar()
        self.mode_var = tk.StringVar()
        self.entries_stat_var = tk.StringVar(value="0")
        self.selected_stat_var = tk.StringVar(value="0")
        self.target_stat_var = tk.StringVar(value="-")
        self.progress_text_var = tk.StringVar(value="-")
        self._progress_mode = "idle"
        self._progress_total = 0
        self._progress_current = 0
        self._is_busy = False
        self.backups: list[GameBackup] = []
        self.current_view = "none"
        self._installed_scan_cache: list[GameBackup] | None = None
        self._repository_scan_cache: dict[str, list[GameBackup]] = {}

        self._set_initial_geometry()
        self._configure_styles()
        self._build_layout()
        self._apply_locale()
        self.bind("<Map>", self._on_window_map)
        if self.target_library_var.get().strip():
            self._append_log(self._t("using_target_library", path=self.target_library_var.get().strip()))

    def _set_initial_geometry(self) -> None:
        left, top, right, bottom = self._get_work_area()
        work_width = max(1, right - left)
        work_height = max(1, bottom - top)
        width = min(1380, max(980, work_width - 80))
        height = min(840, max(620, work_height - 90))
        pos_x = left + max(0, (work_width - width) // 2)
        pos_y = top + max(0, (work_height - height) // 2)
        self.geometry(f"{width}x{height}+{pos_x}+{pos_y}")
        self.after(500, self._adjust_geometry_if_needed)

    def _get_work_area(self) -> tuple[int, int, int, int]:
        class RECT(Structure):
            _fields_ = [
                ("left", wintypes.LONG),
                ("top", wintypes.LONG),
                ("right", wintypes.LONG),
                ("bottom", wintypes.LONG),
            ]

        rect = RECT()
        spi_get_workarea = 0x0030
        try:
            success = windll.user32.SystemParametersInfoW(spi_get_workarea, 0, byref(rect), 0)
            if success:
                return (rect.left, rect.top, rect.right, rect.bottom)
        except Exception:
            pass

        return (0, 0, self.winfo_screenwidth(), self.winfo_screenheight())

    def _adjust_geometry_if_needed(self) -> None:
        """Check if window extends beyond screen bounds and adjust if needed (for dynamic taskbars)."""
        try:
            self.update_idletasks()
            left, top, right, bottom = self._get_work_area()
            win_width = self.winfo_width()
            win_height = self.winfo_height()
            win_x = self.winfo_x()
            win_y = self.winfo_y()

            adjusted = False
            min_x = left
            max_x = max(left, right - win_width)
            min_y = top
            max_y = max(top, bottom - win_height)

            if win_x < min_x:
                win_x = min_x
                adjusted = True
            elif win_x > max_x:
                win_x = max_x
                adjusted = True

            if win_y < min_y:
                win_y = min_y
                adjusted = True
            elif win_y > max_y:
                win_y = max_y
                adjusted = True

            if adjusted:
                self.geometry(f"+{win_x}+{win_y}")
        except Exception:
            pass

    def _configure_styles(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")

        background = "#0a1423"
        panel = "#111f34"
        card = "#152742"
        entry_bg = "#0f1d30"
        accent = "#19a7ff"
        accent_active = "#48bbff"
        text = "#f4f7fb"
        muted = "#93a9c4"
        border = "#203553"

        style.configure("Intel.TFrame", background=background)
        style.configure("Card.TFrame", background=panel, relief="flat")
        style.configure("Hero.TFrame", background=card, relief="flat")
        style.configure("CardTitle.TLabel", background=panel, foreground=text, font=("Segoe UI Semibold", 11))
        style.configure("HeroTitle.TLabel", background=card, foreground=text, font=("Segoe UI Semibold", 22))
        style.configure("HeroSubtitle.TLabel", background=card, foreground=muted, font=("Segoe UI", 10))
        style.configure("Intel.TLabel", background=background, foreground=text, font=("Segoe UI", 10))
        style.configure("Panel.TLabel", background=panel, foreground=text, font=("Segoe UI", 10))
        style.configure("Muted.TLabel", background=panel, foreground=muted, font=("Segoe UI", 9))
        style.configure("MetricValue.TLabel", background=panel, foreground=text, font=("Segoe UI Semibold", 18))
        style.configure("MetricCaption.TLabel", background=panel, foreground=muted, font=("Segoe UI", 9))
        style.configure("Intel.TEntry", fieldbackground=entry_bg, foreground=text, insertcolor=text, bordercolor=border, lightcolor=border, darkcolor=border)
        style.map("Intel.TEntry", bordercolor=[("focus", accent)], lightcolor=[("focus", accent)], darkcolor=[("focus", accent)])
        style.configure("Intel.TCombobox", fieldbackground=entry_bg, background=entry_bg, foreground=text, bordercolor=border, arrowcolor=text)
        style.map("Intel.TCombobox", fieldbackground=[("readonly", entry_bg)], foreground=[("readonly", text)], bordercolor=[("focus", accent)])
        style.configure("Accent.TButton", background=accent, foreground="#04111d", padding=(14, 10), font=("Segoe UI Semibold", 10), borderwidth=0)
        style.map("Accent.TButton", background=[("disabled", "#1a3558"), ("active", accent_active), ("pressed", "#0f8dd8")], foreground=[("disabled", "#4a6080")])
        style.configure("Intel.TButton", background=card, foreground=text, padding=(14, 10), font=("Segoe UI", 10), bordercolor=border, lightcolor=border, darkcolor=border)
        style.map("Intel.TButton", background=[("disabled", "#0d1928"), ("active", "#1a3558"), ("pressed", "#102338")], foreground=[("disabled", "#4a6080")], bordercolor=[("focus", accent)])
        style.configure("Intel.Horizontal.TProgressbar", troughcolor="#0d1a2b", background=accent, bordercolor="#0d1a2b", lightcolor=accent, darkcolor=accent)
        style.configure(
            "Intel.Treeview",
            background=entry_bg,
            fieldbackground=entry_bg,
            foreground=text,
            bordercolor=border,
            rowheight=30,
            font=("Segoe UI", 10),
        )
        style.configure(
            "Intel.Treeview.Heading",
            background=panel,
            foreground=text,
            bordercolor=border,
            font=("Segoe UI Semibold", 10),
            padding=(10, 8),
        )
        style.map("Intel.Treeview", background=[("selected", "#1b68b3")], foreground=[("selected", text)])
        style.map("Intel.Treeview.Heading", background=[("active", "#1c3351")])

    def _build_layout(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        titlebar = tk.Frame(self, bg="#08111d", height=34, highlightthickness=0)
        titlebar.grid(row=0, column=0, sticky="ew")
        titlebar.grid_propagate(False)
        titlebar.columnconfigure(1, weight=1)
        titlebar.bind("<ButtonPress-1>", self._start_window_drag)
        titlebar.bind("<B1-Motion>", self._on_window_drag)
        titlebar.bind("<Double-Button-1>", lambda _: self._toggle_maximize())

        self.window_title_label = tk.Label(
            titlebar,
            bg="#08111d",
            fg="#d8e7f7",
            font=("Segoe UI Semibold", 10),
            padx=12,
            anchor="w",
        )
        self.window_title_label.grid(row=0, column=1, sticky="ew")
        self.window_title_label.bind("<ButtonPress-1>", self._start_window_drag)
        self.window_title_label.bind("<B1-Motion>", self._on_window_drag)
        self.window_title_label.bind("<Double-Button-1>", lambda _: self._toggle_maximize())

        self.min_button = tk.Button(titlebar, text="_", command=self._minimize_window, bg="#08111d", fg="#d8e7f7", bd=0, relief="flat", font=("Segoe UI", 10), width=4, activebackground="#133054", activeforeground="#ffffff")
        self.min_button.grid(row=0, column=2, sticky="ns")
        self.max_button = tk.Button(titlebar, text="□", command=self._toggle_maximize, bg="#08111d", fg="#d8e7f7", bd=0, relief="flat", font=("Segoe UI", 10), width=4, activebackground="#133054", activeforeground="#ffffff")
        self.max_button.grid(row=0, column=3, sticky="ns")
        self.close_button = tk.Button(titlebar, text="×", command=self.destroy, bg="#08111d", fg="#f5c9cf", bd=0, relief="flat", font=("Segoe UI", 11), width=4, activebackground="#c83c4b", activeforeground="#ffffff")
        self.close_button.grid(row=0, column=4, sticky="ns")

        shell = tk.Frame(self, bg="#0a1423")
        shell.grid(row=1, column=0, sticky="nsew")
        shell.columnconfigure(0, weight=1)
        shell.rowconfigure(2, weight=1)

        hero = ttk.Frame(shell, style="Hero.TFrame", padding=20)
        hero.grid(row=0, column=0, sticky="ew", padx=18, pady=(18, 12))
        hero.columnconfigure(0, weight=1)
        hero.columnconfigure(1, weight=0)

        self.hero_title = ttk.Label(hero, style="HeroTitle.TLabel")
        self.hero_title.grid(row=0, column=0, sticky="w")
        self.hero_subtitle = ttk.Label(hero, style="HeroSubtitle.TLabel")
        self.hero_subtitle.grid(row=1, column=0, sticky="w", pady=(6, 0))
        self.status_chip = tk.Label(
            hero,
            textvariable=self.status_var,
            bg="#1a3558",
            fg="#f4f7fb",
            padx=14,
            pady=8,
            font=("Segoe UI Semibold", 10),
        )
        self.status_chip.grid(row=0, column=1, rowspan=2, sticky="e")

        dashboard = tk.Frame(shell, bg="#0a1423")
        dashboard.grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 12))
        dashboard.columnconfigure(0, weight=3)
        dashboard.columnconfigure(1, weight=2)

        controls_card = ttk.Frame(dashboard, style="Card.TFrame", padding=18)
        controls_card.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        controls_card.columnconfigure(1, weight=1)
        ttk.Label(controls_card, style="CardTitle.TLabel", textvariable=self._stringvar_proxy("paths_title")).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 14))

        self.language_label = ttk.Label(controls_card, style="Panel.TLabel")
        self.language_label.grid(row=1, column=0, sticky="w", pady=(0, 10))
        self.language_combo = ttk.Combobox(
            controls_card,
            textvariable=self.locale_var,
            state="readonly",
            values=("zh-TW", "zh-CN", "en"),
            width=16,
            style="Intel.TCombobox",
        )
        self.language_combo.grid(row=1, column=1, sticky="w", pady=(0, 10))
        self.language_combo.bind("<<ComboboxSelected>>", lambda _: self._apply_locale())

        self.repository_label = ttk.Label(controls_card, style="Panel.TLabel")
        self.repository_label.grid(row=2, column=0, sticky="w", pady=(0, 10))
        self.repository_entry = ttk.Entry(controls_card, textvariable=self.repository_var, style="Intel.TEntry")
        self.repository_entry.grid(row=2, column=1, sticky="ew", padx=12, pady=(0, 10))
        self.repository_browse_button = ttk.Button(controls_card, command=self._browse_repository, style="Intel.TButton")
        self.repository_browse_button.grid(row=2, column=2, sticky="ew", pady=(0, 10))

        self.target_label = ttk.Label(controls_card, style="Panel.TLabel")
        self.target_label.grid(row=3, column=0, sticky="w")
        self.target_entry = ttk.Entry(controls_card, textvariable=self.target_library_var, style="Intel.TEntry")
        self.target_entry.grid(row=3, column=1, sticky="ew", padx=12)
        self.target_browse_button = ttk.Button(controls_card, command=self._browse_target_library, style="Intel.TButton")
        self.target_browse_button.grid(row=3, column=2, sticky="ew")

        metrics_card = ttk.Frame(dashboard, style="Card.TFrame", padding=18)
        metrics_card.grid(row=0, column=1, sticky="nsew")
        metrics_card.columnconfigure((0, 1, 2), weight=1)
        self.metrics_title = ttk.Label(metrics_card, style="CardTitle.TLabel")
        self.metrics_title.grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 14))
        self.mode_label = ttk.Label(metrics_card, style="Muted.TLabel", textvariable=self.mode_var)
        self.mode_label.grid(row=1, column=0, columnspan=3, sticky="w", pady=(0, 16))

        self.metric_entries_caption = ttk.Label(metrics_card, style="MetricCaption.TLabel")
        self.metric_entries_caption.grid(row=2, column=0, sticky="w")
        ttk.Label(metrics_card, textvariable=self.entries_stat_var, style="MetricValue.TLabel").grid(row=3, column=0, sticky="w")
        self.metric_selected_caption = ttk.Label(metrics_card, style="MetricCaption.TLabel")
        self.metric_selected_caption.grid(row=2, column=1, sticky="w")
        ttk.Label(metrics_card, textvariable=self.selected_stat_var, style="MetricValue.TLabel").grid(row=3, column=1, sticky="w")
        self.metric_target_caption = ttk.Label(metrics_card, style="MetricCaption.TLabel")
        self.metric_target_caption.grid(row=2, column=2, sticky="w")
        ttk.Label(metrics_card, textvariable=self.target_stat_var, style="MetricValue.TLabel").grid(row=3, column=2, sticky="w")
        ttk.Label(metrics_card, textvariable=self.summary_var, style="Muted.TLabel").grid(row=4, column=0, columnspan=3, sticky="w", pady=(18, 6))
        ttk.Label(metrics_card, textvariable=self.space_var, style="Muted.TLabel").grid(row=5, column=0, columnspan=3, sticky="w")

        body = tk.Frame(shell, bg="#0a1423")
        body.grid(row=2, column=0, sticky="nsew", padx=18, pady=(0, 18))
        body.columnconfigure(0, weight=7)
        body.columnconfigure(1, weight=3)
        body.rowconfigure(1, weight=1)

        content_card = ttk.Frame(body, style="Card.TFrame", padding=18)
        content_card.grid(row=0, column=0, rowspan=2, sticky="nsew", padx=(0, 12))
        content_card.columnconfigure(0, weight=1)
        content_card.rowconfigure(2, weight=1, minsize=300)

        self.content_title = ttk.Label(content_card, style="CardTitle.TLabel")
        self.content_title.grid(row=0, column=0, sticky="w")
        self.progress_percent_label = ttk.Label(content_card, style="Muted.TLabel", textvariable=self.progress_text_var)
        self.progress_percent_label.grid(row=0, column=1, sticky="e")
        self.progressbar = ttk.Progressbar(content_card, mode="indeterminate", style="Intel.Horizontal.TProgressbar", maximum=100, value=0)
        self.progressbar.grid(row=1, column=0, sticky="ew", pady=(12, 14))

        columns = ("kind", "app_id", "name", "backup_time", "size", "source")
        self.tree = ttk.Treeview(content_card, columns=columns, show="headings", selectmode="extended", style="Intel.Treeview")
        self.tree.grid(row=2, column=0, sticky="nsew")
        self.tree.column("kind", width=140, anchor="center")
        self.tree.column("app_id", width=90, anchor="center")
        self.tree.column("name", width=240)
        self.tree.column("backup_time", width=170, anchor="center")
        self.tree.column("size", width=120, anchor="e")
        self.tree.column("source", width=460)
        self.tree.bind("<Button-1>", self._on_tree_simple_click)
        self.tree.bind("<<TreeviewSelect>>", lambda _: self._refresh_space_summary())
        tree_scrollbar = ttk.Scrollbar(content_card, orient="vertical", command=self.tree.yview)
        tree_scrollbar.grid(row=2, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=tree_scrollbar.set)

        actions_card = ttk.Frame(body, style="Card.TFrame", padding=18)
        actions_card.grid(row=0, column=1, sticky="nsew")
        actions_card.columnconfigure(0, weight=1)
        self.actions_title = ttk.Label(actions_card, style="CardTitle.TLabel")
        self.actions_title.grid(row=0, column=0, sticky="w", pady=(0, 14))
        self.scan_installed_button = ttk.Button(actions_card, command=self._scan_installed, style="Accent.TButton")
        self.scan_installed_button.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        self.scan_repository_button = ttk.Button(actions_card, command=self._scan_repository, style="Intel.TButton")
        self.scan_repository_button.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        self.select_all_button = ttk.Button(actions_card, command=self._select_all, style="Intel.TButton")
        self.select_all_button.grid(row=3, column=0, sticky="ew", pady=(10, 10))
        self.clear_selection_button = ttk.Button(actions_card, command=self._clear_selection, style="Intel.TButton")
        self.clear_selection_button.grid(row=4, column=0, sticky="ew", pady=(0, 10))
        self.backup_selected_button = ttk.Button(actions_card, command=self._backup_selected, style="Accent.TButton")
        self.backup_selected_button.grid(row=5, column=0, sticky="ew", pady=(10, 10))
        self.restore_selected_button = ttk.Button(actions_card, command=self._restore_selected, style="Intel.TButton")
        self.restore_selected_button.grid(row=6, column=0, sticky="ew", pady=(0, 10))
        self.copy_paths_button = ttk.Button(actions_card, command=self._copy_selected_paths, style="Intel.TButton")
        self.copy_paths_button.grid(row=7, column=0, sticky="ew", pady=(10, 10))
        self.open_paths_button = ttk.Button(actions_card, command=self._open_selected_paths, style="Intel.TButton")
        self.open_paths_button.grid(row=8, column=0, sticky="ew")

        self._refresh_operation_buttons()

        log_card = ttk.Frame(body, style="Card.TFrame", padding=18)
        log_card.grid(row=1, column=1, sticky="nsew", pady=(12, 0))
        log_card.columnconfigure(0, weight=1)
        log_card.rowconfigure(1, weight=1)
        self.log_title = ttk.Label(log_card, style="CardTitle.TLabel")
        self.log_title.grid(row=0, column=0, sticky="w", pady=(0, 12))
        self.log_text = scrolledtext.ScrolledText(
            log_card,
            height=16,
            wrap="word",
            state="disabled",
            bg="#0f1d30",
            fg="#f4f7fb",
            insertbackground="#f4f7fb",
            relief="flat",
            font=("Consolas", 10),
            padx=10,
            pady=10,
        )
        self.log_text.grid(row=1, column=0, sticky="nsew")

    def _stringvar_proxy(self, key: str) -> tk.StringVar:
        variable = tk.StringVar(value=self._t(key))
        setattr(self, f"_{key}_var", variable)
        return variable

    def _browse_repository(self) -> None:
        selected = filedialog.askdirectory(title=self._t("folder_dialog_repository"))
        if selected:
            self.repository_var.set(selected)
            self._refresh_space_summary()

    def _browse_target_library(self) -> None:
        selected = filedialog.askdirectory(title=self._t("folder_dialog_target"))
        if selected:
            self.target_library_var.set(selected)
            self._append_log(self._t("using_target_library", path=selected))
            self._refresh_space_summary()

    def _scan_installed(self) -> None:
        if self._installed_scan_cache is not None:
            self._scan_completed(list(self._installed_scan_cache), view="installed")
            return
        self._set_busy(True, self._t("status_scanning"))
        threading.Thread(target=self._scan_installed_worker, daemon=True).start()

    def _scan_installed_worker(self) -> None:
        try:
            backups = scan_installed_games()
        except Exception as exc:  # noqa: BLE001
            self.after(0, lambda: self._operation_failed(exc))
            return
        self._installed_scan_cache = list(backups)
        self.after(0, lambda: self._scan_completed(backups, view="installed"))

    def _scan_repository(self) -> None:
        repository_text = self.repository_var.get().strip()
        if not repository_text:
            messagebox.showerror(self._t("missing_repository_title"), self._t("missing_repository"))
            return
        cached = self._repository_scan_cache.get(repository_text)
        if cached is not None:
            self._scan_completed(list(cached), view="repository")
            return
        self._set_busy(True, self._t("status_scanning"))
        threading.Thread(target=self._scan_repository_worker, args=(Path(repository_text),), daemon=True).start()

    def _scan_repository_worker(self, repository_root: Path) -> None:
        try:
            backups = scan_repository_backups(repository_root)
        except Exception as exc:  # noqa: BLE001
            self.after(0, lambda: self._operation_failed(exc))
            return
        self._repository_scan_cache[str(repository_root)] = list(backups)
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
                    self._display_time_value(backup),
                    format_bytes(backup.required_bytes),
                    str(backup.source_path),
                ),
            )

        self.entries_stat_var.set(str(len(backups)))
        self.selected_stat_var.set("0")
        self.mode_var.set(self._t("mode_installed") if view == "installed" else self._t("mode_repository"))
        self.tree.heading("backup_time", text=self._time_column_label())
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
        if not self._ensure_free_space(repository_root, selected):
            return
        self._prepare_progress(total_steps=len(selected))
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
        if not self._ensure_free_space(target_root, selected):
            return
        self._prepare_progress(total_steps=len(selected))
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
        if operation == "backup":
            # Repository entries changed, force a fresh repository scan next time.
            self._repository_scan_cache.clear()
        elif operation == "restore":
            # Installed game state may have changed after restore.
            self._installed_scan_cache = None
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

    def _on_tree_simple_click(self, event: tk.Event) -> str:
        """Toggle clicked row selection without requiring Ctrl, while keeping other selected rows."""
        item = self.tree.identify_row(event.y)
        if not item:
            return "break"

        current_selection = self.tree.selection()
        if item in current_selection:
            self.tree.selection_remove(item)
        else:
            self.tree.selection_add(item)

        self.tree.focus(item)
        self.tree.see(item)
        self.after(0, self._refresh_space_summary)
        return "break"

    def _clear_selection(self) -> None:
        self.tree.selection_remove(self.tree.selection())
        self._refresh_space_summary()

    def _selected_backups(self) -> list[GameBackup]:
        selected_ids = set(self.tree.selection())
        return [backup for backup in self.backups if self._row_id(backup) in selected_ids]

    def _copy_selected_paths(self) -> None:
        selected = self._selected_backups()
        if not selected:
            messagebox.showinfo(self._t("no_selection_title"), self._no_selection_message())
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
            messagebox.showinfo(self._t("no_selection_title"), self._no_selection_message())
            return
        opened = 0
        for item in selected[:10]:
            try:
                os.startfile(str(item.source_path))
                opened += 1
            except OSError:
                continue
        self._append_log(self._t("open_paths_done", count=opened))

    def _ensure_free_space(self, target_path: Path, selected: list[GameBackup]) -> bool:
        """Return True if it is safe to proceed (enough space or user confirmed). False means cancel."""
        required = sum(item.required_bytes for item in selected)
        free = get_free_space_bytes(target_path)
        if required > free:
            return messagebox.askokcancel(
                self._t("free_space_warning_title"),
                self._t("free_space_warning", required=format_bytes(required), free=format_bytes(free)),
                icon="warning",
            )
        return True

    def _queue_log(self, message: str) -> None:
        if message.startswith("__PROGRESS__|"):
            self.after(0, lambda: self._apply_progress_message(message))
            return
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
        self.selected_stat_var.set(str(len(selected)))
        target_label = Path(free_target).name if free_target else "-"
        self.target_stat_var.set(target_label[:18] + "..." if len(target_label) > 21 else target_label)
        if self.backups:
            self.summary_var.set(self._t("detected_summary", count=len(self.backups), selected=len(selected)))
        else:
            self.summary_var.set(self._t("no_scan"))

    def _refresh_operation_buttons(self) -> None:
        if self._is_busy:
            self.scan_installed_button.configure(state="disabled")
            self.scan_repository_button.configure(state="disabled")
            self.backup_selected_button.configure(state="disabled")
            self.restore_selected_button.configure(state="disabled")
            return

        self.scan_installed_button.configure(state="normal")
        self.scan_repository_button.configure(state="normal")

        if self.current_view == "installed":
            self.backup_selected_button.configure(state="normal")
            self.restore_selected_button.configure(state="disabled")
            return

        if self.current_view == "repository":
            self.backup_selected_button.configure(state="disabled")
            self.restore_selected_button.configure(state="normal")
            return

        self.backup_selected_button.configure(state="disabled")
        self.restore_selected_button.configure(state="disabled")

    def _kind_label(self, kind: BackupKind) -> str:
        if kind is BackupKind.INSTALLED_GAME:
            return self._t("backup_kind_installed")
        return self._t("backup_kind_repository")

    def _set_busy(self, busy: bool, status: str) -> None:
        self._is_busy = busy
        self.status_var.set(status)
        if busy:
            if self._progress_mode == "determinate":
                self.progressbar.configure(mode="determinate")
            else:
                self.progressbar.configure(mode="indeterminate")
                self.progressbar.start(10)
            self.status_chip.configure(bg="#145a93")
        else:
            self.progressbar.stop()
            self.progressbar.configure(mode="indeterminate", value=0)
            self.progress_text_var.set("-")
            self._progress_mode = "idle"
            self._progress_total = 0
            self._progress_current = 0
            self.status_chip.configure(bg="#1a3558")
        self._refresh_operation_buttons()

    def _prepare_progress(self, total_steps: int) -> None:
        self._progress_mode = "determinate"
        self._progress_total = max(1, total_steps)
        self._progress_current = 0
        self.progressbar.configure(mode="determinate", maximum=100, value=0)
        self.progress_text_var.set("0%")

    def _apply_progress_message(self, message: str) -> None:
        # message format: __PROGRESS__|current|total|operation|item_name
        parts = message.split("|", 4)
        if len(parts) != 5:
            return
        try:
            current = int(parts[1])
            total = max(1, int(parts[2]))
        except ValueError:
            return
        self._progress_total = total
        self._progress_current = max(0, min(current, total))
        percent = (self._progress_current / self._progress_total) * 100
        self.progressbar.configure(mode="determinate", maximum=100, value=percent)
        self.progress_text_var.set(f"{percent:.0f}%")

    def _t(self, key: str, **kwargs: object) -> str:
        template = LOCALE_DATA[self.locale_var.get()][key]
        if kwargs:
            return template.format(**kwargs)
        return template

    def _apply_locale(self) -> None:
        self.title(self._t("title"))
        self.hero_title.configure(text=self._t("hero_primary"))
        self.hero_subtitle.configure(text=self._t("hero_secondary"))
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
        self.metrics_title.configure(text=self._t("stat_entries"))
        self.actions_title.configure(text=self._t("actions_title"))
        self.content_title.configure(text=self._t("content_title"))
        self.log_title.configure(text=self._t("operation_log"))
        self.metric_entries_caption.configure(text=self._t("stat_entries"))
        self.metric_selected_caption.configure(text=self._t("stat_selected"))
        self.metric_target_caption.configure(text=self._t("stat_target"))
        getattr(self, "_paths_title_var").set(self._t("paths_title"))
        self.tree.heading("kind", text=self._t("type"))
        self.tree.heading("app_id", text=self._t("app_id"))
        self.tree.heading("name", text=self._t("game"))
        self.tree.heading("backup_time", text=self._time_column_label())
        self.tree.heading("size", text=self._t("size"))
        self.tree.heading("source", text=self._t("source_col"))
        self.window_title_label.configure(text=self._t("title"))
        self.status_var.set(self._t("status_ready"))
        if self.current_view == "installed":
            self.mode_var.set(self._t("mode_installed"))
        elif self.current_view == "repository":
            self.mode_var.set(self._t("mode_repository"))
        else:
            self.mode_var.set("-")
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
                        self._display_time_value(backup),
                        format_bytes(backup.required_bytes),
                        str(backup.source_path),
                    ),
                )
            self.tree.selection_set(list(selected_ids))

    def _display_time_value(self, backup: GameBackup) -> str:
        if backup.kind is BackupKind.INSTALLED_GAME:
            return self._display_iso_time(backup.last_updated_time)
        return self._display_iso_time(backup.backup_time)

    def _display_iso_time(self, value: str | None) -> str:
        if not value:
            return "-"
        try:
            return datetime.fromisoformat(value).strftime("%Y-%m-%d %H:%M")
        except ValueError:
            return value

    def _time_column_label(self) -> str:
        if self.current_view == "installed":
            return self._t("updated_time")
        return self._t("backup_time")

    def _no_selection_message(self) -> str:
        if self.current_view == "repository":
            return self._t("no_repository_selection")
        return self._t("no_installed_selection")

    def _start_window_drag(self, event: tk.Event) -> None:
        self._drag_offset_x = event.x_root - self.winfo_x()
        self._drag_offset_y = event.y_root - self.winfo_y()

    def _on_window_drag(self, event: tk.Event) -> None:
        if self._is_maximized:
            return
        x = event.x_root - self._drag_offset_x
        y = event.y_root - self._drag_offset_y

        left, top, right, bottom = self._get_work_area()
        width = self.winfo_width()
        height = self.winfo_height()

        min_x = left
        max_x = max(left, right - width)
        min_y = top
        max_y = max(top, bottom - height)

        x = max(min_x, min(x, max_x))
        y = max(min_y, min(y, max_y))

        snap_distance = 14
        if abs(x - left) <= snap_distance:
            x = left
        elif abs((x + width) - right) <= snap_distance:
            x = right - width

        if abs(y - top) <= snap_distance:
            y = top
        elif abs((y + height) - bottom) <= snap_distance:
            y = bottom - height

        self.geometry(f"+{x}+{y}")

    def _minimize_window(self) -> None:
        self.overrideredirect(False)
        self.iconify()

    def _toggle_maximize(self) -> None:
        if self._is_maximized:
            if self._restore_geometry:
                self.geometry(self._restore_geometry)
            self._is_maximized = False
            self.max_button.configure(text="□")
            return

        self._restore_geometry = self.geometry()
        left, top, right, bottom = self._get_work_area()
        width = max(200, right - left)
        height = max(200, bottom - top)
        self.geometry(f"{width}x{height}+{left}+{top}")
        self._is_maximized = True
        self.max_button.configure(text="❐")

    def _on_window_map(self, _: tk.Event) -> None:
        if self.state() == "normal":
            self.overrideredirect(True)

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
