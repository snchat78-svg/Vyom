"""
Project : Vyom AI
Version : 1.0
Module  : Local Semantic Brain

Purpose:
    Dependency-free semantic interpretation for natural Hindi, Roman Hindi,
    Hinglish and English computer instructions.

Design:
    User language -> semantic operation -> generic Action Schema

Rules:
    - Application/file/user names are runtime data, never a vocabulary table.
    - Linguistic action markers are allowed because the brain must identify
      operations such as opening, typing, searching or clicking.
    - Ambiguous intent never executes.
    - The brain never touches the computer and never calls an AI provider.
    - Gemini/local LLM can remain an optional escalation path for goals that
      this deterministic semantic layer cannot safely compile.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from ai_core.context_action_compiler import ContextActionCompiler


class LocalSemanticBrain:
    """Small local semantic planner used before any remote model."""

    _OPEN = (
        "open", "launch", "start", "run", "khol", "kholo", "kholna",
        "kholiye", "kholen", "khol do", "kholdo", "chalu", "chalu karo",
        "chalao", "chala do", "open karo", "open kar", "launch karo",
        "start karo", "खोल", "खोलो", "खोलना", "खोलिए", "खोलिये",
        "खोल दो", "चालू", "चालू करो", "चलाओ", "ओपन", "ओपन करो",
    )
    _CLOSE = (
        "close", "quit", "exit", "stop", "band", "band karo",
        "band kar", "band kar do", "rok", "rok do", "close karo",
        "close kar", "close kar do", "बंद", "बंद करो", "बंद कर",
        "बंद कर दो", "बन्द", "रोक", "रोक दो", "क्लोज", "क्लोज करो",
    )
    _SEARCH = (
        "search", "find", "look for", "look up", "search for",
        "sarch", "serch", "surch", "seach", "dhundo", "dhoondo",
        "khojo", "खोज", "खोजो", "ढूंढ", "ढूंढो", "ढूंढना",
    )
    _TYPE = (
        "type", "write", "enter", "paste", "likh", "likho", "likhen",
        "likhna", "taip", "type karo", "write karo", "paste karo",
        "टाइप", "टाइप करो", "लिख", "लिखो", "लिखें", "लिखना",
        "डालो", "डालें", "डाल",
    )
    _CLICK = (
        "click", "click karo", "klik", "clik", "क्लिक", "क्लिक करो",
    )
    _INVOKE = (
        "invoke", "activate", "press", "select", "choose", "choose karo",
        "daba", "dabao", "दबाओ", "दबाएँ", "दबाएं", "चुनो", "चुनिए",
        "select karo",
    )
    _FOCUS = (
        "focus", "focus karo", "फोकस", "फोकस करो",
    )
    _SCROLL = (
        "scroll", "scrol", "स्क्रोल", "स्क्रॉल",
    )
    _SHORTCUTS = {
        "save": ("ctrl", "s"),
        "save karo": ("ctrl", "s"),
        "refresh": ("ctrl", "r"),
        "refresh karo": ("ctrl", "r"),
        "back": ("alt", "left"),
        "go back": ("alt", "left"),
        "piche": ("alt", "left"),
        "पीछे": ("alt", "left"),
        "forward": ("alt", "right"),
        "go forward": ("alt", "right"),
        "aage": ("alt", "right"),
        "आगे": ("alt", "right"),
        "copy": ("ctrl", "c"),
        "copy karo": ("ctrl", "c"),
        "paste": ("ctrl", "v"),
        "paste karo": ("ctrl", "v"),
        "cut": ("ctrl", "x"),
        "cut karo": ("ctrl", "x"),
        "undo": ("ctrl", "z"),
        "undo karo": ("ctrl", "z"),
        "redo": ("ctrl", "y"),
        "redo karo": ("ctrl", "y"),
        "select all": ("ctrl", "a"),
        "all select": ("ctrl", "a"),
    }

    _QUESTION_WORDS = {
        "what", "who", "why", "when", "where", "how", "which",
        "kya", "kaun", "kyu", "kyun", "kab", "kahan", "kaise",
        "kitna", "kitni", "kitne", "kitney",
    }

    _POLITE = (
        "please", "pls", "mujhe", "mujhko", "mere liye", "zara", "jara",
        "kripya", "कृपया", "मुझे", "मेरे लिए", "जरा", "ज़रा",
    )

    _REFERENCE_PREFIXES = (
        "isme", "isamen", "isame", "ismein", "is mein", "is me",
        "usme", "usamen", "usame", "usmein", "us mein", "us me",
        "in it", "in this", "in that", "there", "here",
        "इसमें", "इस में", "उसमें", "उस में", "यहाँ", "वहाँ",
    )

    _CONNECTOR_RE = re.compile(
        r"\s+(?:and|then|after\s+that|aur|phir|fir|uske\s+baad|और|फिर|उसके\s+बाद|और\s+फिर)\s+",
        re.IGNORECASE,
    )

    def __init__(
        self,
        context_action_compiler: Optional[ContextActionCompiler] = None,
    ):
        self.context_action_compiler = (
            context_action_compiler
            if context_action_compiler is not None
            else ContextActionCompiler()
        )
        self.last_result: Optional[Dict[str, Any]] = None

    @staticmethod
    def _normalize(value: Any) -> str:
        return re.sub(r"\s+", " ", str(value or "").strip())

    @classmethod
    def _lower(cls, value: Any) -> str:
        return cls._normalize(value).lower()

    @staticmethod
    def _strip_end(value: str) -> str:
        value = re.sub(
            r"\s+(?:please|pls|please do|kar do|karna hai|karna|karo|kar|do|दे दो|कर दो|करना है|करना|करो)$",
            "",
            value,
            flags=re.IGNORECASE,
        )
        return value.strip(" ,.!?")

    @classmethod
    def _is_question(cls, text: str) -> bool:
        value = cls._lower(text)
        if not value:
            return False
        if "?" in value:
            return True
        tokens = value.replace("-", " ").split()
        return bool(tokens and (
            tokens[0] in cls._QUESTION_WORDS
            or (
                tokens[0] in {"tum", "aap", "you"}
                and any(item in cls._QUESTION_WORDS for item in tokens[1:])
            )
            or (
                len(tokens) > 1
                and tokens[-1] in {"hai", "hain", "is", "are", "was", "were"}
                and any(item in cls._QUESTION_WORDS for item in tokens[:-1])
            )
        ))

    @classmethod
    def _matches_verb(cls, text: str, vocabulary) -> Optional[str]:
        lowered = cls._lower(text)
        for phrase in sorted(vocabulary, key=len, reverse=True):
            if lowered == phrase.lower():
                return phrase
        return None

    @classmethod
    def _strip_reference_prefix(cls, value: str) -> str:
        text = cls._normalize(value)
        lowered = text.lower()
        for prefix in sorted(cls._REFERENCE_PREFIXES, key=len, reverse=True):
            marker = prefix.lower() + " "
            if lowered.startswith(marker):
                return text[len(prefix):].strip()
        return text

    @classmethod
    def _resolve_reference_target(
        cls,
        target: str,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        value = cls._normalize(target)
        lowered = value.lower()
        reference_forms = (
            "it", "this", "that", "this one", "that one",
            "the same", "same one", "wahi", "wohi", "ye", "ye wala",
            "woh", "woh wala", "isko", "usko", "ise", "use",
            "इसे", "इसे वाला", "इसे खोल", "उसे", "उसको", "यह",
            "यह वाला", "वह", "वो", "वो वाला", "वही",
        )
        is_reference = (
            lowered in reference_forms
            or lowered.startswith(("this one ", "that one ", "ye wala ", "woh wala "))
            or lowered.startswith(("वही ", "वो वाला ", "वह वाला ", "यह वाला "))
        )
        if not is_reference:
            return {"resolved": True, "target": value, "reference": None}

        candidates = []
        for key in ("current_target", "current_app", "current_file"):
            item = str(context.get(key) or "").strip()
            if item and item not in candidates:
                candidates.append(item)

        if not candidates:
            ui = context.get("ui")
            focused = (
                ui.get("focused_element")
                if isinstance(ui, dict)
                else context.get("focused_control")
            )
            if isinstance(focused, dict) and focused.get("exists"):
                candidates.append("focused_element")

        if len(candidates) == 1:
            return {
                "resolved": True,
                "target": candidates[0],
                "reference": "current_context",
            }

        return {
            "resolved": False,
            "clarification": (
                "मैंने reference सुना, लेकिन current target स्पष्ट नहीं है। "
                "कृपया बताइए किस item या window की बात कर रहे हैं।"
            ),
        }

    @classmethod
    def _is_file_target(cls, target: str) -> bool:
        value = cls._lower(target)
        extensions = (
            ".txt", ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".csv",
            ".ppt", ".pptx", ".jpg", ".jpeg", ".png", ".gif", ".bmp",
            ".mp3", ".wav", ".mp4", ".avi", ".mkv", ".zip", ".rar",
            ".7z", ".py", ".dart", ".json", ".xml", ".html", ".htm",
        )
        return value.endswith(extensions) or bool(
            re.match(r"^[a-zA-Z]:[\\/]", value)
        ) or "/" in value or "\\\\" in value

    @classmethod
    def _browser_context(cls, context: Dict[str, Any]) -> bool:
        window = context.get("current_window")
        if not isinstance(window, dict):
            ui = context.get("ui")
            window = ui.get("active_window") if isinstance(ui, dict) else {}

        if not isinstance(window, dict):
            window = {}

        class_name = cls._lower(window.get("class_name"))
        title = cls._lower(window.get("title"))

        # Structural UI fingerprints, not application aliases. This is used
        # only to decide whether a generic address-bar search workflow is safe.
        browser_classes = (
            "chrome_widgetwin", "mozillawindowclass",
            "applicationframewindow",
        )
        if any(marker in class_name for marker in browser_classes):
            return True

        return "browser" in title

    @classmethod
    def _context_has_focus(cls, context: Dict[str, Any]) -> bool:
        focused = context.get("focused_control")
        if not isinstance(focused, dict):
            ui = context.get("ui")
            focused = ui.get("focused_element") if isinstance(ui, dict) else None
        return bool(isinstance(focused, dict) and focused.get("exists", False))

    @classmethod
    def _current_target(cls, context: Dict[str, Any]) -> str:
        for key in ("current_target", "current_app", "current_file"):
            value = str(context.get(key) or "").strip()
            if value:
                return value
        if cls._context_has_focus(context):
            return "focused_element"
        return ""

    def _action(
        self,
        action: str,
        target: str = "",
        args: Optional[Dict[str, Any]] = None,
        depends_on: Optional[List[str]] = None,
        description: str = "",
        verification: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        action_dict = {
            "type": "action",
            "id": "",
            "action": action,
            "capability": "windows_ui",
            "target": target,
            "args": dict(args or {}),
            "preconditions": [],
            "postconditions": [],
            "depends_on": list(depends_on or []),
            "description": description or target or action,
        }
        if verification:
            action_dict["metadata"] = {"verification": verification}
        return action_dict

    @staticmethod
    def _set_ids(steps: List[Dict[str, Any]]) -> None:
        previous = None
        for index, step in enumerate(steps, start=1):
            step["step"] = index
            step["id"] = "semantic_%d" % index
            step["depends_on"] = [previous] if previous else []
            previous = step["id"]

    def _open_close(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        value = self._normalize(text)

        action_patterns = [
            ("open", self._OPEN),
            ("close", self._CLOSE),
        ]

        for operation, vocabulary in action_patterns:
            phrases = "|".join(re.escape(item) for item in sorted(vocabulary, key=len, reverse=True))
            before = re.match(
                rf"^(?:please\s+|mujhe\s+|mere\s+liye\s+)?(?:{phrases})\s+(.+)$",
                value,
                re.IGNORECASE,
            )
            after = re.match(
                rf"^(?:please\s+|mujhe\s+|mere\s+liye\s+)?(.+?)\s+(?:{phrases})(?:\s+.*)?$",
                value,
                re.IGNORECASE,
            )

            match = before or after
            if not match:
                continue

            groups = match.groups()
            target = groups[0] if groups else ""
            target = self._strip_end(self._strip_reference_prefix(target))
            target = re.sub(r"^(?:the|a|an)\s+", "", target, flags=re.IGNORECASE).strip()

            reference = self._resolve_reference_target(target, context or {})
            if not reference.get("resolved"):
                return {
                    "operation": "clarification",
                    "message": reference.get(
                        "clarification",
                        "Current target is ambiguous.",
                    ),
                    "confidence": 0.40,
                }

            target = str(reference.get("target") or "").strip()
            if not target:
                continue

            return {
                "operation": "open_application" if operation == "open" and not self._is_file_target(target) else (
                    "open_file" if operation == "open" else "close_application"
                ),
                "target": target,
                "confidence": 0.94,
                "interpretation": {
                    "operation": operation,
                    "target_role": "file" if self._is_file_target(target) else "application",
                    "reference": reference.get("reference"),
                },
            }

        return None

    def _search(self, text: str, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        value = self._normalize(text)

        phrases = "|".join(re.escape(item) for item in sorted(self._SEARCH, key=len, reverse=True))
        leading = re.match(
            rf"^(?:please\s+)?(?:{phrases})\s+(?:for\s+|ko\s+|को\s+)?(.+)$",
            value,
            re.IGNORECASE,
        )
        trailing = re.match(
            rf"^(?:{re.escape(' '.join(self._REFERENCE_PREFIXES))})\s+(.+?)\s+(?:{phrases})(?:\s+(?:karo|kar|करो|कर))?$",
            value,
            re.IGNORECASE,
        )

        candidate = ""
        if leading:
            candidate = leading.group(1)
        elif trailing:
            candidate = trailing.group(1)

        if not candidate:
            # Flexible trailing verb pattern including ordinary user phrasing:
            # "youtube search karo", "report dhundo", "isme youtube sarch karo".
            generic = re.search(
                rf"(.+?)\s+(?:{phrases})(?:\s+(?:karo|kar|karo|करो|कर))?\s*$",
                value,
                flags=re.IGNORECASE,
            )
            if generic:
                candidate = generic.group(1)
                candidate = self._strip_reference_prefix(candidate)

        candidate = self._strip_end(candidate)
        candidate = self._strip_reference_prefix(candidate)
        candidate = re.sub(
            r"^(?:please\s+|mujhe\s+|mere\s+liye\s+|for\s+|ko\s+|के\s+)",
            "",
            candidate,
            flags=re.IGNORECASE,
        ).strip(" ,.!?")

        if not candidate:
            return None

        if not self._browser_context(context):
            # Searching in a non-browser UI is still possible through the
            # semantic UI compiler, but an address-bar workflow would be an
            # unsafe guess. Ask the existing UI layer to ground a search field.
            return {
                "operation": "ui_search",
                "query": candidate,
                "confidence": 0.78,
                "browser": False,
            }

        steps = [
            self._action(
                "hotkey",
                target="ctrl+l",
                args={"keys": ["ctrl", "l"]},
                description="Focus the current browser navigation/search surface.",
            ),
            self._action(
                "type_text",
                target=candidate,
                args={"text": candidate},
                description="Enter the user's search query without rewriting it.",
            ),
            self._action(
                "keypress",
                target="enter",
                args={"key": "enter"},
                description="Submit the current search/navigation query.",
            ),
        ]
        # Keyboard dispatch is verified by the input controller. Type text
        # additionally receives the normal focused-value verification.
        self._set_ids(steps)
        return {
            "operation": "web_search",
            "query": candidate,
            "confidence": 0.88,
            "steps": steps,
            "browser": True,
        }

    def _generic_from_context_compiler(self, text: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        try:
            compiled = self.context_action_compiler.compile(text, context=context)
        except Exception:
            return []
        if not isinstance(compiled, dict) or not compiled.get("complete"):
            return []
        plan = compiled.get("plan")
        return [dict(item) for item in plan if isinstance(item, dict)]

    def _operation_from_surface(self, text: str) -> Optional[Dict[str, Any]]:
        value = self._normalize(text)
        lower = value.lower()

        if self._matches_verb(value, self._CLICK):
            return {"operation": "click_ui_element", "target": value}
        if self._matches_verb(value, self._FOCUS):
            return {"operation": "focus_window", "target": value}
        if self._matches_verb(value, self._SCROLL):
            return {"operation": "scroll"}
        shortcut = self._SHORTCUTS.get(lower)
        if shortcut:
            target = "+".join(shortcut)
            return {
                "operation": "hotkey",
                "target": target,
                "args": {"keys": list(shortcut)},
            }

        # Hindi/English suffixes can leave a polite helper after the action.
        # Remove only language glue; never rewrite the user target.
        cleaned = self._strip_end(lower)
        shortcut = self._SHORTCUTS.get(cleaned)
        if shortcut:
            target = "+".join(shortcut)
            return {
                "operation": "hotkey",
                "target": target,
                "args": {"keys": list(shortcut)},
            }
        return None

    def reason(
        self,
        goal: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        original = self._normalize(goal)
        ctx = dict(context or {})

        if not original:
            result = {
                "success": False,
                "route": "clarification",
                "message": "Please tell me what you want me to do.",
                "confidence": 0.0,
                "source": "local_semantic_brain",
            }
            self.last_result = result
            return result

        if self._is_question(original):
            result = {
                "success": True,
                "route": "conversation",
                "goal": original,
                "confidence": 0.91,
                "semantic_interpretation": "information_question",
                "plan": [],
                "source": "local_semantic_brain",
            }
            self.last_result = result
            return result

        # Reuse the canonical contextual compiler first. It already knows
        # how to preserve dependency order for supported mixed goals such as
        # "open X and type Y" without losing the second semantic stage.
        whole_plan = self._generic_from_context_compiler(original, ctx)
        if whole_plan:
            self._set_ids(whole_plan)
            has_legacy = any(
                isinstance(step, dict)
                and str(step.get("type") or "").strip().lower() == "execute_existing_intent"
                for step in whole_plan
            )
            result = {
                "success": True,
                "route": "mission" if len(whole_plan) > 1 or has_legacy else "capability",
                "goal": original,
                "confidence": 0.93,
                "semantic_interpretation": [{
                    "text": original,
                    "source": "context_action_compiler",
                    "confidence": 0.93,
                }],
                "plan": whole_plan,
                "source": "local_semantic_brain",
                "needs_confirmation": False,
            }
            self.last_result = result
            return result

        parts = [
            self._normalize(item)
            for item in self._CONNECTOR_RE.split(original)
            if self._normalize(item)
        ] or [original]

        steps: List[Dict[str, Any]] = []
        interpretations = []
        unresolved = []

        for part in parts:
            local_plan = self._generic_from_context_compiler(part, ctx)
            if local_plan:
                steps.extend(local_plan)
                interpretations.append({
                    "text": part,
                    "source": "context_action_compiler",
                    "confidence": 0.93,
                })
                continue

            opened = self._open_close(part, context=ctx)
            if opened:
                if opened.get("operation") == "clarification":
                    unresolved.append(part)
                    interpretations.append({
                        "text": part,
                        "operation": "clarification",
                        "confidence": opened.get("confidence", 0.40),
                    })
                    continue
                steps.append(
                    self._action(
                        opened["operation"],
                        target=opened["target"],
                        description="Resolve the user's requested target at runtime.",
                    )
                )
                interpretations.append({
                    "text": part,
                    **opened["interpretation"],
                    "confidence": opened["confidence"],
                })
                continue

            searched = self._search(part, ctx)
            if searched:
                if searched.get("steps"):
                    steps.extend(searched["steps"])
                else:
                    # Non-browser search remains a UI semantic goal. Let the
                    # UI grounder resolve the actual search control instead
                    # of guessing coordinates or an application-specific API.
                    steps.extend([
                        self._action(
                            "focus_ui_element",
                            target="Search",
                            description="Focus the visible search input/control.",
                        ),
                        self._action(
                            "type_text",
                            target=searched["query"],
                            args={"text": searched["query"]},
                            description="Enter the user's search query.",
                        ),
                        self._action(
                            "keypress",
                            target="enter",
                            args={"key": "enter"},
                            description="Submit the search query.",
                        ),
                    ])
                interpretations.append({
                    "text": part,
                    "operation": searched["operation"],
                    "query": searched["query"],
                    "confidence": searched["confidence"],
                })
                continue

            generic = self._operation_from_surface(part)
            if generic:
                operation = generic["operation"]
                target = generic.get("target") or ""
                args = generic.get("args") or {}
                steps.append(
                    self._action(
                        operation,
                        target=target if operation != "hotkey" else target,
                        args=args,
                        description="Interpret the requested generic computer operation.",
                    )
                )
                interpretations.append({
                    "text": part,
                    "operation": operation,
                    "confidence": 0.83,
                })
                continue

            # Last chance: a natural generic action compiler may understand a
            # paraphrase that does not use one of the compact surface forms.
            local_plan = self._generic_from_context_compiler(original, ctx)
            if local_plan:
                steps.extend(local_plan)
                interpretations.append({
                    "text": part,
                    "source": "context_action_compiler",
                    "confidence": 0.88,
                })
                continue

            unresolved.append(part)

        if unresolved:
            current = self._current_target(ctx)
            selection_ambiguity = any(
                "number" in self._lower(item)
                or "option" in self._lower(item)
                or "instance" in self._lower(item)
                for item in unresolved
            )

            if selection_ambiguity:
                message = (
                    "मैंने instruction समझने की कोशिश की, लेकिन selection का संदर्भ "
                    "स्पष्ट नहीं है। कृपया बताइए किस item/instance को चुनना है।"
                )
                route = "clarification"
            elif current:
                message = (
                    "मैं active context पहचान रहा हूँ, लेकिन इस instruction को "
                    "safely execute करने के लिए semantic interpretation और चाहिए।"
                )
                route = "escalate"
            else:
                message = (
                    "यह instruction local semantic rules से पूरी तरह resolve नहीं हुई। "
                    "इसे आगे semantic reasoning के लिए भेजा जा सकता है।"
                )
                route = "escalate"

            result = {
                "success": True,
                "route": route,
                "goal": original,
                "confidence": 0.34 if route == "clarification" else 0.46,
                "semantic_interpretation": interpretations,
                "unresolved_parts": unresolved,
                "message": message,
                "plan": [],
                "source": "local_semantic_brain",
                "terminal": route == "clarification",
                "needs_model": route == "escalate",
            }
            self.last_result = result
            return result

        self._set_ids(steps)
        has_legacy = any(
            isinstance(step, dict)
            and str(step.get("type") or "").strip().lower() == "execute_existing_intent"
            for step in steps
        )
        route = "mission" if len(steps) > 1 or has_legacy else "capability"

        result = {
            "success": True,
            "route": route,
            "goal": original,
            "confidence": round(
                min(
                    [float(item.get("confidence", 0.80)) for item in interpretations]
                    or [0.80]
                ),
                4,
            ),
            "semantic_interpretation": interpretations,
            "plan": steps,
            "source": "local_semantic_brain",
            "needs_confirmation": False,
        }
        self.last_result = result
        return result
