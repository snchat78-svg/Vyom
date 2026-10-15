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
        self.observation_history: list = []
        self.max_observation_history = 50

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

    def _screen_state(self, include_snapshot: bool = False) -> Dict[str, Any]:
        observer = self.screen_observer
        if observer is None:
            return {
                "available": False,
                "snapshot": {"available": False, "captured": False},
            }

        try:
            available = bool(observer.is_available())
        except Exception:
            available = False

        state = {
            "available": available,
            "snapshot": {
                "available": available,
                "captured": False,
            },
        }
        if available:
            try:
                state["size"] = dict(observer.get_size())
            except Exception:
                state["size"] = {"width": 0, "height": 0}

            # Screen pixels are captured only when explicitly requested.
            # Normal autonomous observations stay lightweight on low-resource
            # machines while Phase 4 still exposes a real snapshot contract.
            if include_snapshot:
                capture = getattr(observer, "capture", None)
                if callable(capture):
                    try:
                        result = capture()
                        if isinstance(result, dict):
                            safe = {
                                key: result.get(key)
                                for key in (
                                    "success", "stage", "path",
                                    "width", "height", "verification"
                                )
                                if key in result
                            }
                            state["snapshot"].update(safe)
                            state["snapshot"]["captured"] = bool(
                                result.get("success", False)
                            )
                        else:
                            state["snapshot"]["error"] = (
                                "Screen observer returned an invalid capture result."
                            )
                    except Exception as error:
                        state["snapshot"]["error"] = str(error)

        return state

    @staticmethod
    def _observation_entity_summary(value: Any) -> Dict[str, Any]:
        """Retain target identity only; omit entered text, values and UI trees."""
        if not isinstance(value, dict):
            return {}
        summary: Dict[str, Any] = {}
        for field in (
            "exists", "name", "title", "control_type",
            "automation_id", "class_name", "visible", "enabled",
        ):
            item = value.get(field)
            if isinstance(item, (str, bool, int, float)):
                summary[field] = str(item)[:160] if isinstance(item, str) else item
        return summary

    @classmethod
    def _compact_observation(cls, observation: Dict[str, Any], timestamp: float) -> Dict[str, Any]:
        """Avoid recursively storing full world snapshots inside observation history."""
        recorded: Dict[str, Any] = {"timestamp": timestamp}
        for field, limit in (("phase", 80), ("step_id", 100), ("step_type", 80)):
            value = observation.get(field)
            if value is not None:
                recorded[field] = str(value)[:limit]

        result = observation.get("result")
        if isinstance(result, dict):
            result_summary = {}
            for field in ("success", "stage", "status"):
                if isinstance(result.get(field), (bool, int, float, str)):
                    value = result[field]
                    result_summary[field] = str(value)[:120] if isinstance(value, str) else value
            if result_summary:
                recorded["result"] = result_summary
        elif isinstance(result, (str, bool, int, float)):
            recorded["result"] = str(result)[:160] if isinstance(result, str) else result

        verification = observation.get("verification")
        if isinstance(verification, dict):
            verification_summary = {}
            for field in ("verified", "state", "verification_level"):
                if isinstance(verification.get(field), (bool, int, float, str)):
                    value = verification[field]
                    verification_summary[field] = str(value)[:120] if isinstance(value, str) else value
            if verification_summary:
                recorded["verification"] = verification_summary

        world = observation.get("world_state")
        if isinstance(world, dict):
            world_summary: Dict[str, Any] = {}
            for field in ("timestamp", "platform", "task_state", "last_success"):
                value = world.get(field)
                if isinstance(value, (str, bool, int, float)):
                    world_summary[field] = value
            for field in ("current_window", "focused_control", "selected_control"):
                summary = cls._observation_entity_summary(world.get(field))
                if summary:
                    world_summary[field] = summary
            mission = world.get("mission_state")
            if isinstance(mission, dict):
                mission_summary = {}
                for field in ("mission_state", "current_step", "completed_steps", "failed_steps"):
                    value = mission.get(field)
                    if isinstance(value, (str, bool, int, float)):
                        mission_summary[field] = value
                if mission_summary:
                    world_summary["mission_state"] = mission_summary
            recorded["world_state"] = world_summary
        return recorded

    def record_observation(self, observation: Dict[str, Any]) -> None:
        """Store bounded, compact observations without recursive world snapshots."""
        if not isinstance(observation, dict):
            return
        timestamp = observation.get("timestamp")
        if not isinstance(timestamp, (int, float)) or timestamp <= 0:
            timestamp = time.time()
        recorded = self._compact_observation(observation, float(timestamp))
        self.observation_history.append(recorded)
        del self.observation_history[:-self.max_observation_history]

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
        include_screen_snapshot: bool = False,
    ):
        ctx = session_context if isinstance(session_context, dict) else {}

        state = {
            "timestamp": time.time(),
            "platform": os.name,
            "cwd": os.getcwd(),

            # Session/context owner data.
            "current_app": ctx.get("current_app") or "",
            "current_file": ctx.get("current_file") or "",
            "current_target": ctx.get("current_target") or "",
            "task_state": ctx.get("task_state") or "",
            "last_success": ctx.get("last_success"),
            "pending_selection": ctx.get("pending_selection", False),
            "awaiting_confirmation": ctx.get("awaiting_confirmation", False),

            # Execution/verification state.
            "last_action": self.last_action,
            "last_result": self.last_result,
            "last_verification": self.last_verification,

            # Computer state.
            "running_processes": self._running_processes(),
            "screen": self._screen_state(include_screen_snapshot),

            # Mission state belongs here as an observation, not a second owner.
            "mission_state": (
                dict(mission_state)
                if isinstance(mission_state, dict)
                else {}
            ),
            "observation_history": [dict(item) for item in self.observation_history],
        }

        if include_ui:
            ui = self._ui_state(self.last_action)
            state["ui"] = ui
            windows = ui.get("running_windows", [])
            state["running_windows"] = (
                [dict(item) for item in windows if isinstance(item, dict)]
                if isinstance(windows, list)
                else []
            )
            state["current_window"] = ui.get("active_window", {})
            state["focused_control"] = ui.get("focused_element", {})
            state["selected_control"] = ui.get("selected_element", {})
            state["visible_ui_elements"] = ui.get("ui_tree_signature", [])
        else:
            state["ui"] = {"available": False, "skipped": True}
            state["running_windows"] = []

        if include_clipboard:
            state["clipboard"] = self._clipboard_state()
        else:
            state["clipboard"] = {"available": False, "skipped": True}

        self.last_snapshot = state
        return state


__all__ = ["WorldStateModel"]
