from __future__ import annotations

import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
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
    min_scale: float = 0.7
    max_scale: float = 1.3
    scale_step: float = 0.06


class SteamGuiAutomator:
    def __init__(self, templates_root: Path, settings: SteamGuiSettings | None = None) -> None:
        self.templates_root = templates_root
        self.settings = settings or SteamGuiSettings()
        self._progress_callback = None
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.15

    def run_batch_restore(
        self,
        steam_executable: Path,
        backup_paths: list[Path],
        on_progress: callable | None = None,
        steam_already_running: bool = False,
    ) -> None:
        self._progress_callback = on_progress
        if not backup_paths:
            raise SteamGuiAutomationError("No backup path selected.")

        try:
            screenshot = pyautogui.screenshot()
        except Exception as exc:  # noqa: BLE001
            raise SteamGuiAutomationError(
                "Screenshot backend initialization failed. Please rebuild using updated dependencies (pillow/pyscreeze) and hidden-import settings."
            ) from exc
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
                self._emit(on_progress, "Steam window not found by title. Trying taskbar fallback...")
                self._try_activate_from_taskbar(on_progress)
        except Exception as exc:
            self._emit(on_progress, f"Window focus attempt failed (non-fatal): {exc}")
            self._try_activate_from_taskbar(on_progress)

    def _try_activate_from_taskbar(self, on_progress: callable | None) -> None:
        # Auto-hidden taskbar needs a mouse move to screen bottom before template matching.
        screen = pyautogui.size()
        pyautogui.moveTo(screen.width // 2, max(1, screen.height - 2), duration=0.15)
        time.sleep(0.4)

        clicked = self._click_first_optional(
            [
                "en_02_TaskBarSteamIcon.png",
                "en_0_EULA_minimized.png",
            ],
            "Steam icon on taskbar",
            timeout_seconds=4.0,
        )
        if clicked:
            time.sleep(0.8)
            try:
                windows = pygetwindow.getWindowsWithTitle("Steam")
                if windows:
                    windows[0].activate()
                    self._emit(on_progress, "Steam activated from taskbar fallback.")
                    return
            except Exception:
                pass
        self._emit(on_progress, "Taskbar fallback did not activate Steam window.")

    def _run_single_restore(self, backup_path: Path, on_progress: callable | None) -> None:
        try:
            self._focus_steam_window(on_progress)
            menu_region = self._top_left_region()
            menu_clicked = self._click_first_optional(
                ["en_03_SteamMenu_TopLeft.png", "en_04_SteamMenuClick_TopLeft.png"],
                "Steam top-left menu",
                timeout_seconds=10.0,
                region=menu_region,
            )
            if not menu_clicked:
                self._emit(on_progress, "Top-left Steam menu not matched, trying keyboard fallback Alt+S")
                pyautogui.hotkey("alt", "s")
                time.sleep(self.settings.post_click_pause_seconds)

            if not self._open_restore_wizard(menu_region):
                self._click_first(
                    ["en_05_Game_Restore.png", "en_06_Game_RestoreClick.png.png"],
                    "Restore Game Backup menu item",
                    region=menu_region,
                )
            self._click_first_optional(["en_07_Find_backup_path.png"], "Find backup path title", timeout_seconds=8.0)
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

    def _open_restore_wizard(self, menu_region: tuple[int, int, int, int]) -> bool:
        # Keyboard-first fallback for UI/theme/scale drift in menu templates.
        sequences = [
            ("alt+s", "r"),
            ("alt+s", "b"),
        ]
        for hotkey, follow_key in sequences:
            self._emit(self._progress_callback, f"Trying keyboard sequence: {hotkey} then {follow_key}")
            keys = hotkey.split("+")
            if len(keys) == 2:
                pyautogui.hotkey(keys[0], keys[1])
            else:
                pyautogui.press(hotkey)
            time.sleep(0.5)
            pyautogui.press(follow_key)
            time.sleep(1.0)

            if self._wait_for_any(
                ["en_07_Find_backup_path.png", "en_08_browse_path.png", "en_09_browse_pathClick.png"],
                3.0,
                "Restore wizard entry after keyboard sequence",
                raise_on_timeout=False,
            ) is not None:
                self._emit(self._progress_callback, "Restore wizard opened via keyboard sequence.")
                return True

            # Re-open menu before trying the next sequence.
            self._click_first_optional(
                ["en_03_SteamMenu_TopLeft.png", "en_04_SteamMenuClick_TopLeft.png"],
                "Steam top-left menu retry",
                timeout_seconds=3.0,
                region=menu_region,
            )

        self._emit(self._progress_callback, "Keyboard sequences did not open restore wizard; falling back to template click.")
        return False

    def _click_first(self, image_names: list[str], step_name: str, region: tuple[int, int, int, int] | None = None) -> None:
        self._emit(self._progress_callback, f"Waiting for step: {step_name} | templates={image_names}")
        found = self._wait_for_any(image_names, self.settings.step_timeout_seconds, step_name, region=region)
        if found is None:
            raise SteamGuiAutomationError(f"Could not find {step_name} on screen.")

        center = pyautogui.center(found)
        self._emit(self._progress_callback, f"Matched {step_name} at x={center.x}, y={center.y}")
        pyautogui.moveTo(center.x, center.y, duration=0.15)
        pyautogui.click()
        time.sleep(self.settings.post_click_pause_seconds)

    def _click_first_optional(
        self,
        image_names: list[str],
        step_name: str,
        timeout_seconds: float = 3.0,
        region: tuple[int, int, int, int] | None = None,
    ) -> bool:
        self._emit(self._progress_callback, f"Waiting optional step: {step_name} | templates={image_names}")
        found = self._wait_for_any(image_names, timeout_seconds, step_name, raise_on_timeout=False, region=region)
        if found is None:
            return False
        center = pyautogui.center(found)
        self._emit(self._progress_callback, f"Matched optional {step_name} at x={center.x}, y={center.y}")
        pyautogui.moveTo(center.x, center.y, duration=0.15)
        pyautogui.click()
        time.sleep(self.settings.post_click_pause_seconds)
        return True

    def _wait_for_any(
        self,
        image_names: list[str],
        timeout_seconds: float,
        step_name: str,
        raise_on_timeout: bool = True,
        region: tuple[int, int, int, int] | None = None,
    ):
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            for image_name in image_names:
                template = self.templates_root / image_name
                if not template.exists():
                    self._emit(self._progress_callback, f"Template missing: {template}")
                    continue
                try:
                    found = self._locate_with_multiscale(template, region=region)
                except Exception:
                    found = None
                if found is not None:
                    self._emit(self._progress_callback, f"Template matched: {template.name}")
                    return found
            time.sleep(0.3)

        screenshot_path = None
        if self.settings.debug_screenshots:
            screenshot_path = self._save_debug_screenshot(step_name)
            if screenshot_path is not None:
                self._emit(self._progress_callback, f"Debug screenshot saved: {screenshot_path}")
        if raise_on_timeout:
            raise SteamGuiAutomationError(f"Timed out while waiting for: {step_name}")
        return None

    def _locate_with_multiscale(self, template_path: Path, region: tuple[int, int, int, int] | None = None):
        screenshot = pyautogui.screenshot()
        screen_bgr = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
        gray_screen = cv2.cvtColor(screen_bgr, cv2.COLOR_BGR2GRAY)

        offset_x = 0
        offset_y = 0
        if region is not None:
            x, y, w, h = region
            x = max(0, x)
            y = max(0, y)
            w = max(1, w)
            h = max(1, h)
            x2 = min(gray_screen.shape[1], x + w)
            y2 = min(gray_screen.shape[0], y + h)
            gray_screen = gray_screen[y:y2, x:x2]
            offset_x = x
            offset_y = y

        template = cv2.imread(str(template_path), cv2.IMREAD_GRAYSCALE)
        if template is None:
            return None

        th, tw = template.shape[:2]
        best_score = -1.0
        best_rect = None

        scale = self.settings.min_scale
        while scale <= self.settings.max_scale + 1e-9:
            rw = max(8, int(tw * scale))
            rh = max(8, int(th * scale))
            if rw >= gray_screen.shape[1] or rh >= gray_screen.shape[0]:
                scale += self.settings.scale_step
                continue

            resized = cv2.resize(template, (rw, rh), interpolation=cv2.INTER_LINEAR)
            result = cv2.matchTemplate(gray_screen, resized, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(result)
            if max_val > best_score:
                best_score = max_val
                best_rect = (max_loc[0], max_loc[1], rw, rh)
            scale += self.settings.scale_step

        if best_rect is None:
            return None
        if best_score < self.settings.confidence:
            return None

        left, top, width, height = best_rect
        # Return a PyAutoGUI-compatible box tuple.
        return (left + offset_x, top + offset_y, width, height)

    def _top_left_region(self) -> tuple[int, int, int, int]:
        screen = pyautogui.size()
        return (0, 0, int(screen.width * 0.55), int(screen.height * 0.55))

    def _save_debug_screenshot(self, step_name: str) -> Path | None:
        try:
            safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in step_name)
            debug_dir = Path(tempfile.gettempdir()) / "SteamBatchRecover_debug"
            debug_dir.mkdir(parents=True, exist_ok=True)
            out_path = debug_dir / f"fail_{safe_name}_{int(time.time())}.png"
            pyautogui.screenshot(str(out_path))
            return out_path
        except Exception:
            return None

    @staticmethod
    def _emit(callback: callable | None, message: str) -> None:
        if callback:
            callback(message)
