from __future__ import annotations

import ctypes
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
    manual_takeover_seconds: float = 15.0
    cursor_move_speed_pixels_per_sec: float = 500.0
    cursor_hover_pause_seconds: float = 0.2
    menu_hover_maintain_interval_seconds: float = 0.5


class SteamGuiAutomator:
    def __init__(self, templates_root: Path, settings: SteamGuiSettings | None = None) -> None:
        self.templates_root = templates_root
        self.settings = settings or SteamGuiSettings()
        self._progress_callback = None
        self._template_anchor_cache: dict[str, tuple[float, float]] = {}
        self._template_match_cache: dict[str, np.ndarray] = {}
        self._missing_template_reported: set[str] = set()
        _enable_dpi_awareness()
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.15

    def run_batch_restore(
        self,
        steam_executable: Path,
        backup_paths: list[Path],
        on_progress: callable | None = None,
        steam_already_running: bool = False,
        start_from_restore_wizard: bool = False,
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
            self._run_single_restore(backup_path, on_progress, start_from_restore_wizard=start_from_restore_wizard)
            start_from_restore_wizard = False

    def _focus_steam_window(self, on_progress: callable | None) -> None:
        # First check if Steam process is running at all.
        if not self._check_steam_running():
            self._emit(on_progress, "Steam process not detected in taskbar. Checking window by title...")

        try:
            windows = pygetwindow.getWindowsWithTitle("Steam")
            if windows:
                win = windows[0]
                if win.isMinimized:
                    self._emit(on_progress, "Steam window is minimized. Restoring...")
                    win.restore()
                try:
                    win.moveTo(0, 0)
                except Exception:
                    pass
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

    def _run_single_restore(self, backup_path: Path, on_progress: callable | None, start_from_restore_wizard: bool = False) -> None:
        try:
            self._focus_steam_window(on_progress)
            if not start_from_restore_wizard:
                menu_region = self._top_left_region()
                menu_clicked = self._open_steam_menu(menu_region)
                if not menu_clicked:
                    self._wait_for_restore_wizard_manual(on_progress)
                else:
                    # Find the menu center to maintain menu hover during restore item search.
                    menu_loc = self._locate_with_multiscale(
                        self.templates_root / "en_03_SteamMenu_TopLeft.png", region=menu_region
                    ) or self._locate_with_multiscale(
                        self.templates_root / "en_03_SteamMenu_TopLeft_PART.png", region=menu_region
                    )
                    menu_center = (None, None)
                    if menu_loc:
                        center = (menu_loc["click"][0], menu_loc["click"][1])
                        menu_center = (center[0], center[1] + 60, menu_region)  # Offset to menu hover area

                    restore_clicked = self._click_first_optional(
                        [
                            "en_05_Game_Restore.png",
                            "en_05_Game_Restore_PART.png",
                            "en_06_Game_RestoreClick.png.png",
                        ],
                        "Restore Game Backup menu item",
                        timeout_seconds=8.0,
                        region=menu_region,
                        maintain_menu_position=menu_center if menu_center[0] is not None else None,
                    )
                    if not restore_clicked:
                        self._emit(on_progress, "Restore menu item not matched. Switching to manual wizard takeover.")
                        self._wait_for_restore_wizard_manual(on_progress)
            else:
                self._emit(on_progress, "Starting from manually opened restore wizard.")

            self._click_first_optional(
                ["en_07_Find_backup_path.png", "en_06_Find_backup_path.png", "en_06_Find_backup_path_PART.png"],
                "Find backup path title",
                timeout_seconds=8.0,
            )
            browse_clicked = self._click_first_optional(["en_08_browse_path.png", "en_09_browse_pathClick.png"], "Browse button", timeout_seconds=6.0)
            if not browse_clicked:
                self._emit(on_progress, "Browse button not matched; trying keyboard fallback Alt+B")
                pyautogui.hotkey("alt", "b")
                time.sleep(self.settings.post_click_pause_seconds)
            self._click_first(["en_11_file_explorer_path_input.png", "en_7_file_explorer_path_input.png"], "File explorer path input")

            pyautogui.hotkey("ctrl", "a")
            pyautogui.typewrite(str(backup_path), interval=0.01)
            pyautogui.press("enter")
            time.sleep(self.settings.post_click_pause_seconds)

            self._click_first(["en_12_select_folder.png", "en_8_select_folder.png"], "Select Folder")
            self._click_first(
                [
                    "en_13_Start_restore.png",
                    "en_9_Start_restore.png",
                    "en_14_Start_restore-backup.png",
                    "en_10_Start_restore-backup.png",
                    "en_15_Start_restore-backupClick.png",
                ],
                "Restore button",
            )

            # Optional EULA acceptance step.
            self._click_first_optional(["en_16_EULA_agree_optional.png", "en_17_EULA_agree_Accept_optional.png", "en_18_EULA_agree_AcceptClick_optional.png"], "Optional EULA accept")

            # Wait until the Steam menu is visible again as a signal to proceed to next item.
            self._wait_for_any(
                ["en_03_SteamMenu_TopLeft.png", "en_03_SteamMenu_TopLeft_PART.png", "en_04_SteamMenuClick_TopLeft.png"],
                self.settings.restore_wait_timeout_seconds,
                "Steam main window after restore",
            )
            self._emit(on_progress, "Restore step completed, moving to next item.")
        except pyautogui.FailSafeException as exc:
            raise SteamGuiAutomationError(auto_fail_safe_message) from exc

    def _check_steam_running(self) -> bool:
        """Check if Steam process is running on Windows."""
        try:
            result = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq steam.exe"],
                capture_output=True,
                text=True,
                timeout=3,
            )
            return "steam.exe" in result.stdout.lower()
        except Exception:
            return False

    def _smooth_move_to(self, target_x: int, target_y: int) -> None:
        """Move cursor smoothly from current position to target based on configured speed."""
        current = pyautogui.position()
        dist_x = target_x - current.x
        dist_y = target_y - current.y
        distance = (dist_x**2 + dist_y**2) ** 0.5

        if distance < 1:
            return

        # Calculate duration based on configured speed (pixels per second).
        duration = distance / max(self.settings.cursor_move_speed_pixels_per_sec, 100)
        pyautogui.moveTo(target_x, target_y, duration=duration)

    def _maintain_menu_hover(self, menu_center_x: int, menu_center_y: int, menu_region: tuple[int, int, int, int]) -> None:
        """Periodically re-hover over the menu dropdown area to keep menu active."""
        hover_x = min(menu_center_x + 24, menu_region[0] + menu_region[2] - 10)
        hover_y = min(menu_center_y + 90, menu_region[1] + menu_region[3] - 10)
        self._smooth_move_to(hover_x, hover_y)
        time.sleep(0.05)

    def _open_steam_menu(self, menu_region: tuple[int, int, int, int]) -> bool:
        self._emit(self._progress_callback, "Opening Steam menu and hovering into dropdown area.")
        found = self._wait_for_any(
            ["en_03_SteamMenu_TopLeft.png", "en_03_SteamMenu_TopLeft_PART.png", "en_04_SteamMenuClick_TopLeft.png"],
            10.0,
            "Steam top-left menu",
            raise_on_timeout=False,
            region=menu_region,
        )
        if found is None:
            return False

        center = pyautogui.center(found)
        self._smooth_move_to(center.x, center.y)
        pyautogui.click()
        time.sleep(0.25)

        # Move cursor into dropdown area and keep it there.
        hover_x = min(center.x + 24, menu_region[0] + menu_region[2] - 10)
        hover_y = min(center.y + 90, menu_region[1] + menu_region[3] - 10)
        self._smooth_move_to(hover_x, hover_y)
        time.sleep(self.settings.post_click_pause_seconds)
        self._emit(self._progress_callback, f"Steam menu hover hold at x={hover_x}, y={hover_y}")
        return True

    def _wait_for_restore_wizard_manual(self, on_progress: callable | None) -> None:
        self._emit(
            on_progress,
            "Manual takeover: open Steam > Restore Game Backup... yourself now. Waiting for restore wizard for 20 seconds...",
        )
        found = self._wait_for_any(
            [
                "en_07_Find_backup_path.png",
                "en_06_Find_backup_path.png",
                "en_06_Find_backup_path_PART.png",
                "en_08_browse_path.png",
                "en_09_browse_pathClick.png",
            ],
            max(20.0, self.settings.manual_takeover_seconds),
            "Restore wizard during manual takeover",
            raise_on_timeout=False,
        )
        if found is None:
            raise SteamGuiAutomationError(
                "Manual takeover timed out. Steam restore wizard did not appear. Please open 'Steam > Restore Game Backup...' during the takeover window."
            )
        self._emit(on_progress, "Restore wizard detected after manual takeover.")

    def _click_first(self, image_names: list[str], step_name: str, region: tuple[int, int, int, int] | None = None) -> None:
        self._emit(self._progress_callback, f"Waiting for step: {step_name} | templates={image_names}")
        found = self._wait_for_any(image_names, self.settings.step_timeout_seconds, step_name, region=region)
        if found is None:
            raise SteamGuiAutomationError(f"Could not find {step_name} on screen.")

        click_x, click_y = found["click"]
        self._emit(
            self._progress_callback,
            f"Matched {step_name} via {found['template']} at x={click_x}, y={click_y}, score={found['score']:.3f}",
        )
        # Smooth movement to target, brief hover, then click.
        self._smooth_move_to(click_x, click_y)
        time.sleep(self.settings.cursor_hover_pause_seconds)
        pyautogui.click()
        time.sleep(self.settings.post_click_pause_seconds)

    def _click_first_optional(
        self,
        image_names: list[str],
        step_name: str,
        timeout_seconds: float = 3.0,
        region: tuple[int, int, int, int] | None = None,
        maintain_menu_position: tuple[int, int, tuple[int, int, int, int]] | None = None,
    ) -> bool:
        self._emit(self._progress_callback, f"Waiting optional step: {step_name} | templates={image_names}")
        found = self._wait_for_any(
            image_names,
            timeout_seconds,
            step_name,
            raise_on_timeout=False,
            region=region,
            maintain_menu_position=maintain_menu_position,
        )
        if found is None:
            return False
        click_x, click_y = found["click"]
        self._emit(
            self._progress_callback,
            f"Matched optional {step_name} via {found['template']} at x={click_x}, y={click_y}, score={found['score']:.3f}",
        )
        # Smooth movement to target, brief hover, then click.
        self._smooth_move_to(click_x, click_y)
        time.sleep(self.settings.cursor_hover_pause_seconds)
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
        maintain_menu_position: tuple[int, int, tuple[int, int, int, int]] | None = None,
    ):
        """
        maintain_menu_position: tuple of (menu_center_x, menu_center_y, menu_region) to keep menu active.
        """
        deadline = time.monotonic() + timeout_seconds
        last_maintain_time = time.monotonic()

        while time.monotonic() < deadline:
            # Periodically re-hover menu to keep dropdown active.
            if maintain_menu_position is not None:
                now = time.monotonic()
                if now - last_maintain_time >= self.settings.menu_hover_maintain_interval_seconds:
                    menu_center_x, menu_center_y, menu_region = maintain_menu_position
                    self._maintain_menu_hover(menu_center_x, menu_center_y, menu_region)
                    last_maintain_time = now

            for image_name in image_names:
                template = self.templates_root / image_name
                if not template.exists():
                    key = str(template)
                    if key not in self._missing_template_reported:
                        self._missing_template_reported.add(key)
                        self._emit(self._progress_callback, f"Template missing: {template}")
                    continue
                try:
                    found = self._locate_with_multiscale(template, region=region)
                except Exception:
                    found = None
                if found is not None:
                    self._emit(
                        self._progress_callback,
                        f"Template matched: {template.name} score={found['score']:.3f} click=({found['click'][0]},{found['click'][1]})",
                    )
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

        template = self._get_match_template(template_path)
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
        abs_left = left + offset_x
        abs_top = top + offset_y
        ratio_x, ratio_y = self._get_click_anchor_ratio(template_path)
        click_x = int(abs_left + width * ratio_x)
        click_y = int(abs_top + height * ratio_y)

        return {
            "template": template_path.name,
            "score": float(best_score),
            "box": (abs_left, abs_top, width, height),
            "click": (click_x, click_y),
        }

    def _get_match_template(self, template_path: Path) -> np.ndarray | None:
        key = str(template_path)
        cached = self._template_match_cache.get(key)
        if cached is not None:
            return cached

        color_template = cv2.imread(str(template_path), cv2.IMREAD_COLOR)
        if color_template is None:
            return None

        gray_template = cv2.cvtColor(color_template, cv2.COLOR_BGR2GRAY)

        # Non-PART templates are annotated full screenshots; use red-box ROI as the matching patch.
        if not template_path.stem.upper().endswith("_PART"):
            bounds = self._extract_red_box_bounds(color_template)
            if bounds is not None:
                x1, y1, x2, y2 = bounds
                crop = gray_template[y1:y2, x1:x2]
                if crop.size > 0:
                    self._template_match_cache[key] = crop
                    self._template_anchor_cache[key] = (0.5, 0.5)
                    return crop

        self._template_match_cache[key] = gray_template
        return gray_template

    def _extract_red_box_bounds(self, color_template: np.ndarray) -> tuple[int, int, int, int] | None:
        hsv = cv2.cvtColor(color_template, cv2.COLOR_BGR2HSV)
        mask1 = cv2.inRange(hsv, (0, 90, 90), (10, 255, 255))
        mask2 = cv2.inRange(hsv, (160, 90, 90), (179, 255, 255))
        red_mask = cv2.bitwise_or(mask1, mask2)

        contours, _ = cv2.findContours(red_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return None

        contour = max(contours, key=cv2.contourArea)
        area = cv2.contourArea(contour)
        if area < 40:
            return None

        x, y, w, h = cv2.boundingRect(contour)
        if w < 8 or h < 8:
            return None

        # Trim border thickness by 1px where possible.
        x1 = x + 1 if w > 2 else x
        y1 = y + 1 if h > 2 else y
        x2 = x + w - 1 if w > 2 else x + w
        y2 = y + h - 1 if h > 2 else y + h
        return (x1, y1, x2, y2)

    def _get_click_anchor_ratio(self, template_path: Path) -> tuple[float, float]:
        key = str(template_path)
        cached = self._template_anchor_cache.get(key)
        if cached is not None:
            return cached

        # Rule 1: *_PART uses object center.
        if template_path.stem.upper().endswith("_PART"):
            ratio = (0.5, 0.5)
            self._template_anchor_cache[key] = ratio
            return ratio

        # Rule 2: non-PART uses red-box center in the annotated template.
        color_template = cv2.imread(str(template_path), cv2.IMREAD_COLOR)
        if color_template is None:
            ratio = (0.5, 0.5)
            self._template_anchor_cache[key] = ratio
            return ratio

        hsv = cv2.cvtColor(color_template, cv2.COLOR_BGR2HSV)
        mask1 = cv2.inRange(hsv, (0, 80, 80), (10, 255, 255))
        mask2 = cv2.inRange(hsv, (160, 80, 80), (179, 255, 255))
        red_mask = cv2.bitwise_or(mask1, mask2)

        ys, xs = np.where(red_mask > 0)
        if len(xs) < 10:
            ratio = (0.5, 0.5)
            self._template_anchor_cache[key] = ratio
            return ratio

        min_x, max_x = int(xs.min()), int(xs.max())
        min_y, max_y = int(ys.min()), int(ys.max())
        center_x = (min_x + max_x) / 2.0
        center_y = (min_y + max_y) / 2.0

        h, w = color_template.shape[:2]
        ratio = (
            max(0.0, min(1.0, center_x / max(1, w - 1))),
            max(0.0, min(1.0, center_y / max(1, h - 1))),
        )
        self._template_anchor_cache[key] = ratio
        return ratio

    def _top_left_region(self) -> tuple[int, int, int, int]:
        screen = pyautogui.size()
        return (0, 0, int(screen.width * 0.55), int(screen.height * 0.55))


def _enable_dpi_awareness() -> None:
    # Keep screen-capture coordinates and mouse coordinates in the same pixel space.
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

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
