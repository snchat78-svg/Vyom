"""Safe command-vs-goal boundary for Vyom.

The router only classifies user input. It never executes tools and never
modifies the existing command/executor pipeline.
"""

import re
from typing import Any, Dict, Optional


class GoalRouter:
    """Identify explicit multi-step goals before single-action parsing."""

    COMPOUND_SEPARATORS = (
        "और फिर",
        "उसके बाद",
        "और",
        "फिर",
        "after that",
        "then",
        "and",
    )

    TASK_MARKERS = (
        "create", "make", "build", "write", "type", "enter", "save",
        "edit", "modify", "rename", "move", "copy", "delete", "fill",
        "बनाओ", "बनाना", "बनाएं", "बनाएँ", "बना दो", "बनाकर",
        "लिखो", "लिखना", "लिखें", "टाइप", "डालो", "डालना", "सेव",
        "सहेज", "बदल", "एडिट", "नाम बदल", "कॉपी", "मूव", "हटाओ",
        "भरो", "भरना",
    )

    def normalize(self, value: Any) -> str:
        text = str(value or "").strip().lower()
        return re.sub(r"\s+", " ", text)

    def has_compound_structure(self, value: Any) -> bool:
        text = self.normalize(value)
        if not text:
            return False

        for separator in self.COMPOUND_SEPARATORS:
            pattern = r"\S(?:.*\S)?\s+" + re.escape(separator) + r"\s+\S"
            if re.search(pattern, text, flags=re.IGNORECASE):
                return True

        return bool(re.search(r";\s*\S", text))

    def has_task_marker(self, value: Any) -> bool:
        text = self.normalize(value)
        return any(marker in text for marker in self.TASK_MARKERS)

    def classify(
        self,
        value: Any,
        intent: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        text = self.normalize(value)
        if not text:
            return {"route": "command", "reason": "empty_input"}

        compound = self.has_compound_structure(text)
        task_marker = self.has_task_marker(text)

        if compound:
            return {
                "route": "goal",
                "reason": "compound_structure",
                "compound": True,
                "task_marker": task_marker,
            }

        intent_name = ""
        if isinstance(intent, dict):
            intent_name = str(intent.get("intent") or "").strip().lower()

        deterministic = {
            "open", "open_file", "search_file", "search_and_open_file",
            "close_app", "close_current", "conversation", "selection",
        }

        if task_marker and intent_name not in deterministic:
            return {
                "route": "goal",
                "reason": "task_language",
                "compound": False,
                "task_marker": True,
            }

        return {
            "route": "command",
            "reason": "single_action_or_conversation",
            "compound": False,
            "task_marker": task_marker,
        }
