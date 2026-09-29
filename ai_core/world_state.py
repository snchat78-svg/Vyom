"""
Project : Vyom AI
Version : 2.0
Module  : World State Model

Purpose:
    Provide one canonical, read-only snapshot of the computer and mission
    state for reasoning, planning, verification and re-planning.

Design:
    - Observation only; this module never executes UI actions.
    - UI Automation is optional and failure-isolated.
    - Legacy callers can keep using snapshot(session_context).
    - Runtime state can be recorded without creating a second context owner.
"""

from __future__ import annotations

import os
import subprocess
import time
from typing import Any, Dict, Optional


class WorldStateModel:
    """Canonical observable world-state aggregator."""

    def __init__(
        self,
        max_processes: int = 30,
        ui_observer: Any = None,
        clipboard_manager: Any = None,
        screen_observer: Any = None,
    ):
        self.max_processes = max(5, int(max_processes))
        self.ui_observer = ui_observer
        self.clipboard_manager = clipboard_manager
        self.screen_observer = screen_observer
        self.last_snapshot: Optional[Dict[str, Any]] = None
        self.last_action: Optional[Dict[str, Any]] = None
        self.last_result: Any = None
        self.last_verification: Optional[Dict[str, Any]] = None

    def _running_processes(self):
        if os.name != "nt":
            return []

        try:
            result = subprocess.run(
                ["tasklist", "/FO", "CSV", "/NH"],
                capture_output=True,
                text=True,
                timeout=3,
            )
            processes = []
            for line in result.stdout.splitlines():
                line = line.strip()
                if not line or line.startswith("INFO:"):
                    continue
                first = line.split('","', 1)[0].replace('"', "").strip()
                if first:
                    processes.append(first)
            return processes[:self.max_processes]
        except Exception:
            return []

    @staticmethod
    def _safe_dict(value: Any) -> Dict[str, Any]:
        return dict(value) if isinstance(value, dict) else {}

    def _ui_state(self, action: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        observer = self.ui_observer
        if observer is None:
            return {"available": False}

        try:
            state = observer.snapshot(action)
            return self._safe_dict(state)
        except Exception as error:
            return {
                "available": False,
                "error": str(error),
            }

    def _clipboard_state(self) -> Dict[str, Any]:
        manager = self.clipboard_manager
        if manager is None:
            return {"available": False}

        try:
            available = bool(manager.is_available())
        except Exception:
            available = False

        if not available:
            return {"available": False}

        try:
            result = manager.get_text()
        except Exception as error:
            return {"available": True, "read_error": str(error)}

        if not isinstance(result, dict):
            return {"available": True}

        return {
            "available": True,
            "success": bool(result.get("success", False)),
            "text": str(result.get("text", "")) if result.get("success") else "",
        }

    def _screen_state(self) -> Dict[str, Any]:
        observer = self.screen_observer
        if observer is None:
            return {"available": False}

        try:
            available = bool(observer.is_available())
        except Exception:
            available = False

        state = {"available": available}
        if available:
            try:
                state["size"] = dict(observer.get_size())
            except Exception:
                state["size"] = {"width": 0, "height": 0}
        return state

    def record_execution(
        self,
        action: Optional[Dict[str, Any]],
        result: Any,
        verification: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.last_action = dict(action) if isinstance(action, dict) else action
        self.last_result = result
        self.last_verification = (
            dict(verification)
            if isinstance(verification, dict)
            else verification
        )

    def snapshot(
        self,
        session_context: Optional[Dict[str, Any]] = None,
        *,
        mission_state: Optional[Dict[str, Any]] = None,
        include_ui: bool = True,
        include_clipboard: bool = True,
    ):
        ctx = session_context if isinstance(session_context, dict) else {}

        state = {
            "timestamp": time.time(),
            "platform": os.name,
            "cwd": os.getcwd(),

            # Session/context owner data.
            "current_app": ctx.get("current_app"),
            "current_file": ctx.get("current_file"),
            "current_target": ctx.get("current_target"),
            "task_state": ctx.get("task_state"),
            "last_success": ctx.get("last_success"),
            "pending_selection": ctx.get("pending_selection", False),
            "awaiting_confirmation": ctx.get("awaiting_confirmation", False),

            # Execution/verification state.
            "last_action": self.last_action,
            "last_result": self.last_result,
            "last_verification": self.last_verification,

            # Computer state.
            "running_processes": self._running_processes(),
            "screen": self._screen_state(),

            # Mission state belongs here as an observation, not a second owner.
            "mission_state": (
                dict(mission_state)
                if isinstance(mission_state, dict)
                else {}
            ),
        }

        if include_ui:
            ui = self._ui_state(self.last_action)
            state["ui"] = ui
            state["current_window"] = ui.get("active_window", {})
            state["focused_control"] = ui.get("focused_element", {})
            state["visible_ui_elements"] = ui.get("ui_tree_signature", [])
        else:
            state["ui"] = {"available": False, "skipped": True}

        if include_clipboard:
            state["clipboard"] = self._clipboard_state()
        else:
            state["clipboard"] = {"available": False, "skipped": True}

        self.last_snapshot = state
        return state


__all__ = ["WorldStateModel"]
