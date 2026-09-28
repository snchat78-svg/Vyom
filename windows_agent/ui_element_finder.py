"""Generic Windows UI Automation element discovery.

Uses Microsoft's UI Automation tree through pywinauto when available. The
dependency is optional so existing Vyom functionality remains usable on
systems where UI Automation is unavailable.

No application names or fixed control coordinates are embedded here.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional


class UIElementFinder:
    """Discover semantic UI elements from a window or the desktop."""

    def __init__(self, backend: str = "uia"):
        self.backend = backend
        self.available = False
        self._pywinauto = None
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

    @classmethod
    def _info(cls, element: Any) -> Dict[str, Any]:
        info: Dict[str, Any] = {}
        try:
            wrapper = element.wrapper_object()
            info["name"] = cls._text(getattr(wrapper, "window_text", lambda: "")())
            info["control_type"] = cls._text(getattr(wrapper, "control_type", lambda: "")())
            info["automation_id"] = cls._text(getattr(wrapper, "automation_id", lambda: "")())
            info["class_name"] = cls._text(getattr(wrapper, "class_name", lambda: "")())
            info["enabled"] = bool(getattr(wrapper, "is_enabled", lambda: True)())
            info["visible"] = bool(getattr(wrapper, "is_visible", lambda: True)())
        except Exception:
            pass
        return info

    def _desktop(self):
        if not self.is_available():
            raise RuntimeError("Windows UI Automation is unavailable.")
        return self._Desktop(backend=self.backend)

    def find(
        self,
        *,
        name: str = "",
        automation_id: str = "",
        control_type: str = "",
        class_name: str = "",
        window_title: str = "",
        hwnd: Optional[int] = None,
        max_results: int = 20,
    ) -> List[Dict[str, Any]]:
        """Find controls using UIA properties and return wrappers + metadata."""
        if not self.is_available():
            return []

        desktop = self._desktop()
        query: Dict[str, Any] = {}
        if name:
            query["title"] = name
        if automation_id:
            query["auto_id"] = automation_id
        if control_type:
            query["control_type"] = control_type
        if class_name:
            query["class_name"] = class_name

        root = desktop
        if hwnd is not None:
            try:
                root = desktop.window(handle=int(hwnd))
            except Exception:
                return []

        try:
            elements = root.descendants(**query) if query else root.descendants()
        except Exception:
            return []

        results: List[Dict[str, Any]] = []
        wanted_name = self._text(name).lower()
        wanted_type = self._text(control_type).lower()
        wanted_class = self._text(class_name).lower()
        wanted_id = self._text(automation_id).lower()

        for element in elements:
            info = self._info(element)
            if window_title:
                try:
                    parent = element.top_level_parent()
                    parent_title = self._text(parent.window_text()).lower()
                    if self._text(window_title).lower() not in parent_title:
                        continue
                except Exception:
                    continue

            checks = [
                (wanted_name, self._text(info.get("name")).lower()),
                (wanted_type, self._text(info.get("control_type")).lower()),
                (wanted_class, self._text(info.get("class_name")).lower()),
                (wanted_id, self._text(info.get("automation_id")).lower()),
            ]
            if any(wanted and wanted != actual for wanted, actual in checks):
                continue

            results.append({
                "element": element,
                "info": info,
            })
            if len(results) >= max(1, int(max_results)):
                break

        return results

    def find_best(self, **kwargs) -> Optional[Dict[str, Any]]:
        matches = self.find(**kwargs)
        return matches[0] if matches else None

    @staticmethod
    def serializable(result: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not result:
            return None
        return dict(result.get("info") or {})


__all__ = ["UIElementFinder"]
