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
        "start karo", "खोल", "खोलो", "खोलना", "खोलिए", "खोलिये",
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
            (r"^(?:please\s+)?(?:open|launch|start|run|khol|kholo|kholna|chalu|chalao|open karo|launch karo|start karo|खोलो?|खोलना|खोलिए|खोलिये|खोल दो|चालू करो|चालू|चलाओ|ओपन(?: करो)?)(?:\s+)(.+)$", "open"),
            (r"^(?:please\s+)?(.+?)\s+(?:open|launch|start|run|khol|kholo|chalu|chalao|open karo|launch karo|start karo|खोलो?|खोलना|खोलिए|खोलिये|खोल दो|चालू करो|चालू|चलाओ|ओपन(?: करो)?)$", "open"),
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

    def _split_compound(self, goal: str) -> List[str]:
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

        if not suggested:
            for part in self._split_compound(original):
                compiled = self._compile_single_intent(part)
                if compiled:
                    target = str(compiled.get("target") or "").lower()
                    if target in ("it", "this", "that", "इसे", "इसे", "वह", "वो"):
                        compiled = None
                if compiled:
                    suggested.append(compiled)

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
        for index, part in enumerate(self._split_compound(original), start=1):
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
            "requires_new_capability": not bool(suggested),
            "reason": (
                "Goal compiled into existing executable intents."
                if suggested
                else "Goal understood at a high level; no existing executable intent was safely matched."
            ),
        }
        self.last_compilation = result
        return result

