"""Generic Windows UI Automation element discovery.

Uses Microsoft's UI Automation tree through pywinauto when available.
Discovery is application-agnostic and ranks semantic candidates instead of
requiring exact control names.

No application names or fixed coordinates are embedded here.
"""

from __future__ import annotations

import difflib
import os
import re
from typing import Any, Dict, List, Optional


class UIElementFinder:
    """Discover and rank semantic UI elements from a window or the desktop."""

    def __init__(self, backend: str = "uia"):
        self.backend = backend
        self.available = False
        self._pywinauto = None
        self._Desktop = None
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
    def _norm(cls, value: Any) -> str:
        return cls._text(value).lower()

    @classmethod
    def _tokens(cls, value: Any) -> List[str]:
        return re.findall(r"[\\w\\u0900-\\u097F]+", cls._norm(value))

    @classmethod
    def _name_similarity(cls, wanted: str, actual: str) -> float:
        wanted = cls._norm(wanted)
        actual = cls._norm(actual)
        if not wanted or not actual:
            return 0.0
        if wanted == actual:
            return 1.0

        ratio = difflib.SequenceMatcher(None, wanted, actual).ratio()

        if wanted in actual:
            ratio = max(ratio, min(0.96, 0.72 + 0.20 * len(wanted) / max(1, len(actual))))

        wanted_tokens = set(cls._tokens(wanted))
        actual_tokens = set(cls._tokens(actual))
        if wanted_tokens and actual_tokens:
            overlap = len(wanted_tokens & actual_tokens) / len(wanted_tokens)
            ratio = max(ratio, 0.50 + 0.45 * overlap)

        return min(1.0, ratio)

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

    def _root(self, desktop, hwnd: Optional[int], window_title: str):
        root = desktop

        if hwnd is not None:
            try:
                return desktop.window(handle=int(hwnd))
            except Exception:
                return None

        if window_title:
            return root

        try:
            return desktop.get_active()
        except Exception:
            return desktop

    @staticmethod
    def _window_matches(element: Any, window_title: str) -> bool:
        wanted = " ".join(str(window_title or "").strip().lower().split())
        if not wanted:
            return True
        try:
            parent = element.top_level_parent()
            actual = " ".join(str(parent.window_text()).strip().lower().split())
            return wanted in actual
        except Exception:
            return False

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
        """Find UIA controls and return candidates ordered by semantic score.

        Stable UIA properties (AutomationId/ControlType/ClassName) act as
        hard filters. A human semantic name is ranked rather than requiring an
        exact string match, which tolerates ordinary wording and small STT
        distortions.
        """
        if not self.is_available():
            return []

        desktop = self._desktop()
        root = self._root(desktop, hwnd, window_title)
        if root is None:
            return []

        # Do not pass name as an exact UIA title filter. That would defeat
        # semantic/fuzzy matching and make "search box" fail on a "Search"
        # control. Stable structural properties remain exact filters.
        query: Dict[str, Any] = {}
        if automation_id:
            query["auto_id"] = automation_id
        if control_type:
            query["control_type"] = control_type
        if class_name:
            query["class_name"] = class_name

        try:
            elements = root.descendants(**query) if query else root.descendants()
        except Exception:
            return []

        wanted_name = self._norm(name)
        wanted_id = self._norm(automation_id)
        wanted_type = self._norm(control_type)
        wanted_class = self._norm(class_name)
        scored: List[tuple[float, Dict[str, Any]]] = []

        for element in elements:
            if not self._window_matches(element, window_title):
                continue

            info = self._info(element)
            actual_name = self._norm(info.get("name"))
            actual_id = self._norm(info.get("automation_id"))
            actual_type = self._norm(info.get("control_type"))
            actual_class = self._norm(info.get("class_name"))

            # query already filters these properties, but retain defensive
            # checks for wrappers that implement descendants() loosely.
            if wanted_id and actual_id != wanted_id:
                continue
            if wanted_type and actual_type != wanted_type:
                continue
            if wanted_class and actual_class != wanted_class:
                continue

            score = 0.0

            if wanted_name:
                similarity = self._name_similarity(wanted_name, actual_name)
                if similarity <= 0.18:
                    continue
                score += similarity * 70.0
            else:
                score += 35.0

            if wanted_id:
                score += 20.0
            if wanted_type:
                score += 8.0
            if wanted_class:
                score += 6.0

            if info.get("enabled", True):
                score += 2.0
            if info.get("visible", True):
                score += 2.0

            scored.append((
                score,
                {
                    "element": element,
                    "info": info,
                    "score": round(score / 110.0, 4),
                },
            ))

        scored.sort(
            key=lambda pair: (
                -pair[0],
                self._norm(pair[1]["info"].get("name")),
                self._norm(pair[1]["info"].get("automation_id")),
            )
        )

        return [item for _, item in scored[: max(1, int(max_results))]]

    def find_ranked(self, **kwargs) -> List[Dict[str, Any]]:
        """Return candidates with confidence/score metadata."""
        return self.find(**kwargs)

    def find_best(self, **kwargs) -> Optional[Dict[str, Any]]:
        matches = self.find_ranked(**kwargs)
        if not matches:
            return None
        return matches[0]

    @staticmethod
    def serializable(result: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not result:
            return None
        return dict(result.get("info") or {})


__all__ = ["UIElementFinder"]
