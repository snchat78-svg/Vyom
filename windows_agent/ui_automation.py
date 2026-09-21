"""
Project : Vyom AI
Version : 1.0
Module  : Windows UI Capability

Purpose:
    Generic runtime capability for computer interaction. It is deliberately
    application-agnostic: no Excel/Word/Chrome/Notepad names, paths or
    fixed user commands are embedded here.

Scope of Step 2:
    - focus_window
    - move_mouse
    - click
    - double_click
    - type_text
    - keypress
    - hotkey
    - scroll
    - clipboard_set
    - clipboard_get
    - screenshot
    - read_active_window
    - read_windows
    - wait

Higher-level UI element grounding, OCR and semantic control discovery belong
in later capabilities; this provider is the generic low-level computer
control layer.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from windows_agent.clipboard_manager import ClipboardManager
from windows_agent.input_controller import InputController
from windows_agent.screen_observer import ScreenObserver
from windows_agent.window_manager import WindowManager


class WindowsUICapability:
    name = "windows_ui"
    capability_name = name
    description = "Generic Windows window, keyboard, mouse, clipboard and screen control."

    def __init__(
        self,
        window_manager: Optional[WindowManager] = None,
        input_controller: Optional[InputController] = None,
        clipboard_manager: Optional[ClipboardManager] = None,
        screen_observer: Optional[ScreenObserver] = None,
    ):
        self.window_manager = window_manager or WindowManager()
        self.input_controller = input_controller or InputController()
        self.clipboard_manager = clipboard_manager or ClipboardManager()
        self.screen_observer = screen_observer or ScreenObserver()

        self._handlers = {
            "focus_window": self._focus_window,
            "move_mouse": self._move_mouse,
            "click": self._click,
            "double_click": self._double_click,
            "type_text": self._type_text,
            "keypress": self._keypress,
            "hotkey": self._hotkey,
            "scroll": self._scroll,
            "clipboard_set": self._clipboard_set,
            "clipboard_get": self._clipboard_get,
            "screenshot": self._screenshot,
            "read_active_window": self._read_active_window,
            "read_windows": self._read_windows,
            "wait": self._wait,
        }

    def supported_actions(self) -> List[str]:
        return sorted(self._handlers.keys())

    def execute(self, action: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(action, dict):
            return {"success": False, "stage": "invalid_action", "message": "Action must be an object."}

        name = str(action.get("action") or "").strip().lower()
        handler = self._handlers.get(name)
        if handler is None:
            return {
                "success": False,
                "stage": "unsupported_action",
                "message": f"Windows UI capability does not support action '{name}'.",
            }

        try:
            result = handler(action)
        except Exception as error:
            return {
                "success": False,
                "stage": "windows_ui_error",
                "message": str(error),
                "action": name,
            }

        if not isinstance(result, dict):
            return {
                "success": bool(result),
                "stage": "action_completed" if result else "action_failed",
                "action": name,
            }
        return result

    @staticmethod
    def _args(action: Dict[str, Any]) -> Dict[str, Any]:
        value = action.get("args")
        return dict(value) if isinstance(value, dict) else {}

    def _focus_window(self, action: Dict[str, Any]) -> Dict[str, Any]:
        args = self._args(action)
        return self.window_manager.focus(
            target=action.get("target", ""),
            hwnd=args.get("hwnd"),
            title=args.get("title", ""),
            class_name=args.get("class_name", ""),
            pid=args.get("pid"),
        )

    def _move_mouse(self, action: Dict[str, Any]) -> Dict[str, Any]:
        args = self._args(action)
        return self.input_controller.move_mouse(args.get("x"), args.get("y"))

    def _click(self, action: Dict[str, Any]) -> Dict[str, Any]:
        args = self._args(action)
        return self.input_controller.click(
            button=args.get("button", "left"),
            x=args.get("x"),
            y=args.get("y"),
            count=max(1, int(args.get("count", 1))),
            interval=float(args.get("interval", 0.05)),
        )

    def _double_click(self, action: Dict[str, Any]) -> Dict[str, Any]:
        args = self._args(action)
        return self.input_controller.click(
            button=args.get("button", "left"),
            x=args.get("x"),
            y=args.get("y"),
            count=2,
            interval=float(args.get("interval", 0.08)),
        )

    def _type_text(self, action: Dict[str, Any]) -> Dict[str, Any]:
        args = self._args(action)
        text = args.get("text")
        if text is None:
            text = action.get("target", "")
        return self.input_controller.type_text(text)

    def _keypress(self, action: Dict[str, Any]) -> Dict[str, Any]:
        args = self._args(action)
        return self.input_controller.keypress(args.get("key", action.get("target", "")))

    def _hotkey(self, action: Dict[str, Any]) -> Dict[str, Any]:
        args = self._args(action)
        return self.input_controller.hotkey(args.get("keys", action.get("target", "")))

    def _scroll(self, action: Dict[str, Any]) -> Dict[str, Any]:
        args = self._args(action)
        return self.input_controller.scroll(args.get("amount", 0))

    def _clipboard_set(self, action: Dict[str, Any]) -> Dict[str, Any]:
        args = self._args(action)
        text = args.get("text")
        if text is None:
            text = action.get("target", "")
        return self.clipboard_manager.set_text(text)

    def _clipboard_get(self, _action: Dict[str, Any]) -> Dict[str, Any]:
        return self.clipboard_manager.get_text()

    def _screenshot(self, action: Dict[str, Any]) -> Dict[str, Any]:
        args = self._args(action)
        return self.screen_observer.capture(
            path=args.get("path") or action.get("target") or None,
            x=args.get("x", 0),
            y=args.get("y", 0),
            width=args.get("width"),
            height=args.get("height"),
        )

    def _read_active_window(self, _action: Dict[str, Any]) -> Dict[str, Any]:
        active = self.window_manager.get_foreground()
        if active is None:
            return {
                "success": False,
                "stage": "active_window_unavailable",
                "message": "No active window could be observed.",
            }
        return {
            "success": True,
            "stage": "active_window_read",
            "window": active,
            "verification": {"verified": True, "verification_level": "state"},
        }

    def _read_windows(self, action: Dict[str, Any]) -> Dict[str, Any]:
        args = self._args(action)
        windows = self.window_manager.list_windows(
            include_invisible=bool(args.get("include_invisible", False)),
            max_results=max(1, int(args.get("max_results", 100))),
        )
        return {
            "success": True,
            "stage": "windows_read",
            "windows": windows,
            "count": len(windows),
            "verification": {"verified": True, "verification_level": "state"},
        }

    def _wait(self, action: Dict[str, Any]) -> Dict[str, Any]:
        args = self._args(action)
        seconds = float(args.get("seconds", action.get("target", 0) or 0))
        if seconds < 0 or seconds > 30:
            return {
                "success": False,
                "stage": "invalid_wait_duration",
                "message": "Wait duration must be between 0 and 30 seconds.",
            }
        time.sleep(seconds)
        return {
            "success": True,
            "stage": "wait_completed",
            "seconds": seconds,
            "verification": {"verified": True, "verification_level": "dispatch"},
        }
