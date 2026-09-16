"""Goal-vs-command routing for Vyom.

This module decides whether an input should remain on the existing
single-action command path or enter AutonomousAgent as a user goal.
It never executes tools and does not change the existing command parser.
"""

import re
from typing import Any, Dict, Optional


class GoalRouter:
    """Classify an input before command execution.

    The router is intentionally conservative: ordinary one-action commands
    remain on the proven fast path. Inputs with explicit multi-step structure
    are sent to the existing AutonomousAgent without passing a partially
    parsed intent that could accidentally collapse a goal into one action.
    """

    COMPOUND_SEPARATORS = (
        "और", "फिर", "उसके बाद", "और फिर",
        "and", "then", "after that",
    )

    TASK_MARKERS = (
        "create", "make", "build", "write", "type", "enter", "save",
        "edit", "modify", "rename", "move", "copy", "delete", "fill",
        "बनाओ", "बनाना", "बनाएं", "बनाएँ", "बना दो", "बनाकर",
        "लिखो", "लिखना", "लिखें", "टाइप", "डालो", "डालना", "सेव",
        "सहेज", "बदल", "एडिट", "नाम बदल", "कॉपी", "मूव", "हटाओ",
        "भरो", "भरना",
    )

    def normalize(self, text: Any) -> str:
        value = str(text or "").strip().lower()
        return re.sub(r"\s+", " ", value)

    def has_compound_structure(self, text: Any) -> bool:
        value = self.normalize(text)
        if not value:
            return False

        # Treat explicit separators as multi-step only when there is content
        # on both sides. This avoids false positives from ordinary sentences.
        for separator in self.COMPOUND_SEPARATORS:
            pattern = (
                r"\S(?:.*\S)?\s+"
                + re.escape(separator)
                + r"\s+\S"
            )

            if re.search(
                pattern,
                value,
                flags=re.IGNORECASE
            ):
                return True

        # Also recognise punctuation-based multi-step requests.
        if re.search(r";\s*\S", value):
            return True

        return False

    def has_task_marker(self, text: Any) -> bool:
        value = self.normalize(text)

        return any(
            marker in value
            for marker in self.TASK_MARKERS
        )

    def route(
        self,
        command: Any,
        intent: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:

        text = self.normalize(command)

        if not text:
            return {
                "route": "command",
                "reason": "empty_input",
                "goal": False,
            }

        compound = self.has_compound_structure(text)
        task_marker = self.has_task_marker(text)

        # Explicit multi-step structure always wins.
        # Do not pass the parsed one-action intent into
        # AutonomousAgent for such input.
        if compound:
            return {
                "route": "goal",
                "reason": "compound_structure",
                "goal": True,
                "compound": True,
                "task_marker": task_marker,
            }

        # Task language without a clear separator is also a goal
        # when it is not one of the already-recognised deterministic
        # command intents.
        intent_name = ""

        if isinstance(
            intent,
            dict
        ):
            intent_name = str(
                intent.get(
                    "intent"
                ) or ""
            ).strip().lower()

        deterministic = {
            "open",
            "open_file",
            "search_file",
            "search_and_open_file",
            "close_app",
            "close_current",
            "conversation",
            "selection",
        }

        if (
            task_marker
            and
            intent_name not in deterministic
        ):
            return {
                "route": "goal",
                "reason": "task_language",
                "goal": True,
                "compound": False,
                "task_marker": True,
            }

        return {
            "route": "command",
            "reason": "single_action_or_conversation",
            "goal": False,
            "compound": False,
            "task_marker": task_marker,
        }

    def classify(
        self,
        command: Any,
        intent: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Backward-compatible alias for route().

        IntentEngine in the current main branch still calls
        classify(). Keeping this alias prevents that caller
        from raising AttributeError while preserving route()
        as the canonical API used by Executor.
        """

        return self.route(
            command,
            intent=intent
        )
