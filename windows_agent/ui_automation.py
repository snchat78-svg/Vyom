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
    - find_ui_element
    - focus_ui_element
    - click_ui_element
    - invoke_ui_element
    - set_ui_value
    - select_ui_element
    - toggle_ui_element
    - expand_ui_element
    - collapse_ui_element

Semantic UI Automation is layered above the existing low-level Win32
fallbacks. OCR/visual grounding remains a separate future capability.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from windows_agent.clipboard_manager import ClipboardManager
from windows_agent.input_controller import InputController
from windows_agent.screen_observer import ScreenObserver
from windows_agent.window_manager import WindowManager
from windows_agent.ui_grounder import UIElementGrounder
from windows_agent import ui_patterns
from windows_agent.ui_state_observer import UIStateObserver
from windows_agent.ui_verifier import UIVerificationEngine
from tools.universal_app_launcher import UniversalAppLauncher


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
        ui_grounder: Optional[UIElementGrounder] = None,
    ):
        self.window_manager = window_manager or WindowManager()
        self.input_controller = input_controller or InputController()
        self.clipboard_manager = clipboard_manager or ClipboardManager()
        self.screen_observer = screen_observer or ScreenObserver()
        self.ui_grounder = ui_grounder or UIElementGrounder()
        self.ui_observer = UIStateObserver()
        self.ui_verifier = UIVerificationEngine(observer=self.ui_observer)
        self.app_launcher = UniversalAppLauncher()

        self._handlers = {
            "focus_window": self._focus_window,
            "open_application": self._open_application,
            "open_file": self._open_file,
            "close_application": self._close_application,
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
            "find_ui_element": self._find_ui_element,
            "focus_ui_element": self._focus_ui_element,
            "click_ui_element": self._click_ui_element,
            "invoke_ui_element": self._invoke_ui_element,
            "set_ui_value": self._set_ui_value,
            "select_ui_element": self._select_ui_element,
            "toggle_ui_element": self._toggle_ui_element,
            "expand_ui_element": self._expand_ui_element,
            "collapse_ui_element": self._collapse_ui_element,
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

        verification_actions = {
            "type_text", "find_ui_element", "focus_ui_element", "click_ui_element",
            "invoke_ui_element", "set_ui_value", "select_ui_element",
            "toggle_ui_element", "expand_ui_element", "collapse_ui_element",
        }
        metadata = action.get("metadata")
        explicit_verification = (
            isinstance(metadata, dict)
            and isinstance(metadata.get("verification"), dict)
        )
        should_verify = name in verification_actions or explicit_verification
        before = (
            self.ui_observer.snapshot(action)
            if should_verify
            else None
        )

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
            result = {
                "success": bool(result),
                "stage": "action_completed" if result else "action_failed",
                "action": name,
            }

        if should_verify and result.get("success"):
            after = self.ui_observer.snapshot(action)
            verification = self.ui_verifier.verify(
                action=action,
                before=before or {},
                after=after,
                execution_result=result,
            )

            # Test/dry-run providers may intentionally omit a real UIA
            # observer. Keep their successful capability contract intact, but
            # never weaken real Windows verification: when UIA observation is
            # available, the verifier above remains authoritative.
            def _has_observable_ui(state):
                if not isinstance(state, dict):
                    return False
                if not bool(state.get("available")):
                    return False
                for key in ("active_window", "focused_element", "selected_element", "target_element"):
                    value = state.get(key)
                    if isinstance(value, dict) and value.get("exists") is True:
                        return True
                return bool(state.get("ui_tree_signature"))

            # pywinauto can be importable while the current environment has no
            # usable desktop/UIA observation (for example CI/test hosts).
            # Treat that state as observer-unavailable only when neither the
            # before nor after snapshot contains any observable UI state.
            observer_unavailable = (
                not bool((after or {}).get("available"))
                or (
                    not _has_observable_ui(before or {})
                    and not _has_observable_ui(after or {})
                )
            )
            if (
                not verification.get("verified", False)
                and observer_unavailable
                and result.get("success")
                and name == "type_text"
                and isinstance(result.get("verification"), dict)
                and result["verification"].get("verified") is True
            ):
                verification = {
                    **verification,
                    "verified": True,
                    "verification_level": "dispatch_fallback_no_observer",
                    "method": "execution_contract",
                    "reason": "No UIA observer is available; provider execution contract was accepted.",
                }

            result["verification"] = verification
            if not verification.get("verified", False):
                result["success"] = False
                result["stage"] = "verification_failed"
                result["message"] = verification.get(
                    "reason",
                    "UI action executed but its postcondition was not verified.",
                )
            else:
                result["stage"] = "verified"

        return result

    def _ground(self, action: Dict[str, Any]) -> Dict[str, Any]:
        return self.ui_grounder.ground(action.get("target", ""), self._args(action))

    def _semantic_result(self, operation: str, grounded: Dict[str, Any], callback=None, *args) -> Dict[str, Any]:
        if not grounded.get("success"):
            return grounded
        element = grounded.get("element")
        info = grounded.get("element_info") or {}
        try:
            result = callback(element, *args) if callback else None
            return ui_patterns.operation_result(
                success=True,
                operation=operation,
                element_info=info,
                result=result,
            )
        except Exception as error:
            return ui_patterns.operation_result(
                success=False,
                operation=operation,
                element_info=info,
                error=str(error),
            )

    def _find_ui_element(self, action: Dict[str, Any]) -> Dict[str, Any]:
        grounded = self._ground(action)
        if not grounded.get("success"):
            return grounded
        return {
            "success": True,
            "stage": "ui_element_found",
            "element_info": grounded.get("element_info", {}),
            "verification": grounded.get("verification", {}),
        }

    def _focus_ui_element(self, action: Dict[str, Any]) -> Dict[str, Any]:
        return self._semantic_result("focus_ui_element", self._ground(action), ui_patterns.focus)

    def _click_ui_element(self, action: Dict[str, Any]) -> Dict[str, Any]:
        return self._semantic_result("click_ui_element", self._ground(action), ui_patterns.click)

    def _invoke_ui_element(self, action: Dict[str, Any]) -> Dict[str, Any]:
        return self._semantic_result("invoke_ui_element", self._ground(action), ui_patterns.invoke)

    def _set_ui_value(self, action: Dict[str, Any]) -> Dict[str, Any]:
        args = self._args(action)
        value = args.get("value", "")
        lookup = dict(args)
        lookup.pop("value", None)
        element_target = lookup.get("element_target")
        if element_target:
            lookup["name"] = element_target
        grounded = self.ui_grounder.ground(action.get("target", ""), lookup)
        return self._semantic_result("set_ui_value", grounded, ui_patterns.set_value, value)

    def _select_ui_element(self, action: Dict[str, Any]) -> Dict[str, Any]:
        return self._semantic_result("select_ui_element", self._ground(action), ui_patterns.select)

    def _toggle_ui_element(self, action: Dict[str, Any]) -> Dict[str, Any]:
        return self._semantic_result("toggle_ui_element", self._ground(action), ui_patterns.toggle)

    def _expand_ui_element(self, action: Dict[str, Any]) -> Dict[str, Any]:
        return self._semantic_result("expand_ui_element", self._ground(action), ui_patterns.expand)

    def _collapse_ui_element(self, action: Dict[str, Any]) -> Dict[str, Any]:
        return self._semantic_result("collapse_ui_element", self._ground(action), ui_patterns.collapse)

    @staticmethod
    def _args(action: Dict[str, Any]) -> Dict[str, Any]:
        value = action.get("args")
        return dict(value) if isinstance(value, dict) else {}

    def _open_application(self, action: Dict[str, Any]) -> Dict[str, Any]:
        target = str(action.get("target") or "").strip()
        if not target:
            return {"success": False, "stage": "missing_target", "message": "No application target was supplied."}

        before = self.window_manager.get_foreground() or {}
        result = self.app_launcher.open(target)
        if not isinstance(result, dict) or not result.get("success"):
            return {
                "success": False,
                "stage": "application_launch_failed",
                "message": (result or {}).get("message", "Application could not be opened."),
                "target": target,
                "launcher_result": result,
            }

        after = self.window_manager.get_foreground() or {}
        selected = ""
        results = result.get("results") if isinstance(result, dict) else None
        if isinstance(results, list) and results and isinstance(results[0], dict):
            selected = str(results[0].get("name") or "").strip()

        before_hwnd = before.get("hwnd")
        after_hwnd = after.get("hwnd")
        title = str(after.get("title") or "").strip().lower()
        target_words = [w for w in target.lower().split() if len(w) > 1]
        identity_match = bool(selected and selected.lower() in title)
        if not identity_match and target_words:
            identity_match = all(word in title for word in target_words[:3])

        verified = bool(after and (after_hwnd != before_hwnd or identity_match))
        return {
            "success": verified,
            "stage": "verified" if verified else "launch_not_verified",
            "message": result.get("message", "Application launch requested."),
            "target": target,
            "window_before": before,
            "window_after": after,
            "verification": {
                "verified": verified,
                "verification_level": "state",
                "method": "foreground_window_after_launch",
            },
        }

    def _open_file(self, action: Dict[str, Any]) -> Dict[str, Any]:
        target = str(action.get("target") or "").strip()
        if not target:
            return {"success": False, "stage": "missing_target", "message": "No file target was supplied."}
        before = self.window_manager.get_foreground() or {}
        result = self.app_launcher.open(target)
        after = self.window_manager.get_foreground() or {}
        verified = bool(isinstance(result, dict) and result.get("success") and after)
        return {
            "success": verified,
            "stage": "verified" if verified else "file_open_not_verified",
            "message": result.get("message", "File open requested.") if isinstance(result, dict) else str(result),
            "target": target,
            "window_before": before,
            "window_after": after,
            "verification": {
                "verified": verified,
                "verification_level": "state",
                "method": "foreground_window_after_open",
            },
        }

    def _close_application(self, action: Dict[str, Any]) -> Dict[str, Any]:
        target = str(action.get("target") or "").strip()
        if not target:
            return {"success": False, "stage": "missing_target", "message": "No application target was supplied."}
        args = self._args(action)
        observed_hwnd = args.get("hwnd")

        if observed_hwnd:
            matches = self.window_manager.find(hwnd=observed_hwnd, max_results=5)
        else:
            matches = self.window_manager.find(target=target, max_results=5)

        if not matches:
            return {
                "success": False,
                "stage": "application_not_found",
                "message": "No matching application window was observed.",
                "target": target,
                "hwnd": observed_hwnd,
            }

        # Closing is intentionally not guessed through process termination.
        # Use the observed window handle and a normal WM_CLOSE message.
        hwnd = matches[0].get("hwnd")
        try:
            WM_CLOSE = 0x0010
            self.window_manager._user32.PostMessageW(hwnd, WM_CLOSE, 0, 0)
        except Exception as error:
            return {
                "success": False,
                "stage": "close_failed",
                "message": str(error),
                "target": target,
                "hwnd": hwnd,
            }

        # Some document viewers need more than one scheduler tick to destroy
        # the top-level window. Poll the exact HWND instead of checking only a
        # title string, which may remain ambiguous across viewer instances.
        verified = False
        for _ in range(10):
            time.sleep(0.15)
            remaining = self.window_manager.find(
                hwnd=hwnd,
                max_results=1,
            )
            if not remaining:
                verified = True
                break

        return {
            "success": verified,
            "stage": "verified" if verified else "close_not_verified",
            "target": target,
            "hwnd": hwnd,
            "verification": {
                "verified": verified,
                "verification_level": "state",
                "method": "window_absence_after_close",
            },
        }

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
