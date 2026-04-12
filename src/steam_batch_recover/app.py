from __future__ import annotations

import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .models import GameBackup
from .restorer import get_free_space_bytes, restore_backups
from .scanner import scan_backups


def run_app() -> None:
    app = SteamBatchRecoverApp()
    app.mainloop()


class SteamBatchRecoverApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Steam Game Batch Recover")
        self.geometry("1180x720")
        self.minsize(980, 620)

        self.source_var = tk.StringVar()
        self.destination_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Ready")
        self.summary_var = tk.StringVar(value="No scan yet")
        self.space_var = tk.StringVar(value="Required: 0 B | Free: N/A")
        self.overwrite_var = tk.BooleanVar(value=False)

        self.backups: list[GameBackup] = []

        self._build_layout()

    def _build_layout(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        controls = ttk.Frame(self, padding=12)
        controls.grid(row=0, column=0, sticky="ew")
        controls.columnconfigure(1, weight=1)

        ttk.Label(controls, text="Source path").grid(row=0, column=0, sticky="w", pady=(0, 8))
        ttk.Entry(controls, textvariable=self.source_var).grid(row=0, column=1, sticky="ew", padx=8, pady=(0, 8))
        ttk.Button(controls, text="Browse", command=self._browse_source).grid(row=0, column=2, sticky="ew", pady=(0, 8))

        ttk.Label(controls, text="Destination path").grid(row=1, column=0, sticky="w", pady=(0, 8))
        ttk.Entry(controls, textvariable=self.destination_var).grid(row=1, column=1, sticky="ew", padx=8, pady=(0, 8))
        ttk.Button(controls, text="Browse", command=self._browse_destination).grid(row=1, column=2, sticky="ew", pady=(0, 8))

        actions = ttk.Frame(controls)
        actions.grid(row=2, column=0, columnspan=3, sticky="ew")
        actions.columnconfigure(5, weight=1)

        ttk.Button(actions, text="Scan", command=self._scan).grid(row=0, column=0, padx=(0, 8))
        ttk.Button(actions, text="Select All", command=self._select_all).grid(row=0, column=1, padx=(0, 8))
        ttk.Button(actions, text="Clear Selection", command=self._clear_selection).grid(row=0, column=2, padx=(0, 8))
        ttk.Button(actions, text="Restore Selected", command=self._restore_selected).grid(row=0, column=3, padx=(0, 8))
        ttk.Checkbutton(actions, text="Overwrite existing files", variable=self.overwrite_var).grid(row=0, column=4, padx=(0, 8))
        ttk.Label(actions, textvariable=self.status_var).grid(row=0, column=5, sticky="e")

        center = ttk.Frame(self, padding=(12, 0, 12, 12))
        center.grid(row=1, column=0, sticky="nsew")
        center.columnconfigure(0, weight=3)
        center.columnconfigure(1, weight=2)
        center.rowconfigure(0, weight=1)

        columns = ("kind", "app_id", "name", "size", "source")
        self.tree = ttk.Treeview(center, columns=columns, show="headings", selectmode="extended")
        self.tree.grid(row=0, column=0, sticky="nsew")
        self.tree.heading("kind", text="Type")
        self.tree.heading("app_id", text="App ID")
        self.tree.heading("name", text="Game")
        self.tree.heading("size", text="Required")
        self.tree.heading("source", text="Source")
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

        progress = ttk.Progressbar(log_panel, mode="indeterminate")
        progress.grid(row=3, column=0, sticky="ew", pady=(8, 0))
        self.progressbar = progress

    def _browse_source(self) -> None:
        selected = filedialog.askdirectory(title="Choose backup source folder")
        if selected:
            self.source_var.set(selected)

    def _browse_destination(self) -> None:
        selected = filedialog.askdirectory(title="Choose restore destination")
        if selected:
            self.destination_var.set(selected)
            self._refresh_space_summary()

    def _scan(self) -> None:
        source_text = self.source_var.get().strip()
        if not source_text:
            messagebox.showerror("Missing source", "Choose a source path first.")
            return

        source_path = Path(source_text)
        self._set_busy(True, "Scanning...")
        threading.Thread(target=self._scan_worker, args=(source_path,), daemon=True).start()

    def _scan_worker(self, source_path: Path) -> None:
        try:
            backups = scan_backups(source_path)
        except Exception as exc:
            self.after(0, lambda: self._scan_failed(exc))
            return
        self.after(0, lambda: self._scan_completed(backups))

    def _scan_failed(self, exc: Exception) -> None:
        self._set_busy(False, "Scan failed")
        messagebox.showerror("Scan failed", str(exc))

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
                    backup.kind.value,
                    backup.app_id,
                    backup.name,
                    format_bytes(backup.required_bytes),
                    str(backup.source_path),
                ),
            )

        self.summary_var.set(f"Detected {len(backups)} backups")
        self._refresh_space_summary()
        self._append_log(f"Scan complete. Found {len(backups)} backup entries.")
        self._set_busy(False, "Ready")

    def _select_all(self) -> None:
        item_ids = self.tree.get_children()
        self.tree.selection_set(item_ids)
        self._refresh_space_summary()

    def _clear_selection(self) -> None:
        self.tree.selection_remove(self.tree.selection())
        self._refresh_space_summary()

    def _restore_selected(self) -> None:
        selection = self._selected_backups()
        if not selection:
            messagebox.showinfo("No selection", "Select at least one game to restore.")
            return

        destination_text = self.destination_var.get().strip()
        if not destination_text:
            messagebox.showerror("Missing destination", "Choose a destination path first.")
            return

        destination = Path(destination_text)
        required_bytes = sum(item.required_bytes for item in selection)
        free_bytes = get_free_space_bytes(destination)
        if free_bytes < required_bytes:
            messagebox.showerror(
                "Insufficient space",
                f"Required {format_bytes(required_bytes)}, but only {format_bytes(free_bytes)} is available.",
            )
            return

        self._set_busy(True, "Restoring...")
        self._append_log(f"Starting restore of {len(selection)} item(s) to {destination}")
        threading.Thread(
            target=self._restore_worker,
            args=(selection, destination, self.overwrite_var.get()),
            daemon=True,
        ).start()

    def _restore_worker(self, selection: list[GameBackup], destination: Path, overwrite: bool) -> None:
        try:
            restore_backups(selection, destination, overwrite, self._queue_log)
        except Exception as exc:
            self.after(0, lambda: self._restore_failed(exc))
            return
        self.after(0, self._restore_completed)

    def _restore_failed(self, exc: Exception) -> None:
        self._set_busy(False, "Restore failed")
        messagebox.showerror("Restore failed", str(exc))

    def _restore_completed(self) -> None:
        self._set_busy(False, "Ready")
        self._append_log("Restore completed.")
        self._refresh_space_summary()
        messagebox.showinfo("Finished", "Selected backups have been processed.")

    def _queue_log(self, message: str) -> None:
        self.after(0, lambda: self._append_log(message))

    def _append_log(self, message: str) -> None:
        self.log_text.configure(state="normal")
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _refresh_space_summary(self) -> None:
        selected = self._selected_backups()
        required_bytes = sum(item.required_bytes for item in selected)
        destination_text = self.destination_var.get().strip()
        if destination_text:
            try:
                free_bytes = get_free_space_bytes(Path(destination_text))
                free_text = format_bytes(free_bytes)
            except OSError:
                free_text = "Unavailable"
        else:
            free_text = "N/A"

        self.space_var.set(f"Required: {format_bytes(required_bytes)} | Free: {free_text}")
        if self.backups:
            self.summary_var.set(f"Detected {len(self.backups)} backups | Selected {len(selected)}")
        else:
            self.summary_var.set("No scan yet")

    def _selected_backups(self) -> list[GameBackup]:
        selected_ids = set(self.tree.selection())
        return [backup for backup in self.backups if self._row_id(backup) in selected_ids]

    def _set_busy(self, busy: bool, status: str) -> None:
        self.status_var.set(status)
        if busy:
            self.progressbar.start(10)
        else:
            self.progressbar.stop()

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
