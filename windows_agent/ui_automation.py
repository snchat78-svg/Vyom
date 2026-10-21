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

import re
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
from tools.phonetic_matcher import score_candidate


class WindowsUICapability:
    name = "windows_ui"
    capability_name = name
    description = "Generic Windows window, keyboard, mouse, clipboard and screen control."

    _SEMANTIC_TARGET_ACTIONS = frozenset({
        "find_ui_element",
        "focus_ui_element",
        "click_ui_element",
        "invoke_ui_element",
        "set_ui_value",
        "select_ui_element",
        "toggle_ui_element",
        "expand_ui_element",
        "collapse_ui_element",
    })

    def __init__(
        self,
        window_manager: Optional[WindowManager] = None,
        input_controller: Optional[InputController] = None,
        clipboard_manager: Optional[ClipboardManager] = None,
        screen_observer: Optional[ScreenObserver] = None,
        ui_grounder: Optional[UIElementGrounder] = None,
        ui_observer: Optional[Any] = None,
    ):
        self.window_manager = window_manager or WindowManager()
        self.input_controller = input_controller or InputController()
        self.clipboard_manager = clipboard_manager or ClipboardManager()
        self.screen_observer = screen_observer or ScreenObserver()
        self.ui_grounder = ui_grounder or UIElementGrounder()
        self.ui_observer = ui_observer or UIStateObserver()
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
            "click", "double_click", "keypress", "hotkey", "scroll",
        }
        metadata = action.get("metadata")
        explicit_verification = (
            isinstance(metadata, dict)
            and isinstance(metadata.get("verification"), dict)
        )
        should_verify = name in verification_actions or explicit_verification

        # Ground semantic UI targets exactly once. The same wrapper object is
        # used for preflight observation, dispatch, and post-action observation.
        prepared_grounding = None
        execution_action = action
        if name in self._SEMANTIC_TARGET_ACTIONS:
            prepared_grounding = self._ground(action)
            if not prepared_grounding.get("success"):
                return prepared_grounding
            execution_action = {**action, "_prepared_grounding": prepared_grounding}

        before = None
        if should_verify:
            try:
                before = self._snapshot(
                    action,
                    primary_element=(prepared_grounding or {}).get("element"),
                )
            except Exception as error:
                return {
                    "success": False,
                    "stage": "observation_failed_before_action",
                    "message": f"Could not observe the desktop before dispatch; no action was sent: {error}",
                    "action": name,
                    "verification": {
                        "verified": False,
                        "verification_level": "pre_dispatch_observation_failed",
                        "method": "windows_ui_state",
                    },
                }

        if prepared_grounding is not None:
            guard_failure = self._validate_target_observation(
                action,
                prepared_grounding,
                before if isinstance(before, dict) else {},
            )
            if guard_failure is not None:
                return guard_failure

        try:
            result = handler(execution_action)
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
            try:
                after = self._snapshot(
                    action,
                    primary_element=(prepared_grounding or {}).get("element"),
                )
            except Exception as error:
                result["success"] = False
                result["stage"] = "verification_failed"
                result["verification"] = {
                    "verified": False,
                    "verification_level": "post_action_observation_failed",
                    "method": "windows_ui_state",
                    "reason": f"The action was dispatched, but its result could not be observed: {error}",
                }
                result["message"] = result["verification"]["reason"]
                return result

            if prepared_grounding is not None and after.get("available") is not True:
                result["success"] = False
                result["stage"] = "verification_failed"
                result["verification"] = {
                    "verified": False,
                    "verification_level": "post_action_observation_unavailable",
                    "method": "windows_ui_state",
                    "reason": "The action was dispatched, but fresh UI Automation state is unavailable; success cannot be verified.",
                }
                result["message"] = result["verification"]["reason"]
                return result

            if prepared_grounding is not None and after.get("coherent") is False:
                result["success"] = False
                result["stage"] = "verification_failed"
                result["verification"] = {
                    "verified": False,
                    "verification_level": "post_action_observation_incoherent",
                    "method": "windows_ui_state",
                    "reason": "The action was dispatched, but the post-action UI observation detected a foreground/window identity race; completion cannot be verified.",
                }
                result["message"] = result["verification"]["reason"]
                return result

            verification = self.ui_verifier.verify(
                action=action,
                before=before if isinstance(before, dict) else {},
                after=after if isinstance(after, dict) else {},
                execution_result=result,
            )

            # A dispatch return is not evidence that a text payload reached a
            # real control. Keep this narrow dry-run compatibility only when
            # an observer explicitly reports unavailable and the provider
            # result itself carries a verified execution contract.
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
        prepared = action.get("_prepared_grounding")
        if isinstance(prepared, dict):
            return prepared
        return self.ui_grounder.ground(action.get("target", ""), self._args(action))

    def _snapshot(self, action: Dict[str, Any], primary_element: Any = None) -> Dict[str, Any]:
        snapshotter = getattr(self.ui_observer, "snapshot", None)
        if not callable(snapshotter):
            raise RuntimeError("The UI state observer does not provide snapshot().")
        if primary_element is not None:
            try:
                state = snapshotter(action, primary_element=primary_element)
            except TypeError:
                # Preserve simple test/dry-run observer compatibility. The
                # production UIStateObserver accepts primary_element.
                state = snapshotter(action)
        else:
            state = snapshotter(action)
        if not isinstance(state, dict):
            raise RuntimeError("The UI state observer returned a non-object snapshot.")
        return state

    @staticmethod
    def _identity_text(value: Any) -> str:
        return " ".join(str(value or "").strip().split()).casefold()

    def _validate_target_observation(
        self,
        action: Dict[str, Any],
        grounded: Dict[str, Any],
        before: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        name = str(action.get("action") or "").strip().lower()

        def reject(stage: str, reason: str) -> Dict[str, Any]:
            return {
                "success": False,
                "stage": stage,
                "message": reason,
                "action": name,
                "target": str(action.get("target") or ""),
                "verification": {
                    "verified": False,
                    "verification_level": "pre_dispatch_guard",
                    "method": "windows_ui_state",
                    "reason": reason,
                },
            }

        if before.get("available") is not True:
            return reject(
                "ui_observation_unavailable_before_action",
                "Live UI Automation observation is unavailable; the target action was not dispatched.",
            )
        if before.get("coherent") is False:
            return reject(
                "ui_observation_incoherent_before_action",
                "The UI observation detected a foreground/window identity race; the target action was not dispatched.",
            )

        target = before.get("target_element")
        if not isinstance(target, dict) or target.get("exists") is not True:
            return reject(
                "ui_target_changed_before_action",
                "The grounded UI target no longer exists in the pre-action observation.",
            )
        if target.get("visible") is False or target.get("enabled") is False:
            return reject(
                "ui_target_unavailable_before_action",
                "The grounded UI target is hidden or disabled; the action was not dispatched.",
            )

        expected = grounded.get("element_info")
        expected = expected if isinstance(expected, dict) else {}
        compared = 0
        for field in ("automation_id", "control_type", "class_name", "name"):
            wanted = self._identity_text(expected.get(field))
            observed = self._identity_text(target.get(field))
            if not wanted or not observed:
                continue
            compared += 1
            if wanted != observed:
                return reject(
                    "ui_target_context_mismatch",
                    f"The live {field} no longer matches the grounded target; the action was not dispatched.",
                )
        if compared == 0:
            return reject(
                "ui_target_identity_unverified",
                "The live observation did not expose a stable identity for the grounded target; the action was not dispatched.",
            )

        active = before.get("active_window")
        active = active if isinstance(active, dict) else {}
        target_window = target.get("window_identity")
        target_window = target_window if isinstance(target_window, dict) else {}
        args = self._args(action)
        requested_hwnd = args.get("hwnd")
        requested_title = self._identity_text(args.get("window_title"))
        target_hwnd = target_window.get("hwnd")
        active_hwnd = active.get("hwnd")
        target_window_name = self._identity_text(target_window.get("name"))
        active_window_name = self._identity_text(active.get("name"))

        if active.get("exists") is False:
            return reject(
                "ui_active_window_unavailable",
                "No active window could be confirmed before dispatch; the action was not sent.",
            )
        if requested_hwnd not in (None, "") and target_hwnd not in (None, ""):
            if str(requested_hwnd) != str(target_hwnd):
                return reject(
                    "ui_target_window_mismatch",
                    "The grounded target is outside the explicitly requested window handle.",
                )
        if requested_title and target_window_name and requested_title not in target_window_name:
            return reject(
                "ui_target_window_mismatch",
                "The grounded target does not belong to the explicitly requested window.",
            )
        if not requested_title and requested_hwnd in (None, ""):
            if target_hwnd not in (None, "") and active_hwnd not in (None, ""):
                if str(target_hwnd) != str(active_hwnd):
                    return reject(
                        "ui_target_window_mismatch",
                        "The active window changed after target grounding; the action was not dispatched.",
                    )
            elif target_window_name and active_window_name and target_window_name != active_window_name:
                return reject(
                    "ui_target_window_mismatch",
                    "The grounded target belongs to a different window than the active observation.",
                )

        return None

    def _semantic_result(self, operation: str, grounded: Dict[str, Any], callback=None, *args) -> Dict[str, Any]:
        if not grounded.get("success"):
            return grounded
        element = grounded.get("element")
        info = grounded.get("element_info") or {}
        operation_key = {
            "focus_ui_element": "focus",
            "click_ui_element": "click",
            "invoke_ui_element": "invoke",
            "set_ui_value": "set_value",
            "select_ui_element": "select",
            "toggle_ui_element": "toggle",
            "expand_ui_element": "expand",
            "collapse_ui_element": "collapse",
        }.get(operation, operation)
        selected_method = ui_patterns.select_operation(element, operation_key)
        if selected_method is None:
            return {
                "success": False,
                "stage": "ui_pattern_unsupported",
                "message": (
                    f"The selected UI element does not expose a supported "
                    f"'{operation_key}' control operation."
                ),
                "operation": operation,
                "element_info": info,
                "supported_operations": ui_patterns.supported_operations(element),
            }
        try:
            result = callback(element, *args) if callback else None
            return ui_patterns.operation_result(
                success=True,
                operation=operation,
                element_info=info,
                result=result,
                method=selected_method,
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
        prepared = action.get("_prepared_grounding")
        grounded = (
            prepared
            if isinstance(prepared, dict)
            else self.ui_grounder.ground(action.get("target", ""), lookup)
        )
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

    @staticmethod
    def _window_title_segments(title: Any) -> List[str]:
        value = str(title or "").strip()
        if not value:
            return []
        return [
            piece.strip()
            for piece in re.split(r"\s+(?:-|—|–|\|)\s+", value)
            if piece.strip()
        ] or [value]

    @classmethod
    def _window_matches_target(
        cls,
        target: str,
        window: Dict[str, Any],
        runtime_names: Optional[List[str]] = None,
    ) -> bool:
        """Match observed title segments to a runtime target without app aliases."""
        if not isinstance(window, dict):
            return False
        names = [str(target or "").strip()]
        names.extend(str(name or "").strip() for name in (runtime_names or []))
        segments = cls._window_title_segments(window.get("title"))
        for name in names:
            if not name:
                continue
            lowered_name = name.lower()
            for segment in segments:
                lowered_segment = segment.lower()
                if lowered_name == lowered_segment:
                    return True
                # Prevent "Notepad" from matching the distinct "Notepad++".
                if lowered_name in lowered_segment or lowered_segment in lowered_name:
                    continue
                if score_candidate(lowered_name, lowered_segment) >= 0.80:
                    return True
        return False

    @staticmethod
    def _verified_open_result(
        target: str,
        before: Dict[str, Any],
        after: Dict[str, Any],
        method: str,
        message: str,
    ) -> Dict[str, Any]:
        return {
            "success": True,
            "stage": "verified",
            "message": message,
            "target": target,
            "window_before": before or {},
            "window_after": after or {},
            "verification": {
                "verified": True,
                "verification_level": "state",
                "method": method,
            },
        }

    def _open_application(self, action: Dict[str, Any]) -> Dict[str, Any]:
        target = str(action.get("target") or "").strip()
        if not target:
            return {"success": False, "stage": "missing_target", "message": "No application target was supplied."}

        before = self.window_manager.get_foreground() or {}
        if self._window_matches_target(target, before):
            return self._verified_open_result(
                target, before, before, "existing_foreground_match",
                "Reusing the already active application window.",
            )

        # Search currently visible runtime windows first. Activate a matching
        # existing window rather than launching another copy of the same app.
        try:
            running_windows = self.window_manager.list_windows(max_results=500)
        except Exception:
            running_windows = []
        for candidate in running_windows if isinstance(running_windows, list) else []:
            if not isinstance(candidate, dict) or not self._window_matches_target(target, candidate):
                continue
            hwnd = candidate.get("hwnd")
            if not hwnd:
                continue
            if before.get("hwnd") and int(before.get("hwnd") or 0) == int(hwnd):
                continue
            try:
                activation = self.window_manager.activate(hwnd)
            except Exception:
                activation = {"success": False}
            after_activation = self.window_manager.get_foreground() or {}
            if activation.get("success") and self._window_matches_target(target, after_activation):
                return self._verified_open_result(
                    target, before, after_activation, "existing_window_activated",
                    "Activated the existing application window.",
                )

        launch = self.app_launcher.open(target)
        if not isinstance(launch, dict) or not launch.get("success"):
            return {
                "success": False,
                "stage": "application_launch_failed",
                "message": (launch or {}).get("message", "Application could not be opened."),
                "target": target,
                "launcher_result": launch,
            }

        runtime_names = []
        records = launch.get("results")
        if isinstance(records, list):
            runtime_names.extend(
                str(item.get("name") or "").strip()
                for item in records if isinstance(item, dict) and item.get("name")
            )

        # Window creation can lag behind process launch. Accept only an
        # observed window whose title matches the spoken target or a runtime-
        # discovered application record; a random foreground change is not proof.
        deadline = time.monotonic() + 2.0
        after = {}
        while time.monotonic() < deadline:
            after = self.window_manager.get_foreground() or {}
            if self._window_matches_target(target, after, runtime_names):
                return self._verified_open_result(
                    target, before, after, "foreground_title_match",
                    launch.get("message", "Application opened and verified."),
                )
            time.sleep(0.10)

        return {
            "success": False,
            "stage": "launch_not_verified",
            "message": "Launch was requested, but the requested application window could not be verified.",
            "target": target,
            "launcher_result": launch,
            "window_before": before,
            "window_after": after,
            "verification": {
                "verified": False,
                "verification_level": "state",
                "method": "foreground_target_match",
                "reason": "No foreground title matched the target or its runtime-discovered name.",
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
