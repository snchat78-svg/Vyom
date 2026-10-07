"""Generic semantic grounding from an action target to a Windows UI element."""

from __future__ import annotations

from typing import Any, Dict, Optional

from windows_agent.ui_element_finder import UIElementFinder


class UIElementGrounder:
    """Resolve semantic targets using ranked UIA candidates and safe ambiguity handling."""

    def __init__(
        self,
        finder: Optional[UIElementFinder] = None,
        ambiguity_margin: float = 0.08,
        minimum_confidence: float = 0.32,
    ):
        self.finder = finder or UIElementFinder()
        self.ambiguity_margin = max(0.01, float(ambiguity_margin))
        self.minimum_confidence = min(1.0, max(0.0, float(minimum_confidence)))

    @staticmethod
    def _value(value: Any) -> str:
        return str(value or "").strip()

    def _ranked(self, **query):
        finder = self.finder
        ranked = getattr(finder, "find_ranked", None)
        if callable(ranked):
            return ranked(**query)
        best = getattr(finder, "find_best", None)
        if callable(best):
            item = best(**query)
            return [item] if item else []
        return []

    def ground(
        self,
        target: Any,
        args: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        args = dict(args or {})
        target = self._value(target)

        name = self._value(args.get("name"))
        automation_id = self._value(args.get("automation_id", args.get("auto_id")))
        control_type = self._value(args.get("control_type"))
        class_name = self._value(args.get("class_name"))
        window_title = self._value(args.get("window_title"))

        if not any((target, name, automation_id, control_type, class_name)):
            return {
                "success": False,
                "stage": "ui_target_missing",
                "message": "A semantic UI target or UIA property is required.",
            }

        query = {
            "name": name or target,
            "automation_id": automation_id,
            "control_type": control_type,
            "class_name": class_name,
            "window_title": window_title,
            "max_results": 5,
        }

        candidates = [
            item for item in self._ranked(**query)
            if isinstance(item, dict)
        ]
        if not candidates:
            return {
                "success": False,
                "stage": "ui_element_not_found",
                "message": f"No matching UI element was found for '{target or name}'.",
                "target": target or name,
                "query": {key: value for key, value in query.items() if key != "max_results"},
            }

        top = candidates[0]
        confidence = float(top.get("score", 1.0) or 0.0)
        second = candidates[1] if len(candidates) > 1 else None
        second_confidence = float(second.get("score", 0.0) or 0.0) if second else 0.0

        explicit_identity = bool(automation_id or control_type or class_name)

        ambiguous = (
            not explicit_identity
            and second is not None
            and confidence < 0.96
            and (confidence - second_confidence) < self.ambiguity_margin
        )
        if confidence < self.minimum_confidence:
            ambiguous = True

        if ambiguous:
            options = []
            for item in candidates[:5]:
                info = dict(item.get("info") or {})
                options.append({
                    "name": info.get("name", ""),
                    "control_type": info.get("control_type", ""),
                    "automation_id": info.get("automation_id", ""),
                    "confidence": float(item.get("score", 0.0) or 0.0),
                })
            return {
                "success": False,
                "stage": "ui_target_ambiguous",
                "message": (
                    f"I found multiple plausible UI elements for '{target or name}'. "
                    "More specific grounding is required before I act."
                ),
                "target": target or name,
                "query": {key: value for key, value in query.items() if key != "max_results"},
                "candidates": options,
            }

        element = top.get("element")
        info = dict(top.get("info") or {})
        return {
            "success": True,
            "stage": "ui_element_grounded",
            "element": element,
            "element_info": info,
            "confidence": confidence,
            "candidates": [
                {
                    "name": dict(item.get("info") or {}).get("name", ""),
                    "control_type": dict(item.get("info") or {}).get("control_type", ""),
                    "automation_id": dict(item.get("info") or {}).get("automation_id", ""),
                    "confidence": float(item.get("score", 0.0) or 0.0),
                }
                for item in candidates[:3]
            ],
            "verification": {
                "verified": True,
                "verification_level": "semantic_grounding",
                "method": "windows_ui_automation_ranked",
            },
        }


__all__ = ["UIElementGrounder"]
