"""Generic before/after verification for Windows UI actions."""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from windows_agent.ui_state_observer import UIStateObserver


class UIVerificationEngine:
    """Evaluate observable UI postconditions without application-specific rules."""

    def __init__(
        self,
        observer: Optional[UIStateObserver] = None,
        default_timeout: float = 2.0,
        poll_interval: float = 0.10,
    ):
        self.observer = observer or UIStateObserver()
        self.default_timeout = min(5.0, max(0.0, float(default_timeout)))
        self.poll_interval = min(0.5, max(0.02, float(poll_interval)))

    @staticmethod
    def _norm(value: Any) -> str:
        return str(value or "").strip().lower()

    @staticmethod
    def _get(state: Dict[str, Any], source: str) -> Dict[str, Any]:
        aliases = {
            "target": "target_element",
            "target_before": "target_element",
            "target_after": "target_element",
            "focused": "focused_element",
            "focused_before": "focused_element",
            "focused_after": "focused_element",
            "window": "active_window",
            "window_before": "active_window",
            "window_after": "active_window",
        }
        key = aliases.get(str(source or "").strip().lower(), source)
        value = state.get(key)
        return value if isinstance(value, dict) else {}

    @classmethod
    def _field(cls, state: Dict[str, Any], source: str, field: str) -> Any:
        return cls._get(state, source).get(field)

    @staticmethod
    def _tree_changed(before: Dict[str, Any], after: Dict[str, Any]) -> bool:
        return before.get("ui_tree_signature", []) != after.get("ui_tree_signature", [])

    @staticmethod
    def _window_changed(before: Dict[str, Any], after: Dict[str, Any]) -> bool:
        b = before.get("active_window", {}) or {}
        a = after.get("active_window", {}) or {}
        keys = ("name", "automation_id", "class_name", "control_type")
        return any(b.get(key) != a.get(key) for key in keys)

    @classmethod
    def _property_check(
        cls,
        check: Dict[str, Any],
        before: Dict[str, Any],
        after: Dict[str, Any],
    ) -> bool:
        source = str(check.get("source", "target_element")).strip()
        field = str(check.get("field", "")).strip()
        operator = cls._norm(check.get("operator", "equals"))
        expected = check.get("value")

        actual_state = after
        before_state = before
        if source.endswith("_before"):
            source_base = source[:-7]
            actual = cls._field(before_state, source_base, field)
        else:
            actual = cls._field(actual_state, source, field)

        if operator in ("equals", "eq", "is"):
            return actual == expected
        if operator in ("not_equals", "ne", "is_not"):
            return actual != expected
        if operator == "contains":
            return str(expected) in str(actual or "")
        if operator == "not_contains":
            return str(expected) not in str(actual or "")
        if operator == "changed":
            before_value = cls._field(before_state, source.replace("_after", ""), field)
            return before_value != actual
        if operator == "in":
            return actual in (expected if isinstance(expected, list) else [])
        if operator == "truthy":
            return bool(actual)
        if operator == "falsy":
            return not bool(actual)
        return False

    @classmethod
    def _single_check(
        cls,
        check: Dict[str, Any],
        before: Dict[str, Any],
        after: Dict[str, Any],
    ) -> bool:
        if not isinstance(check, dict):
            return False

        kind = cls._norm(check.get("kind", "property"))
        if kind == "property":
            return cls._property_check(check, before, after)

        if kind == "element_exists":
            source = str(check.get("source", "target_element"))
            state = cls._get(after, source)
            return bool(state.get("exists", False))

        if kind == "element_not_exists":
            source = str(check.get("source", "target_element"))
            state = cls._get(after, source)
            return not bool(state.get("exists", False))

        if kind in ("state_changed", "target_changed"):
            before_target = before.get("target_element", {}) or {}
            after_target = after.get("target_element", {}) or {}
            return before_target != after_target

        if kind == "ui_tree_changed":
            return cls._tree_changed(before, after)

        if kind == "window_changed":
            return cls._window_changed(before, after)

        if kind == "focused_changed":
            return (
                before.get("focused_element", {}) or {}
            ) != (
                after.get("focused_element", {}) or {}
            )

        return False

    def _default_checks(self, action: Dict[str, Any]) -> List[Dict[str, Any]]:
        name = self._norm(action.get("action"))
        if name == "find_ui_element":
            return [{"kind": "element_exists", "source": "target_element"}]
        if name == "focus_ui_element":
            return [{
                "kind": "property",
                "source": "target_element",
                "field": "focused",
                "operator": "equals",
                "value": True,
            }]
        if name in ("set_ui_value",):
            args = action.get("args")
            args = dict(args) if isinstance(args, dict) else {}
            return [{
                "kind": "property",
                "source": "target_element",
                "field": "value",
                "operator": "equals",
                "value": args.get("value", ""),
            }]
        if name == "select_ui_element":
            return [{
                "kind": "property",
                "source": "target_element",
                "field": "selected",
                "operator": "equals",
                "value": True,
            }]
        if name == "toggle_ui_element":
            return [{
                "kind": "state_changed",
            }]
        if name == "expand_ui_element":
            return [{
                "kind": "property",
                "source": "target_element",
                "field": "expanded",
                "operator": "equals",
                "value": True,
            }]
        if name == "collapse_ui_element":
            return [{
                "kind": "property",
                "source": "target_element",
                "field": "collapsed",
                "operator": "equals",
                "value": True,
            }]
        if name in ("click_ui_element", "invoke_ui_element"):
            return [
                {"kind": "state_changed"},
                {"kind": "element_not_exists", "source": "target_element"},
                {"kind": "ui_tree_changed"},
                {"kind": "window_changed"},
                {"kind": "focused_changed"},
            ]
        if name == "type_text":
            args = action.get("args")
            args = dict(args) if isinstance(args, dict) else {}
            value = args.get("text", action.get("target", ""))
            return [{
                "kind": "property",
                "source": "focused_element",
                "field": "value",
                "operator": "contains",
                "value": value,
            }]
        return []

    def verify(
        self,
        action: Dict[str, Any],
        before: Dict[str, Any],
        after: Dict[str, Any],
        execution_result: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        execution_result = execution_result if isinstance(execution_result, dict) else {}
        executed = bool(execution_result.get("success", True))

        if not executed:
            return {
                "verified": False,
                "verification_level": "execution_failed",
                "method": "windows_ui_state",
                "checks": [],
                "reason": "Execution did not report success.",
            }

        metadata = action.get("metadata")
        verification_spec = metadata.get("verification") if isinstance(metadata, dict) else None
        if isinstance(verification_spec, dict):
            checks = verification_spec.get("checks", [])
            mode = self._norm(verification_spec.get("mode", "all"))
        else:
            checks = self._default_checks(action)
            mode = "any" if self._norm(action.get("action")) in ("click_ui_element", "invoke_ui_element", "toggle_ui_element") else "all"

        if not isinstance(checks, list) or not checks:
            return {
                "verified": False,
                "verification_level": "no_postcondition",
                "method": "windows_ui_state",
                "checks": [],
                "reason": "No observable postcondition was supplied.",
            }

        results = [
            self._single_check(check, before, after)
            for check in checks
        ]
        verified = all(results) if mode != "any" else any(results)

        return {
            "verified": bool(verified),
            "verification_level": "state" if verified else "state_failed",
            "method": "windows_ui_state",
            "mode": mode,
            "checks": [
                {
                    "check": dict(check) if isinstance(check, dict) else {},
                    "passed": passed,
                }
                for check, passed in zip(checks, results)
            ],
            "reason": (
                "All required postconditions were observed."
                if verified and mode != "any"
                else "At least one required postcondition was observed."
                if verified
                else "The requested postconditions were not observed."
            ),
        }


__all__ = ["UIVerificationEngine"]
