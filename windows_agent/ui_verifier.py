"""Generic before/after verification for Windows UI actions."""

from __future__ import annotations

import re

from typing import Any, Dict, List, Optional


class UIVerificationEngine:
    """Evaluate observable UI postconditions without application-specific rules."""

    def __init__(
        self,
        observer: Optional[Any] = None,
        default_timeout: float = 2.0,
        poll_interval: float = 0.10,
    ):
        self.observer = observer
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
        before_tree = before.get("ui_tree_signature")
        after_tree = after.get("ui_tree_signature")
        # Missing/empty trees commonly mean observation failed; they are not
        # evidence that a UI transition occurred.
        return (
            isinstance(before_tree, list)
            and isinstance(after_tree, list)
            and bool(before_tree)
            and bool(after_tree)
            and before_tree != after_tree
        )

    @staticmethod
    def _window_changed(before: Dict[str, Any], after: Dict[str, Any]) -> bool:
        b = before.get("active_window")
        a = after.get("active_window")
        if not isinstance(b, dict) or not isinstance(a, dict) or not b or not a:
            return False
        if b.get("exists") is False or a.get("exists") is False:
            return False
        keys = ("name", "title", "automation_id", "class_name", "control_type", "hwnd", "pid")
        known_before = any(b.get(key) not in (None, "") for key in keys)
        known_after = any(a.get(key) not in (None, "") for key in keys)
        return known_before and known_after and any(
            b.get(key) != a.get(key)
            for key in keys
            if b.get(key) not in (None, "") and a.get(key) not in (None, "")
        )

    @staticmethod
    def _focused_changed(before: Dict[str, Any], after: Dict[str, Any]) -> bool:
        b = before.get("focused_element")
        a = after.get("focused_element")
        if not isinstance(b, dict) or not isinstance(a, dict) or not b or not a:
            return False
        if b.get("exists") is False or a.get("exists") is False:
            return False
        # Compare only properties observed on both sides. A partially missing
        # after-state must not itself count as a focus transition.
        fields = (
            "hwnd", "automation_id", "control_type", "class_name", "name",
            "value", "text", "focused", "selected",
        )
        shared = [
            key for key in fields
            if key in b and key in a and b.get(key) is not None and a.get(key) is not None
        ]
        return bool(shared) and any(b.get(key) != a.get(key) for key in shared)

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

        if source.endswith("_before"):
            source_base = source[:-7]
            actual = cls._field(before, source_base, field)
        else:
            actual = cls._field(after, source, field)

        if operator in ("equals", "eq", "is"):
            return actual is not None and actual == expected
        if operator in ("not_equals", "ne", "is_not"):
            return actual is not None and actual != expected
        if operator in ("contains", "includes"):
            return (
                actual is not None
                and str(expected or "") != ""
                and str(expected) in str(actual)
            )
        if operator == "not_contains":
            return (
                actual is not None
                and str(expected or "") != ""
                and str(expected) not in str(actual)
            )
        if operator == "changed":
            source_base = source.replace("_before", "").replace("_after", "")
            before_value = cls._field(before, source_base, field)
            after_value = cls._field(after, source_base, field)
            return (
                before_value is not None
                and after_value is not None
                and before_value != after_value
            )
        if operator == "in":
            return (
                actual is not None
                and isinstance(expected, list)
                and actual in expected
            )
        if operator == "truthy":
            return actual is not None and bool(actual)
        if operator == "falsy":
            return actual is not None and not bool(actual)
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
            observed = cls._get(after, source)
            return observed.get("exists") is True

        if kind == "element_not_exists":
            source = str(check.get("source", "target_element"))
            observed = cls._get(after, source)
            return "exists" in observed and observed.get("exists") is False

        if kind in ("state_changed", "target_changed"):
            source = str(check.get("source", "target_element"))
            before_state = cls._get(before, source)
            after_state = cls._get(after, source)
            if not before_state or not after_state:
                return False
            # An explicit existence transition is meaningful evidence; missing
            # dictionaries/fields are not.
            if "exists" in before_state and "exists" in after_state:
                if before_state.get("exists") is True and after_state.get("exists") is False:
                    return True
                if before_state.get("exists") is False or after_state.get("exists") is False:
                    return False
            fields = (
                "exists", "enabled", "visible", "focused", "selected",
                "toggle_state", "expanded", "collapsed", "value", "text",
            )
            shared = [
                key for key in fields
                if key in before_state and key in after_state
                and before_state.get(key) is not None and after_state.get(key) is not None
            ]
            return bool(shared) and any(
                before_state.get(key) != after_state.get(key)
                for key in shared
            )

        if kind == "text_input_applied":
            # The typed payload must be visible in the same focused control,
            # and its observed value/text must actually have changed. An
            # unrelated tree change or text that was already present is not
            # sufficient evidence that this typing action succeeded.
            expected = check.get("value")
            if not isinstance(expected, str) or not expected:
                return False
            b = cls._get(before, "focused_element")
            a = cls._get(after, "focused_element")
            if b.get("exists") is not True or a.get("exists") is not True:
                return False
            if b.get("exists") is True and a.get("exists") is True:
                for field in ("value", "text"):
                    before_value = b.get(field)
                    after_value = a.get(field)
                    if (
                        before_value is not None
                        and after_value is not None
                        and before_value != after_value
                        and expected in str(after_value)
                    ):
                        return True
                return False

            # Some legitimate targets (e.g. calculator displays or custom
            # canvas controls) accept text but expose no focused editable
            # element. In that case allow a narrow fallback only when focus
            # is explicitly absent on both sides, the visible tree changed,
            # the payload appears in the new visible state, and it was not
            # already visible before. Unrelated UI changes cannot satisfy it.
            if b.get("exists") is not False or a.get("exists") is not False:
                return False
            before_tree = before.get("ui_tree_signature")
            after_tree = after.get("ui_tree_signature")
            if not cls._tree_changed(before, after):
                return False

            def visible_texts(tree):
                values = []
                if isinstance(tree, list):
                    for item in tree:
                        if not isinstance(item, dict):
                            continue
                        for field in ("name", "text", "value"):
                            text = str(item.get(field) or "").strip()
                            if text:
                                values.append(text)
                return values

            before_texts = visible_texts(before_tree)
            after_texts = visible_texts(after_tree)
            if any(expected.casefold() in item.casefold() for item in before_texts):
                return False
            return any(expected.casefold() in item.casefold() for item in after_texts)

        if kind == "value_changed":
            source = str(check.get("source", "focused_element"))
            before_value = cls._field(before, source, "value")
            after_value = cls._field(after, source, "value")
            return before_value is not None and after_value is not None and before_value != after_value

        if kind == "toggle_state_changed":
            b = cls._get(before, "target_element")
            a = cls._get(after, "target_element")
            if b.get("exists") is not True or a.get("exists") is not True:
                return False
            compared = [
                field for field in ("toggle_state", "selected")
                if field in b and field in a
                and b.get(field) is not None and a.get(field) is not None
            ]
            return bool(compared) and any(b.get(field) != a.get(field) for field in compared)

        if kind == "text_changed":
            source = str(check.get("source", "focused_element"))
            before_text = cls._field(before, source, "text")
            after_text = cls._field(after, source, "text")
            return before_text is not None and after_text is not None and before_text != after_text

        if kind == "contains_visible_text":
            expected = str(check.get("value") or "").strip()
            if not expected:
                return False
            visible_values = []
            tree = after.get("ui_tree_signature", [])
            if isinstance(tree, list):
                for item in tree:
                    if isinstance(item, dict):
                        for field in ("name", "text", "value"):
                            candidate = str(item.get(field) or "").strip()
                            if candidate:
                                visible_values.append(candidate)
            for source in ("active_window", "focused_element", "target_element"):
                item = after.get(source)
                if isinstance(item, dict):
                    for field in ("name", "title", "text", "value"):
                        candidate = str(item.get(field) or "").strip()
                        if candidate:
                            visible_values.append(candidate)
            numeric_expected = bool(re.fullmatch(r"-?\d+(?:\.\d+)?", expected))
            for candidate in visible_values:
                if not numeric_expected:
                    if expected.casefold() in candidate.casefold():
                        return True
                    continue
                for token in re.findall(r"(?<![\w.])-?\d+(?:\.\d+)?(?![\w.])", candidate):
                    try:
                        from decimal import Decimal
                        if Decimal(token) == Decimal(expected):
                            return True
                    except Exception:
                        continue
            return False

        if kind == "ui_tree_changed":
            return cls._tree_changed(before, after)

        if kind == "window_changed":
            return cls._window_changed(before, after)

        if kind == "focused_changed":
            return cls._focused_changed(before, after)

        if kind == "target_focused":
            target = cls._get(after, "target_element")
            return target.get("exists") is True and target.get("focused") is True

        if kind == "target_selected":
            target = cls._get(after, "target_element")
            return target.get("exists") is True and target.get("selected") is True

        return False

    @classmethod
    def _default_checks(
        cls,
        action: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        name = cls._norm(action.get("action"))

        if name == "find_ui_element":
            return [{"kind": "element_exists", "source": "target_element"}]

        if name in ("click", "double_click", "keypress", "hotkey", "scroll"):
            # Dispatch is not proof that the desktop reacted. A real state,
            # focus, window or UI-tree change is required for VERIFIED.
            return [
                {"kind": "ui_tree_changed"},
                {"kind": "window_changed", "source": "window"},
                {"kind": "focused_changed"},
            ]

        if name == "focus_ui_element":
            return [{
                "kind": "property",
                "source": "target_element",
                "field": "focused",
                "operator": "equals",
                "value": True,
            }]

        if name == "set_ui_value":
            args = action.get("args")
            args = dict(args) if isinstance(args, dict) else {}
            # ValuePattern.SetValue replaces the current value; containment
            # would incorrectly accept a longer, stale value (and fails for
            # the legitimate empty-string clear operation).
            return [{
                "kind": "property",
                "source": "target_element",
                "field": "value",
                "operator": "equals",
                "value": str(args.get("value", "")),
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
            return [{"kind": "toggle_state_changed", "source": "target_element"}]

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
            # A click/invoke is verified only when the observed target/window
            # state changes in a way attributable to the interaction, or the
            # target disappears. Pure dispatch is not accepted as state proof.
            return [
                {"kind": "state_changed", "source": "target_element"},
                {"kind": "target_focused"},
                {"kind": "target_selected"},
                {"kind": "element_not_exists", "source": "target_element"},
                {"kind": "ui_tree_changed"},
                {"kind": "window_changed"},
                {"kind": "focused_changed"},
            ]

        if name == "type_text":
            args = action.get("args")
            args = dict(args) if isinstance(args, dict) else {}
            value = args.get("text", action.get("target", ""))
            return [{"kind": "text_input_applied", "source": "focused_element", "value": str(value or "")}]

        return []

    def verify(
        self,
        action: Dict[str, Any],
        before: Dict[str, Any],
        after: Dict[str, Any],
        execution_result: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        execution_result = execution_result if isinstance(execution_result, dict) else {}
        executed = bool(execution_result.get("success", False))

        if not executed:
            return {
                "verified": False,
                "verification_level": "execution_failed",
                "method": "windows_ui_state",
                "checks": [],
                "reason": "Execution did not report success.",
            }

        metadata = action.get("metadata")
        verification_spec = (
            metadata.get("verification")
            if isinstance(metadata, dict)
            else None
        )

        if isinstance(verification_spec, dict):
            checks = verification_spec.get("checks", [])
            mode = self._norm(verification_spec.get("mode", "all"))
        else:
            checks = self._default_checks(action)
            mode = (
                "any"
                if self._norm(action.get("action"))
                in (
                    "click_ui_element", "invoke_ui_element", "toggle_ui_element",
                    "click", "double_click", "keypress", "hotkey", "scroll", "type_text",
                )
                else "all"
            )

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
