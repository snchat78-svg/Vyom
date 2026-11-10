"""Generic Windows UI state observation for post-action verification.

The observer is application-agnostic and returns only JSON-safe state. It uses
Windows UI Automation when available and remains optional for legacy Win32
paths.
"""

from __future__ import annotations

import ctypes
import os
import time
from typing import Any, Dict, List, Optional

from windows_agent.ui_element_finder import UIElementFinder


class UIStateObserver:
    """Capture observable state before and after a UI action."""

    def __init__(
        self,
        finder: Optional[UIElementFinder] = None,
        max_tree_elements: int = 40,
    ):
        self.finder = finder or UIElementFinder()
        self.max_tree_elements = max(1, int(max_tree_elements))
        self._Desktop = None
        self._user32 = None
        self.available = False

        try:
            if os.name == "nt":
                self._user32 = ctypes.windll.user32
        except Exception:
            self._user32 = None

        try:
            if os.name == "nt":
                from pywinauto import Desktop
                self._Desktop = Desktop
                self.available = True
        except Exception:
            self._Desktop = None

    def is_available(self) -> bool:
        return bool(self.available and self._Desktop is not None)

    @staticmethod
    def _text(value: Any) -> str:
        return " ".join(str(value or "").strip().split())

    @staticmethod
    def _safe_call(obj: Any, method: str, default: Any = None) -> Any:
        try:
            callback = getattr(obj, method, None)
            if callable(callback):
                return callback()
        except Exception:
            pass
        return default

    @classmethod
    def element_state(cls, element: Any) -> Dict[str, Any]:
        if element is None:
            return {"exists": False}

        try:
            wrapper = element.wrapper_object()
        except Exception:
            wrapper = element

        # A non-null wrapper can still refer to a destroyed/recycled UIA
        # element. Ask UIA whether it still exists without waiting.
        try:
            exists_check = getattr(wrapper, "exists", None)
            if callable(exists_check):
                try:
                    alive = exists_check(timeout=0)
                except TypeError:
                    alive = exists_check()
                if alive is False:
                    return {"exists": False}
        except Exception:
            # Not every UIA wrapper exposes exists(); the remaining identity
            # fields are still checked by the pre-dispatch guard.
            pass

        info: Dict[str, Any] = {"exists": True}

        for field, method in (
            ("name", "window_text"),
            ("control_type", "control_type"),
            ("automation_id", "automation_id"),
            ("class_name", "class_name"),
        ):
            value = cls._safe_call(wrapper, method, "")
            info[field] = cls._text(value)

        for field, method in (
            ("enabled", "is_enabled"),
            ("visible", "is_visible"),
            ("focused", "has_keyboard_focus"),
        ):
            value = cls._safe_call(wrapper, method, None)
            if value is None and field == "focused":
                value = cls._safe_call(wrapper, "has_focus", None)
            if value is not None:
                info[field] = bool(value)

        for field, attribute in (("hwnd", "handle"), ("pid", "process_id")):
            try:
                value = getattr(wrapper, attribute, None)
                if callable(value):
                    value = value()
                if value not in (None, ""):
                    info[field] = int(value)
            except Exception:
                pass

        value = None
        for method in ("get_value", "get_edit_text", "value", "window_text"):
            candidate = cls._safe_call(wrapper, method, None)
            # Empty text is a real UI value (for example after clearing an
            # edit control), not missing observation. Keep the first readable
            # value even when it is "" so exact-value verification can work.
            if candidate is not None:
                value = candidate
                break
        if value is not None:
            info["value"] = str(value)

        text = cls._safe_call(wrapper, "window_text", None)
        if text is not None:
            info["text"] = str(text)

        for field, methods in (
            ("selected", ("is_selected", "is_checked")),
            ("toggle_state", ("get_toggle_state", "get_check_state")),
            ("expanded", ("is_expanded",)),
            ("collapsed", ("is_collapsed",)),
        ):
            for method in methods:
                value = cls._safe_call(wrapper, method, None)
                if value is not None:
                    info[field] = bool(value) if isinstance(value, (bool, int)) else str(value)
                    break

        try:
            rect = wrapper.rectangle()
            info["rectangle"] = {
                "left": int(rect.left),
                "top": int(rect.top),
                "right": int(rect.right),
                "bottom": int(rect.bottom),
            }
        except Exception:
            pass

        return info

    def _desktop(self):
        if not self.is_available():
            return None
        return self._Desktop(backend="uia")

    def active_element(self):
        desktop = self._desktop()
        if desktop is None:
            return None
        try:
            return desktop.get_active()
        except Exception:
            return None

    def _top_level(self, element: Any):
        if element is None:
            return None
        try:
            return element.top_level_parent()
        except Exception:
            return None

    def active_window_state(self) -> Dict[str, Any]:
        active = self.active_element()
        if active is None:
            return {"exists": False}
        window = self._top_level(active) or active
        return self.element_state(window)

    @staticmethod
    def _same_active_window(before: Dict[str, Any], after: Dict[str, Any]) -> bool:
        """Return True only when both observations identify the same active window."""
        if not isinstance(before, dict) or not isinstance(after, dict):
            return False
        if before.get("exists") is not True or after.get("exists") is not True:
            return False

        before_hwnd = before.get("hwnd")
        after_hwnd = after.get("hwnd")
        if before_hwnd not in (None, "") or after_hwnd not in (None, ""):
            if before_hwnd in (None, "") or after_hwnd in (None, ""):
                return False
            if str(before_hwnd) != str(after_hwnd):
                return False
            before_pid, after_pid = before.get("pid"), after.get("pid")
            return before_pid in (None, "") or after_pid in (None, "") or str(before_pid) == str(after_pid)

        # Without HWND, require process and title identity; a PID alone can own several windows.
        before_pid, after_pid = before.get("pid"), after.get("pid")
        before_name = UIStateObserver._text(before.get("name"))
        after_name = UIStateObserver._text(after.get("name"))
        if before_pid in (None, "") or after_pid in (None, "") or not before_name or not after_name:
            return False
        if str(before_pid) != str(after_pid) or before_name.casefold() != after_name.casefold():
            return False
        before_class = UIStateObserver._text(before.get("class_name"))
        after_class = UIStateObserver._text(after.get("class_name"))
        return not (before_class and after_class and before_class != after_class)


    def _win32_focused_handle(self) -> int:
        """Return the OS-reported focused child HWND when available."""
        if self._user32 is None:
            return 0

        class GUITHREADINFO(ctypes.Structure):
            _fields_ = [
                ("cbSize", ctypes.c_uint32),
                ("flags", ctypes.c_uint32),
                ("hwndActive", ctypes.c_void_p),
                ("hwndFocus", ctypes.c_void_p),
                ("hwndCapture", ctypes.c_void_p),
                ("hwndMenuOwner", ctypes.c_void_p),
                ("hwndMoveSize", ctypes.c_void_p),
                ("hwndCaret", ctypes.c_void_p),
            ]

        try:
            foreground = self._user32.GetForegroundWindow()
            if not foreground:
                return 0

            process_id = ctypes.c_uint32(0)
            thread_id = self._user32.GetWindowThreadProcessId(
                foreground,
                ctypes.byref(process_id),
            )
            if not thread_id:
                return 0

            info = GUITHREADINFO()
            info.cbSize = ctypes.sizeof(GUITHREADINFO)
            if not self._user32.GetGUIThreadInfo(
                thread_id,
                ctypes.byref(info),
            ):
                return 0

            return int(info.hwndFocus or 0)
        except Exception:
            return 0

    def focused_element_state(self) -> Dict[str, Any]:
        desktop = self._desktop()
        if desktop is None:
            return {"exists": False}

        # Prefer the OS focus handle. This avoids depending on the position of
        # the focused control inside a potentially large UIA descendant tree.
        focused_handle = self._win32_focused_handle()
        if focused_handle:
            try:
                focused = desktop.window(handle=focused_handle)
                state = self.element_state(focused)
                if state.get("exists"):
                    return state
            except Exception:
                pass

        try:
            active = desktop.get_active()
        except Exception:
            active = None

        if active is None:
            return {"exists": False}

        # UIA descendant traversal can be expensive on large application
        # trees. Prefer the active element itself; only scan a bounded subset
        # when the direct element does not expose focus state.
        active_state = self.element_state(active)
        if active_state.get("focused") is True:
            return active_state

        try:
            focused = active.descendants(control_type=None)
            for element in focused[: self.max_tree_elements]:
                state = self.element_state(element)
                if state.get("focused") is True:
                    return state
        except Exception:
            pass

        return {"exists": False}

    def selected_element_state(self):
        desktop = self._desktop()
        if desktop is None:
            return {"exists": False}
        active = self.active_element()
        if active is None:
            return {"exists": False}
        try:
            for element in active.descendants()[: self.max_tree_elements]:
                state = self.element_state(element)
                if state.get("selected") is True:
                    return state
        except Exception:
            pass
        return {"exists": False}

    def _tree_signature(self) -> List[Dict[str, Any]]:
        active = self.active_element()
        root = self._top_level(active) if active is not None else None
        if root is None:
            return []

        try:
            descendants = root.descendants()
        except Exception:
            return []

        result: List[Dict[str, Any]] = []
        for element in descendants[: self.max_tree_elements]:
            state = self.element_state(element)
            result.append({
                "name": state.get("name", ""),
                "control_type": state.get("control_type", ""),
                "automation_id": state.get("automation_id", ""),
                "class_name": state.get("class_name", ""),
                "visible": state.get("visible", True),
                "enabled": state.get("enabled", True),
            })
        result.sort(
            key=lambda item: (
                item.get("control_type", ""),
                item.get("automation_id", ""),
                item.get("name", ""),
                item.get("class_name", ""),
            )
        )
        return result

    def _find_target(self, action: Dict[str, Any]):
        # Some action targets are data, not UI elements. Never search the
        # desktop UI tree for text that is about to be typed, pasted, or
        # copied; doing so is both semantically wrong and expensive.
        if isinstance(action, dict) and str(action.get("action") or "").strip().lower() in {
            "type_text",
            "keypress",
            "hotkey",
            "scroll",
            "wait",
            "clipboard_set",
            "clipboard_get",
            "screenshot",
            "read_active_window",
            "read_windows",
        }:
            return None

        args = action.get("args")
        args = dict(args) if isinstance(args, dict) else {}

        name = str(args.get("name") or "").strip()
        automation_id = str(args.get("automation_id", args.get("auto_id")) or "").strip()
        control_type = str(args.get("control_type") or "").strip()
        class_name = str(args.get("class_name") or "").strip()
        target = str(action.get("target") or "").strip()

        if not any((name, automation_id, control_type, class_name, target)):
            return None

        result = self.finder.find_best(
            name=name or target,
            automation_id=automation_id,
            control_type=control_type,
            class_name=class_name,
            window_title=str(args.get("window_title") or "").strip(),
        )
        return result.get("element") if result else None

    def running_windows_state(self) -> List[Dict[str, Any]]:
        """Return a bounded, JSON-safe list of currently discoverable windows."""
        desktop = self._desktop()
        if desktop is None:
            return []

        try:
            windows = desktop.windows()
        except Exception:
            return []

        result: List[Dict[str, Any]] = []
        try:
            candidates = windows[: self.max_tree_elements]
        except Exception:
            try:
                candidates = list(windows)[: self.max_tree_elements]
            except Exception:
                return []

        for window in candidates:
            state = self.element_state(window)
            if not state.get("exists"):
                continue
            item = {
                key: state.get(key, "")
                for key in (
                    "name", "control_type", "automation_id",
                    "class_name", "visible", "enabled",
                )
            }
            if not any(item.get(key) for key in ("name", "automation_id", "class_name")):
                continue
            result.append(item)

        result.sort(
            key=lambda item: (
                item.get("name", ""),
                item.get("control_type", ""),
                item.get("automation_id", ""),
            )
        )
        return result

    def snapshot(
        self,
        action: Optional[Dict[str, Any]] = None,
        primary_element: Any = None,
    ) -> Dict[str, Any]:
        # UIA queries are separate reads. Detect a foreground switch while
        # focus, selection and the visible tree are being collected.
        captured_at = time.time()
        active_before = self.active_window_state()

        target_element = primary_element
        if target_element is None and isinstance(action, dict):
            target_element = self._find_target(action)

        target_state = self.element_state(target_element)
        if target_element is not None and target_state.get("exists") is True:
            parent = self._top_level(target_element) or target_element
            parent_state = self.element_state(parent)
            identity = {
                key: parent_state.get(key)
                for key in ("hwnd", "pid", "name", "automation_id", "class_name", "control_type")
                if parent_state.get(key) not in (None, "")
            }
            if identity:
                target_state["window_identity"] = identity

        focused = self.focused_element_state()
        selected = self.selected_element_state()
        windows = self.running_windows_state()
        tree = self._tree_signature()
        active_after = self.active_window_state()
        coherent = self._same_active_window(active_before, active_after)

        snapshot = {
            "timestamp": time.time(),
            "capture_started_at": captured_at,
            "available": self.is_available(),
            "active_window": active_after,
            "focused_element": focused,
            "selected_element": selected,
            "target_element": target_state,
            "running_windows": windows,
            "ui_tree_signature": tree,
            "coherent": coherent,
        }
        if not coherent:
            snapshot["coherence_reason"] = "active_window_changed_or_identity_unavailable"
        return snapshot


__all__ = ["UIStateObserver"]
