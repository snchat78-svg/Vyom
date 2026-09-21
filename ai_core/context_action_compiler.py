"""
Project : Vyom AI
Version : 1.0
Module  : Context Action Compiler

Purpose:
    Convert short natural-language follow-up instructions into generic
    computer actions while preserving Vyom's existing command fast path.

Key design rules:
    - No application names are embedded.
    - No new user-facing command/intent table is introduced.
    - Existing legacy open/close/search intents are reused only when the
      existing GoalCompiler can already recognize them.
    - Generic UI operations remain provider-agnostic Action Schema data.
    - Session context is used to continue work across turns.
    - A partially understood multi-step request is never executed partially.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional


class ContextActionCompiler:
    """Compile contextual follow-ups into an ordered generic/legacy plan."""

    _ACTION_MARKERS = (
        "type", "write", "enter", "paste", "press", "hit", "keypress",
        "hotkey", "shortcut", "click", "double click", "double-click",
        "scroll", "focus", "wait", "copy", "cut", "undo", "redo",
        "select all", "टाइप", "लिख", "डाल", "दबाओ", "दबाएँ", "क्लिक",
        "स्क्रोल", "फोकस", "रुको", "रुकें",
    )

    _SEPARATORS = re.compile(
        r"\s+(?:and|then|after that|aur|phir|fir|और|फिर|उसके बाद|और फिर)\s+",
        flags=re.IGNORECASE,
    )

    def __init__(self, goal_compiler: Optional[Any] = None):
        self.goal_compiler = goal_compiler

    @staticmethod
    def _normalize(value: Any) -> str:
        return re.sub(r"\s+", " ", str(value or "").strip())

    @classmethod
    def _contains_marker(cls, text: str) -> bool:
        value = text.lower()
        return any(marker in value for marker in cls._ACTION_MARKERS)

    def _split(self, goal: str) -> List[str]:
        text = self._normalize(goal)
        if not text:
            return []
        if self.goal_compiler is not None:
            splitter = getattr(self.goal_compiler, "_split_compound", None)
            if callable(splitter):
                try:
                    parts = splitter(text)
                    if isinstance(parts, list) and parts:
                        return [self._normalize(part) for part in parts if self._normalize(part)]
                except Exception:
                    pass
        return [self._normalize(part) for part in self._SEPARATORS.split(text) if self._normalize(part)]

    @staticmethod
    def _context_target(context: Dict[str, Any]) -> str:
        return str(
            context.get("current_target")
            or context.get("current_app")
            or context.get("current_file")
            or ""
        ).strip()

    @staticmethod
    def _extract_name(history: Any) -> Optional[str]:
        """Use only an explicitly stated name from the current session history."""
        if not isinstance(history, list):
            return None
        patterns = (
            re.compile(r"\bmy\s+name\s+is\s+([A-Za-z][A-Za-z .'-]{0,80})", re.IGNORECASE),
            re.compile(r"\bmera\s+naam\s+(?:is|hai)?\s*([A-Za-z][A-Za-z .'-]{0,80})", re.IGNORECASE),
            re.compile(r"मेरा\s+नाम\s+(?:है\s*)?([\u0900-\u097F A-Za-z][\u0900-\u097F A-Za-z .'-]{0,80})", re.IGNORECASE),
        )
        stop = re.compile(r"\s+(?:ko|hai|is|please|pls|likho|likhen|type|टाइप|लिखो|लिखें|है|को)\s*$", re.IGNORECASE)
        for item in reversed(history):
            if not isinstance(item, dict) or str(item.get("role", "")).lower() != "user":
                continue
            text = ContextActionCompiler._normalize(item.get("text", ""))
            for pattern in patterns:
                match = pattern.search(text)
                if match:
                    value = stop.sub("", match.group(1)).strip(" ,.-")
                    if value:
                        return value
        return None

    def _resolve_text(self, value: str, context: Dict[str, Any]) -> Dict[str, Any]:
        text = self._normalize(value)
        lowered = text.lower()
        if lowered in {"my name", "mera naam", "मेरा नाम"}:
            name = self._extract_name(context.get("conversation_history", []))
            if not name:
                return {
                    "resolved": False,
                    "clarification": "मैं आपका नाम session में नहीं जानता। पहले अपना नाम बताइए।",
                }
            return {"resolved": True, "value": name, "reference": "session.user_name"}
        return {"resolved": True, "value": text, "reference": None}

    def _legacy_intent(self, text: str) -> Optional[Dict[str, Any]]:
        compiler = self.goal_compiler
        method = getattr(compiler, "_compile_single_intent", None) if compiler is not None else None
        if not callable(method):
            return None
        try:
            result = method(text)
        except Exception:
            return None
        return result if isinstance(result, dict) else None

    def _generic_action(self, text: str, context: Dict[str, Any]) -> Dict[str, Any]:
        value = self._normalize(text)
        lower = value.lower()
        current_target = self._context_target(context)
        base = {
            "type": "action",
            "capability": "windows_ui",
            "target": "",
            "args": {},
            "preconditions": [],
            "postconditions": [],
            "depends_on": [],
            "description": value,
        }

        # Text entry: generic and application-agnostic.
        match = re.match(
            r"^(?:please\s+)?(?:type|write|enter|paste|टाइप\s+कर(?:ो|ें|ना)?|टाइप|लिखो|लिखें|लिख|डालो|डालें|डाल)\s+(.+)$",
            value,
            flags=re.IGNORECASE,
        )
        if match:
            if not current_target:
                return {
                    "kind": "clarification",
                    "message": "किस active application या input target में text लिखना है? पहले उसे खोलें या focus करें।",
                }
            resolved = self._resolve_text(match.group(1), context)
            if not resolved.get("resolved"):
                return {"kind": "clarification", "message": resolved.get("clarification", "क्या text लिखना है?")}
            base.update({
                "action": "type_text",
                "target": resolved["value"],
                "args": {"text": resolved["value"]},
                "preconditions": ["an active input target is available"],
                "postconditions": ["the requested text has been dispatched to the active input target"],
            })
            return {"kind": "action", "action": base}

        # Generic key presses and hotkeys.
        if re.match(r"^(?:please\s+)?(?:select\s+all|all\s+select|सब\s+चुनो)$", value, re.IGNORECASE):
            base.update({
                "action": "hotkey",
                "target": "ctrl+a",
                "args": {"keys": ["ctrl", "a"]},
                "postconditions": ["the current input selection contains all selectable content"],
            })
            return {"kind": "action", "action": base}

        match = re.match(r"^(?:please\s+)?(?:hotkey|shortcut)\s+(.+)$", value, re.IGNORECASE)
        if match:
            keys = [part.strip() for part in re.split(r"\s*\+\s*", match.group(1)) if part.strip()]
            if len(keys) < 2:
                return {"kind": "clarification", "message": "कृपया hotkey के लिए कम से कम दो keys बताइए।"}
            base.update({
                "action": "hotkey",
                "target": "+".join(keys),
                "args": {"keys": keys},
                "postconditions": ["the requested key combination has been dispatched"],
            })
            return {"kind": "action", "action": base}

        match = re.match(r"^(?:please\s+)?(?:press|hit|keypress|दबाओ|दबाएँ|दबाएं)\s+(.+)$", value, re.IGNORECASE)
        if match:
            key = self._normalize(match.group(1))
            base.update({
                "action": "keypress",
                "target": key,
                "args": {"key": key},
                "postconditions": ["the requested key has been dispatched"],
            })
            return {"kind": "action", "action": base}

        simple_keys = {
            "copy": ["ctrl", "c"],
            "cut": ["ctrl", "x"],
            "paste": ["ctrl", "v"],
            "undo": ["ctrl", "z"],
            "redo": ["ctrl", "y"],
            "कॉपी": ["ctrl", "c"],
            "कट": ["ctrl", "x"],
            "पेस्ट": ["ctrl", "v"],
            "अनडू": ["ctrl", "z"],
            "रीडू": ["ctrl", "y"],
        }
        if lower in simple_keys:
            keys = simple_keys[lower]
            base.update({
                "action": "hotkey",
                "target": "+".join(keys),
                "args": {"keys": keys},
                "postconditions": ["the requested editing shortcut has been dispatched"],
            })
            return {"kind": "action", "action": base}

        match = re.match(r"^(?:please\s+)?(?:scroll|स्क्रोल)\s+(up|down|ऊपर|नीचे)(?:\s+(\d+))?$", lower, re.IGNORECASE)
        if match:
            direction = match.group(1)
            amount = int(match.group(2) or 1)
            amount = amount if direction in {"down", "नीचे"} else -amount
            base.update({
                "action": "scroll",
                "target": str(amount),
                "args": {"amount": amount},
                "postconditions": ["the requested scroll input has been dispatched"],
            })
            return {"kind": "action", "action": base}

        match = re.match(r"^(?:please\s+)?(?:wait|रुको|रुकें)\s+(\d+(?:\.\d+)?)\s*(?:seconds?|secs?|s|सेकंड|सेकंड्स)$", lower, re.IGNORECASE)
        if match:
            seconds = float(match.group(1))
            base.update({
                "action": "wait",
                "target": str(seconds),
                "args": {"seconds": seconds},
                "postconditions": ["the requested wait interval has elapsed"],
            })
            return {"kind": "action", "action": base}

        match = re.match(r"^(?:please\s+)?(?:focus|फोकस)\s+(.+)$", value, re.IGNORECASE)
        if match:
            target = self._normalize(match.group(1))
            base.update({
                "action": "focus_window",
                "target": target,
                "args": {},
                "postconditions": ["the requested window is foreground"],
            })
            return {"kind": "action", "action": base}

        # Explicit coordinates are the only low-level click form accepted in
        # Step 2B. Semantic control finding belongs to the later vision layer.
        match = re.match(r"^(?:please\s+)?(?:double[- ]?click|डबल\s+क्लिक)(?:\s+at|\s+पर)?\s*(-?\d+)\s*[, ]\s*(-?\d+)$", value, re.IGNORECASE)
        if match:
            x, y = int(match.group(1)), int(match.group(2))
            base.update({
                "action": "double_click",
                "target": f"{x},{y}",
                "args": {"x": x, "y": y},
                "postconditions": ["the requested mouse action has been dispatched"],
            })
            return {"kind": "action", "action": base}

        match = re.match(r"^(?:please\s+)?(?:click|क्लिक)(?:\s+at|\s+पर)?\s*(-?\d+)\s*[, ]\s*(-?\d+)$", value, re.IGNORECASE)
        if match:
            x, y = int(match.group(1)), int(match.group(2))
            base.update({
                "action": "click",
                "target": f"{x},{y}",
                "args": {"x": x, "y": y},
                "postconditions": ["the requested mouse action has been dispatched"],
            })
            return {"kind": "action", "action": base}

        if re.match(r"^(?:screenshot|screen\s+shot|स्क्रीनशॉट)$", value, re.IGNORECASE):
            base.update({
                "action": "screenshot",
                "target": "",
                "args": {},
                "postconditions": ["a current screen capture has been created"],
            })
            return {"kind": "action", "action": base}

        if re.match(r"^(?:read\s+(?:active\s+)?window|show\s+windows|windows\s+list|विंडो\s+दिखाओ)$", value, re.IGNORECASE):
            action = "read_active_window" if "active" in lower or "विंडो" in lower else "read_windows"
            base.update({
                "action": action,
                "target": "",
                "args": {},
                "postconditions": ["current Windows state has been observed"],
            })
            return {"kind": "action", "action": base}

        # A generic type/click/etc phrase without a resolvable form should not
        # silently fall through to the capability builder.
        if self._contains_marker(value):
            return {"kind": "clarification", "message": "मैं इस instruction को safely execute करने के लिए थोड़ा और detail चाहता हूँ।"}

        return {"kind": "unrecognized"}

    def compile(self, goal: Any, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        value = self._normalize(goal)
        ctx = context if isinstance(context, dict) else {}
        parts = self._split(value)
        if not parts:
            return {"success": False, "complete": False, "plan": [], "reason": "empty_goal"}

        steps: List[Dict[str, Any]] = []
        previous_id: Optional[str] = None
        unresolved_parts: List[str] = []
        clarification: Optional[str] = None

        for index, part in enumerate(parts, start=1):
            legacy = self._legacy_intent(part)
            if legacy and legacy.get("intent") and legacy.get("target"):
                step_id = f"context_{index}"
                step = {
                    "step": index,
                    "id": step_id,
                    "type": "execute_existing_intent",
                    "goal": value,
                    "intent": {
                        "intent": str(legacy.get("intent")).strip().lower(),
                        "target": str(legacy.get("target")).strip(),
                    },
                    "depends_on": [previous_id] if previous_id else [],
                    "status": "pending",
                }
                steps.append(step)
                previous_id = step_id
                continue

            generic = self._generic_action(part, ctx)
            if generic.get("kind") == "action":
                action = dict(generic["action"])
                action_id = f"context_{index}"
                action["id"] = action_id
                action["step"] = index
                action["goal"] = value
                action["depends_on"] = [previous_id] if previous_id else []
                action["status"] = "pending"
                steps.append(action)
                previous_id = action_id
                continue

            if generic.get("kind") == "clarification":
                unresolved_parts.append(part)
                if not clarification:
                    clarification = str(generic.get("message") or "कृपया थोड़ा और detail बताइए।")
                continue

            unresolved_parts.append(part)

        # Never return a partial executable plan. This is critical for
        # requests such as "open X and do unknown Y".
        if unresolved_parts:
            return {
                "success": True,
                "complete": False,
                "partial": bool(steps),
                "plan": [],
                "unresolved_parts": unresolved_parts,
                "clarification": clarification,
                "continuation": False,
                "reason": "Some instruction parts could not be resolved safely.",
            }

        generic = any(step.get("type") == "action" for step in steps)
        legacy = any(step.get("type") == "execute_existing_intent" for step in steps)
        continuation = bool(generic and not legacy)

        return {
            "success": True,
            "complete": True,
            "partial": False,
            "plan": steps,
            "continuation": continuation,
            "context_target": self._context_target(ctx),
            "reason": "Contextual instruction compiled into an ordered safe plan.",
        }

