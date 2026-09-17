"""
Project : Vyom AI
Version : 1.0
Module  : Goal Compiler

Purpose:
    Convert natural-language instructions into a structured goal
    without requiring a fixed command for every task.

Design:
    Natural language
        -> objective
        -> constraints/context
        -> simple executable intents (when safely recognizable)
        -> sub-goals (for simple compound requests)

This module NEVER executes anything.
"""

import re
from typing import Any, Dict, List, Optional


class GoalCompiler:

    _OPEN_WORDS = (
        "open", "launch", "start", "run", "khol", "kholo",
        "kholna", "chalu", "chalao", "open karo", "launch karo",
        "start karo", "खोल", "खोलो", "खोलना", "खोलें", "खोलिए", "खोलिये",
        "चालू", "चलाओ", "ओपन", "ओपन करो", "खोल दो", "खोलना है"
    )

    _CLOSE_WORDS = (
        "close", "quit", "exit", "stop", "band", "band karo",
        "band kar do", "rok", "rok do", "close karo",
        "बंद", "बंद करो", "बंद कर दो", "बन्द", "रोक", "रोक दो",
        "क्लोज", "क्लोज करो"
    )

    _SEARCH_WORDS = (
        "search", "find", "look for", "dhundo", "dhundho",
        "खोज", "खोजो", "ढूंढ", "ढूंढो", "ढूंढना"
    )

    _OPEN_FILE_EXTENSIONS = (
        ".txt", ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".csv",
        ".ppt", ".pptx", ".jpg", ".jpeg", ".png", ".gif", ".bmp",
        ".mp3", ".wav", ".mp4", ".avi", ".mkv", ".zip", ".rar",
        ".7z", ".py", ".dart", ".json", ".xml", ".html", ".htm"
    )

    def __init__(self):
        self.last_compilation: Optional[Dict[str, Any]] = None

    def normalize(self, text: Any) -> str:
        value = str(text or "").strip()
        value = re.sub(r"\s+", " ", value)
        return value

    def _clean_target(self, value: str) -> str:
        value = self.normalize(value)
        value = re.sub(
            r"^(?:please|pls|mujhe|mujhko|mere liye|zara|jara|the|a|an)\s+",
            "",
            value,
            flags=re.IGNORECASE,
        )
        value = re.sub(
            r"\s+(?:please|pls|please do|kar do|karna|kar|karo|do|दे दो|कर दो|करना|करो|खोल दो|खोलो)$",
            "",
            value,
            flags=re.IGNORECASE,
        )
        return value.strip()

    def _contains_any(self, text: str, words) -> bool:
        lowered = text.lower()
        return any(word.lower() in lowered for word in words)

    def _make_intent(self, intent: str, target: str) -> Dict[str, Any]:
        return {
            "intent": intent,
            "target": self._clean_target(target),
            "source": "goal_compiler",
        }

    def _compile_single_intent(self, text: str) -> Optional[Dict[str, Any]]:
        value = self.normalize(text)
        lower = value.lower()

        # Open target: verb before target.
        patterns = [
            (r"^(?:please\s+)?(?:open|launch|start|run|khol|kholo|kholna|chalu|chalao|open karo|launch karo|start karo|खोलो?|खोलना|खोलें|खोलिए|खोलिये|खोल दो|चालू करो|चालू|चलाओ|ओपन(?: करो)?)(?:\s+)(.+)$", "open"),
            (r"^(?:please\s+)?(.+?)\s+(?:open|launch|start|run|khol|kholo|chalu|chalao|open karo|launch karo|start karo|खोलो?|खोलना|खोलें|खोलिए|खोलिये|खोल दो|चालू करो|चालू|चलाओ|ओपन(?: करो)?)$", "open"),
        ]
        for pattern, family in patterns:
            match = re.match(pattern, value, flags=re.IGNORECASE)
            if match:
                target = self._clean_target(match.group(1))
                if target:
                    return self._make_intent(family, target)

        # Close target.
        patterns = [
            (r"^(?:please\s+)?(?:close|quit|exit|stop|band karo|band kar do|band|rok do|rok|close karo|बंद करो|बंद कर दो|बन्द करो|बन्द|रोक दो|रोक|क्लोज करो|क्लोज)\s+(.+)$", "close_app"),
            (r"^(?:please\s+)?(.+?)\s+(?:close|quit|exit|stop|band karo|band kar do|band|rok do|rok|close karo|बंद करो|बंद कर दो|बन्द करो|बन्द|रोक दो|रोक|क्लोज करो|क्लोज)$", "close_app"),
        ]
        for pattern, family in patterns:
            match = re.match(pattern, value, flags=re.IGNORECASE)
            if match:
                target = self._clean_target(match.group(1))
                if target:
                    return self._make_intent(family, target)

        # Search / find.
        for word in self._SEARCH_WORDS:
            pattern = r"^(?:please\s+)?(?:%s)\s+(.+)$" % re.escape(word)
            match = re.match(pattern, value, flags=re.IGNORECASE)
            if match:
                target = self._clean_target(match.group(1))
                if target:
                    return self._make_intent("search_file", target)

        # Direct file path/name.
        if any(lower.endswith(ext) for ext in self._OPEN_FILE_EXTENSIONS):
            return self._make_intent("open_file", value)

        return None

    def _targets_are_clean(self, targets: List[str]) -> bool:
        """Reject target fragments that secretly contain another action/clause."""

        action_words = list(self._OPEN_WORDS) + list(self._CLOSE_WORDS)
        normalized_actions = sorted(
            {
                self.normalize(word).lower()
                for word in action_words
                if self.normalize(word)
            },
            key=len,
            reverse=True
        )

        compound_words = (
            "then",
            "after that",
            "फिर",
            "उसके बाद",
        )

        for target in targets:
            value = self.normalize(target).lower()

            if not value:
                return False

            for action in normalized_actions:
                if value == action or value.startswith(action + " "):
                    return False

            if any(separator in value for separator in compound_words):
                return False

        return True

    def _shared_action_parts(self, goal: str) -> Optional[List[str]]:
        """Expand a shared action across multiple targets.

        Examples:
            "नोटपैड और कैलकुलेटर खोलो"
                -> ["नोटपैड खोलो", "कैलकुलेटर खोलो"]

            "open notepad and calculator"
                -> ["open notepad", "open calculator"]

        This is still deterministic goal compilation. It does not execute
        anything and therefore keeps the existing command/tool architecture
        intact.
        """

        value = self.normalize(goal)
        if not value:
            return None

        action_words = list(self._OPEN_WORDS) + list(self._CLOSE_WORDS)
        action_words = sorted(
            {str(word).strip() for word in action_words if str(word).strip()},
            key=len,
            reverse=True
        )

        action_pattern = "|".join(
            re.escape(word)
            for word in action_words
        )

        # -----------------------------------------------------
        # Action BEFORE multiple targets.
        # -----------------------------------------------------
        match = re.match(
            rf"^({action_pattern})\s+(.+?)$",
            value,
            flags=re.IGNORECASE,
        )

        if match:
            action = match.group(1).strip()
            target_text = match.group(2).strip(" ,")
            targets = [
                part.strip()
                for part in re.split(
                    r"\s*(?:,|and|aur|और)\s*",
                    target_text,
                    flags=re.IGNORECASE,
                )
                if part.strip()
            ]

            if (
                len(targets) >= 2
                and self._targets_are_clean(targets)
            ):
                return [
                    f"{action} {target}"
                    for target in targets
                ]

        # -----------------------------------------------------
        # Action AFTER multiple targets.
        # -----------------------------------------------------
        match = re.match(
            rf"^(.+?)\s+({action_pattern})$",
            value,
            flags=re.IGNORECASE,
        )

        if match:
            target_text = match.group(1).strip(" ,")
            action = match.group(2).strip()
            targets = [
                part.strip()
                for part in re.split(
                    r"\s*(?:,|and|aur|और)\s*",
                    target_text,
                    flags=re.IGNORECASE,
                )
                if part.strip()
            ]

            if (
                len(targets) >= 2
                and self._targets_are_clean(targets)
            ):
                return [
                    f"{target} {action}"
                    for target in targets
                ]

        return None

    def _split_compound(self, goal: str) -> List[str]:
        # First expand deterministic shared-action forms such as:
        #
        #     "नोटपैड और कैलकुलेटर खोलो"
        #     "open notepad and calculator"
        #
        # This allows the mission planner to receive two complete executable
        # intents instead of one partial compound sentence.
        shared_parts = self._shared_action_parts(goal)

        if shared_parts:
            return shared_parts

        # Only split when there is a clear action separator. Do not
        # split ordinary sentences containing "and" accidentally.
        separators = r"\s+(?:and|then|after that|aur|phir|fir|और|फिर|उसके बाद)\s+"
        parts = [
            part.strip()
            for part in re.split(separators, goal, flags=re.IGNORECASE)
            if part.strip()
        ]
        return parts if len(parts) > 1 else [goal]

    def compile(
        self,
        goal: str,
        intent: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        original = self.normalize(goal)
        ctx = context if isinstance(context, dict) else {}

        if not original:
            result = {
                "success": False,
                "understood": False,
                "goal": "",
                "objective": "",
                "complexity": "none",
                "suggested_intents": [],
                "sub_goals": [],
                "reason": "Empty goal.",
            }
            self.last_compilation = result
            return result

        suggested: List[Dict[str, Any]] = []

        if isinstance(intent, dict):
            intent_name = str(intent.get("intent") or "").strip()
            target = str(intent.get("target") or "").strip()
            if intent_name in (
                "open", "open_file", "search_file",
                "search_and_open_file", "close_app"
            ) and target:
                suggested.append(dict(intent))

        parts = self._split_compound(original)

        if not suggested:
            for part in parts:
                compiled = self._compile_single_intent(part)
                if compiled:
                    target = str(compiled.get("target") or "").lower()
                    if target in ("it", "this", "that", "इसे", "इसे", "वह", "वो"):
                        compiled = None
                if compiled:
                    suggested.append(compiled)

        # Safety boundary for compound goals: if only some parts have a
        # deterministic intent, do not treat the partial result as a complete
        # executable goal. This prevents "open X and do Y" from silently
        # executing only "open X". The next reasoning/capability phase can
        # decide how to handle the missing part.
        partial_compilation = bool(
            len(parts) > 1
            and 0 < len(suggested) < len(parts)
        )

        if partial_compilation:
            suggested = []

        # Context-aware short follow-ups.
        lowered = original.lower()
        if not suggested and lowered in (
            "open it", "open this", "isko kholo", "इसे खोलो",
            "इसे खोल दो", "वह खोलो", "वो खोलो"
        ):
            target = ctx.get("current_target") or ctx.get("current_file") or ctx.get("current_app")
            if target:
                suggested.append(self._make_intent("open", str(target)))

        if not suggested and lowered in (
            "close it", "close this", "isko band karo", "इसे बंद करो",
            "इसे बंद कर दो", "वह बंद करो", "वो बंद करो"
        ):
            target = ctx.get("current_app") or ctx.get("current_target")
            if target:
                suggested.append(self._make_intent("close_app", str(target)))

        complexity = "simple"
        if len(suggested) > 1:
            complexity = "medium"
        elif any(word in lowered for word in (
            "create", "make", "build", "write", "edit", "modify",
            "automate", "code", "coding", "develop", "excel", "website",
            "program", "फाइल बनाओ", "बनाओ", "कोड", "ऑटोमेट"
        )):
            complexity = "complex"

        sub_goals = []
        for index, part in enumerate(parts, start=1):
            sub_goals.append({
                "step": index,
                "goal": part,
                "intent": suggested[index - 1] if index <= len(suggested) else None,
            })

        result = {
            "success": True,
            "understood": True,
            "goal": original,
            "objective": original,
            "complexity": complexity,
            "constraints": [],
            "context_used": bool(ctx),
            "suggested_intents": suggested,
            "sub_goals": sub_goals,
            "partial_compilation": partial_compilation,
            "requires_new_capability": not bool(suggested),
            "reason": (
                "Goal compiled into existing executable intents."
                if suggested
                else (
                    "Compound goal was only partially recognized; "
                    "no partial execution is allowed."
                    if partial_compilation
                    else "Goal understood at a high level; no existing executable intent was safely matched."
                )
            ),
        }
        self.last_compilation = result
        return result


