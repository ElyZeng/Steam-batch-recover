from __future__ import annotations

import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

import pyautogui
import pygetwindow


auto_fail_safe_message = (
    "PyAutoGUI fail-safe was triggered. Move the mouse away from the top-left corner and retry."
)


class SteamGuiAutomationError(RuntimeError):
    pass


@dataclass(slots=True)
class SteamGuiSettings:
    confidence: float = 0.75
    step_timeout_seconds: float = 30.0
    restore_wait_timeout_seconds: float = 1200.0
    post_click_pause_seconds: float = 0.8
    steam_initial_wait_seconds: float = 8.0
    debug_screenshots: bool = True


class SteamGuiAutomator:
    def __init__(self, templates_root: Path, settings: SteamGuiSettings | None = None) -> None:
        self.templates_root = templates_root
        self.settings = settings or SteamGuiSettings()
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.15

    def run_batch_restore(
        self,
        steam_executable: Path,
        backup_paths: list[Path],
        on_progress: callable | None = None,
        steam_already_running: bool = False,
    ) -> None:
        if not backup_paths:
            raise SteamGuiAutomationError("No backup path selected.")

        screenshot = pyautogui.screenshot()
        self._emit(on_progress, f"Screen capture size: {screenshot.width}x{screenshot.height} (physical pixels)")

        if not steam_already_running:
            self._emit(on_progress, "Launching Steam...")
            try:
                subprocess.Popen([str(steam_executable)], shell=False)
            except OSError as exc:
                raise SteamGuiAutomationError(f"Failed to launch Steam: {exc}") from exc
            time.sleep(self.settings.steam_initial_wait_seconds)

        self._focus_steam_window(on_progress)

        for index, backup_path in enumerate(backup_paths, start=1):
            self._emit(on_progress, f"[{index}/{len(backup_paths)}] Restoring from: {backup_path}")
            self._run_single_restore(backup_path, on_progress)

    def _focus_steam_window(self, on_progress: callable | None) -> None:
        try:
            windows = pygetwindow.getWindowsWithTitle("Steam")
            if windows:
                win = windows[0]
                if win.isMinimized:
                    win.restore()
                win.activate()
                time.sleep(0.5)
                self._emit(on_progress, f"Steam window focused: {win.title!r}")
            else:
                self._emit(on_progress, "Steam window not found by title, proceeding anyway.")
        except Exception as exc:
            self._emit(on_progress, f"Window focus attempt failed (non-fatal): {exc}")

    def _run_single_restore(self, backup_path: Path, on_progress: callable | None) -> None:
        try:
            self._focus_steam_window(on_progress)
            self._click_first(["en_03_SteamMenu_TopLeft.png", "en_04_SteamMenuClick_TopLeft.png"], "Steam top-left menu")
            self._click_first(["en_05_Game_Restore.png", "en_06_Game_RestoreClick.png.png"], "Restore Game Backup menu item")
            self._click_first(["en_08_browse_path.png", "en_09_browse_pathClick.png"], "Browse button")
            self._click_first(["en_11_file_explorer_path_input.png"], "File explorer path input")

            pyautogui.hotkey("ctrl", "a")
            pyautogui.typewrite(str(backup_path), interval=0.01)
            pyautogui.press("enter")
            time.sleep(self.settings.post_click_pause_seconds)

            self._click_first(["en_12_select_folder.png"], "Select Folder")
            self._click_first(["en_13_Start_restore.png", "en_14_Start_restore-backup.png", "en_15_Start_restore-backupClick.png"], "Restore button")

            # Optional EULA acceptance step.
            self._click_first_optional(["en_16_EULA_agree_optional.png", "en_17_EULA_agree_Accept_optional.png", "en_18_EULA_agree_AcceptClick_optional.png"], "Optional EULA accept")

            # Wait until the Steam menu is visible again as a signal to proceed to next item.
            self._wait_for_any(["en_03_SteamMenu_TopLeft.png", "en_04_SteamMenuClick_TopLeft.png"], self.settings.restore_wait_timeout_seconds, "Steam main window after restore")
            self._emit(on_progress, "Restore step completed, moving to next item.")
        except pyautogui.FailSafeException as exc:
            raise SteamGuiAutomationError(auto_fail_safe_message) from exc

    def _click_first(self, image_names: list[str], step_name: str) -> None:
        found = self._wait_for_any(image_names, self.settings.step_timeout_seconds, step_name)
        if found is None:
            raise SteamGuiAutomationError(f"Could not find {step_name} on screen.")

        center = pyautogui.center(found)
        pyautogui.moveTo(center.x, center.y, duration=0.15)
        pyautogui.click()
        time.sleep(self.settings.post_click_pause_seconds)

    def _click_first_optional(self, image_names: list[str], step_name: str) -> None:
        found = self._wait_for_any(image_names, 3.0, step_name, raise_on_timeout=False)
        if found is None:
            return
        center = pyautogui.center(found)
        pyautogui.moveTo(center.x, center.y, duration=0.15)
        pyautogui.click()
        time.sleep(self.settings.post_click_pause_seconds)

    def _wait_for_any(
        self,
        image_names: list[str],
        timeout_seconds: float,
        step_name: str,
        raise_on_timeout: bool = True,
    ):
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            for image_name in image_names:
                template = self.templates_root / image_name
                if not template.exists():
                    continue
                try:
                    found = pyautogui.locateOnScreen(str(template), confidence=self.settings.confidence)
                except Exception:
                    found = None
                if found is not None:
                    return found
            time.sleep(0.3)

        if self.settings.debug_screenshots:
            self._save_debug_screenshot(step_name)
        if raise_on_timeout:
            raise SteamGuiAutomationError(f"Timed out while waiting for: {step_name}")
        return None

    def _save_debug_screenshot(self, step_name: str) -> None:
        try:
            safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in step_name)
            debug_dir = Path(tempfile.gettempdir()) / "SteamBatchRecover_debug"
            debug_dir.mkdir(parents=True, exist_ok=True)
            out_path = debug_dir / f"fail_{safe_name}_{int(time.time())}.png"
            pyautogui.screenshot(str(out_path))
        except Exception:
            pass

    @staticmethod
    def _emit(callback: callable | None, message: str) -> None:
        if callback:
            callback(message)
