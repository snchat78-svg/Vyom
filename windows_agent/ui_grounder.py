"""Generic semantic grounding from an action target to a Windows UI element."""

from __future__ import annotations

from typing import Any, Dict, Optional

from windows_agent.ui_element_finder import UIElementFinder


class UIElementGrounder:
    """Resolve a semantic target using stable UIA properties."""

    def __init__(self, finder: Optional[UIElementFinder] = None):
        self.finder = finder or UIElementFinder()

    @staticmethod
    def _value(value: Any) -> str:
        return str(value or "").strip()

    def ground(self, target: Any, args: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
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

        # Explicit UIA properties are authoritative. A plain target is treated
        # as a UI name only; application-specific aliases are never embedded.
        result = self.finder.find_best(
            name=name or target,
            automation_id=automation_id,
            control_type=control_type,
            class_name=class_name,
            window_title=window_title,
        )
        if not result:
            return {
                "success": False,
                "stage": "ui_element_not_found",
                "message": f"No matching UI element was found for '{target or name}'.",
                "target": target or name,
                "query": {
                    "name": name or target,
                    "automation_id": automation_id,
                    "control_type": control_type,
                    "class_name": class_name,
                    "window_title": window_title,
                },
            }

        return {
            "success": True,
            "stage": "ui_element_grounded",
            "element": result["element"],
            "element_info": dict(result.get("info") or {}),
            "verification": {
                "verified": True,
                "verification_level": "semantic_grounding",
                "method": "windows_ui_automation",
            },
        }


__all__ = ["UIElementGrounder"]
