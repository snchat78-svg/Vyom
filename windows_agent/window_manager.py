"""
Project : Vyom AI
Version : 1.0
Module  : Window Manager

Purpose:
    Generic Windows top-level window discovery, activation and inspection.

Design:
    No application names are embedded here. A caller supplies a title,
    class, or window handle and the manager discovers the matching window.

Platform:
    Windows runtime only. Importing this module remains safe elsewhere so
    offline tests can run on development machines.
"""

from __future__ import annotations

import ctypes
import os
from ctypes import wintypes
from typing import Any, Dict, List, Optional


class WindowManager:
    """Generic Win32 window discovery and focus control."""

    def __init__(self):
        self.available = os.name == "nt"
        self._user32 = getattr(ctypes, "windll", None).user32 if self.available else None
        if self.available and self._user32 is not None:
            try:
                self._user32.GetForegroundWindow.restype = wintypes.HWND
                self._user32.IsWindow.argtypes = [wintypes.HWND]
                self._user32.IsWindow.restype = wintypes.BOOL
                self._user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
                self._user32.ShowWindow.restype = wintypes.BOOL
                self._user32.BringWindowToTop.argtypes = [wintypes.HWND]
                self._user32.BringWindowToTop.restype = wintypes.BOOL
                self._user32.SetForegroundWindow.argtypes = [wintypes.HWND]
                self._user32.SetForegroundWindow.restype = wintypes.BOOL
            except Exception:
                pass

    @staticmethod
    def _normalize(value: Any) -> str:
        return " ".join(str(value or "").strip().lower().split())

    def is_available(self) -> bool:
        return self.available and self._user32 is not None

    def list_windows(self, include_invisible: bool = False, max_results: int = 200) -> List[Dict[str, Any]]:
        if not self.is_available():
            return []

        user32 = self._user32
        results: List[Dict[str, Any]] = []
        max_results = max(1, int(max_results))

        enum_proc_type = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)

        def callback(hwnd, _lparam):
            try:
                visible = bool(user32.IsWindowVisible(hwnd))
                if not include_invisible and not visible:
                    return True

                length = int(user32.GetWindowTextLengthW(hwnd))
                title_buffer = ctypes.create_unicode_buffer(max(length + 1, 1))
                user32.GetWindowTextW(hwnd, title_buffer, len(title_buffer))
                title = title_buffer.value.strip()

                if not title and not include_invisible:
                    return True

                class_buffer = ctypes.create_unicode_buffer(256)
                user32.GetClassNameW(hwnd, class_buffer, len(class_buffer))

                pid = wintypes.DWORD(0)
                user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))

                results.append({
                    "hwnd": int(hwnd),
                    "title": title,
                    "class_name": class_buffer.value.strip(),
                    "pid": int(pid.value),
                    "visible": visible,
                    "enabled": bool(user32.IsWindowEnabled(hwnd)),
                })

                return len(results) < max_results
            except Exception:
                return True

        user32.EnumWindows(enum_proc_type(callback), 0)
        return results[:max_results]

    def get_foreground(self) -> Optional[Dict[str, Any]]:
        if not self.is_available():
            return None

        hwnd = self._user32.GetForegroundWindow()
        if not hwnd:
            return None

        for item in self.list_windows(include_invisible=True, max_results=500):
            if int(item.get("hwnd", 0)) == int(hwnd):
                return item

        return {"hwnd": int(hwnd), "title": "", "class_name": "", "pid": 0}

    def find(
        self,
        target: Any = "",
        hwnd: Optional[int] = None,
        title: Any = "",
        class_name: Any = "",
        pid: Optional[int] = None,
        max_results: int = 10,
    ) -> List[Dict[str, Any]]:
        if not self.is_available():
            return []

        wanted = self._normalize(target)
        wanted_title = self._normalize(title)
        wanted_class = self._normalize(class_name)
        wanted_pid = int(pid) if pid is not None else None
        wanted_hwnd = int(hwnd) if hwnd is not None else None

        scored = []
        for item in self.list_windows(include_invisible=False, max_results=500):
            score = 0
            item_title = self._normalize(item.get("title"))
            item_class = self._normalize(item.get("class_name"))
            item_pid = int(item.get("pid", 0) or 0)
            item_hwnd = int(item.get("hwnd", 0) or 0)

            if wanted_hwnd is not None:
                if item_hwnd != wanted_hwnd:
                    continue
                score += 1000

            if wanted_pid is not None:
                if item_pid != wanted_pid:
                    continue
                score += 300

            if wanted_title:
                if item_title == wanted_title:
                    score += 600
                elif wanted_title in item_title:
                    score += 300
                else:
                    continue

            if wanted_class:
                if item_class == wanted_class:
                    score += 400
                elif wanted_class in item_class:
                    score += 200
                else:
                    continue

            if wanted:
                if item_title == wanted:
                    score += 500
                elif wanted in item_title:
                    score += 250
                elif wanted in item_class:
                    score += 150
                else:
                    continue

            if not any((wanted, wanted_title, wanted_class, wanted_pid is not None, wanted_hwnd is not None)):
                score = 1

            scored.append((score, item))

        scored.sort(key=lambda pair: (-pair[0], pair[1].get("title", "").lower()))
        return [item for _, item in scored[: max(1, int(max_results))]]

    def activate(self, hwnd: Any) -> Dict[str, Any]:
        if not self.is_available():
            return {"success": False, "stage": "windows_unavailable", "message": "Windows APIs are unavailable."}

        try:
            handle = wintypes.HWND(int(hwnd))
        except (TypeError, ValueError):
            return {"success": False, "stage": "invalid_window", "message": "Invalid window handle."}

        if not self._user32.IsWindow(handle):
            return {"success": False, "stage": "window_not_found", "message": "The requested window no longer exists."}

        try:
            if self._user32.IsIconic(handle):
                self._user32.ShowWindow(handle, 9)  # SW_RESTORE
            self._user32.ShowWindow(handle, 5)      # SW_SHOW
            self._user32.BringWindowToTop(handle)
            focused = bool(self._user32.SetForegroundWindow(handle))
        except Exception as error:
            return {"success": False, "stage": "focus_error", "message": str(error)}

        return {
            "success": focused,
            "stage": "window_focused" if focused else "focus_not_confirmed",
            "window": self.get_foreground(),
            "verification": {
                "verified": focused,
                "verification_level": "state",
                "method": "GetForegroundWindow",
            },
        }

    def focus(
        self,
        target: Any = "",
        hwnd: Optional[int] = None,
        title: Any = "",
        class_name: Any = "",
        pid: Optional[int] = None,
    ) -> Dict[str, Any]:
        matches = self.find(
            target=target,
            hwnd=hwnd,
            title=title,
            class_name=class_name,
            pid=pid,
            max_results=5,
        )
        if not matches:
            return {
                "success": False,
                "stage": "window_not_found",
                "message": "No matching window was found.",
                "target": str(target or title or class_name or hwnd or ""),
            }

        result = self.activate(matches[0]["hwnd"])
        result["matches"] = matches
        return result
