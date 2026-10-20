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
from decimal import Decimal, InvalidOperation
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional

from ai_core.context_action_compiler import ContextActionCompiler
from ai_core.transcript_recovery import TranscriptRecovery
from ai_core.meaning_intent_engine import MeaningIntentEngine


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
    _DOUBLE_CLICK = (
        "double click", "double-click", "doubleclick", "dubble click",
        "dobara click", "दो बार क्लिक", "डबल क्लिक",
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
    _KEYWORDS = {
        "enter", "return", "tab", "escape", "esc", "space", "backspace",
        "delete", "insert", "home", "end", "left", "right", "up", "down",
        "pageup", "pagedown", "f1", "f2", "f3", "f4", "f5", "f6", "f7",
        "f8", "f9", "f10", "f11", "f12",
        "एंटर", "टैब", "एस्केप", "स्पेस", "बैकस्पेस", "डिलीट",
        "लेफ्ट", "राइट", "अप", "डाउन",
    }

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
        "what", "who", "why", "when", "where", "how", "which", "whose", "whom",
        "kya", "kaun", "kyu", "kyun", "kab", "kahan", "kaise",
        "kitna", "kitni", "kitne", "kitney", "kitana", "kitane", "kitani",
        "kitanaa", "kitanee", "kitnay", "kis", "kise", "kiska", "kiski", "kiske",
        "kisne", "kisko",
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
        if re.search(
            r"^(?:please\s+)?(?:tell me(?: about)?|explain|define|describe|"
            r"give me (?:some )?information about)\b|"
            r"\b(?:batao|bataiye|samjhao|samjhaiye|explain|define|describe)\s*(?:karo|kar do)?$|"
            r"(?:बताओ|बताइए|समझाओ|समझाइए|समझा दो|के बारे में बताओ|के बारे में बताइए)$",
            value,
            flags=re.IGNORECASE,
        ):
            return True
        # STT can omit punctuation and put the Hindi interrogative mid-sentence.
        tokens = value.replace("-", " ").split()
        return any(token in cls._QUESTION_WORDS for token in tokens)

    @classmethod
    def _fuzzy_phrase(cls, text: str, vocabulary, threshold: float = 0.78) -> Optional[str]:
        value = cls._lower(text)
        if not value:
            return None

        exact = cls._matches_verb(value, vocabulary)
        if exact:
            return exact

        best = None
        best_score = 0.0
        for phrase in vocabulary:
            score = SequenceMatcher(
                None,
                value.replace(" ", ""),
                str(phrase).lower().replace(" ", ""),
            ).ratio()
            if score > best_score:
                best_score = score
                best = phrase
        return best if best_score >= threshold else None

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

    @classmethod
    def _selection_index(cls, text: str) -> Optional[int]:
        value = cls._lower(text)
        word_numbers = {
            "one": 1, "first": 1, "two": 2, "second": 2,
            "three": 3, "third": 3, "four": 4, "fourth": 4,
            "five": 5, "fifth": 5,
            "ek": 1, "pehla": 1, "पहला": 1,
            "do": 2, "dusra": 2, "दूसरा": 2,
            "teen": 3, "teesra": 3, "तीसरा": 3,
            "char": 4, "chautha": 4, "चौथा": 4,
            "paanch": 5, "pachva": 5, "पाँचवाँ": 5,
        }
        digit = re.search(
            r"(?:number|no\.?|option|item|choice|विकल्प|नंबर|आइटम)\s*([0-9]+)",
            value,
            flags=re.IGNORECASE,
        )
        if digit:
            return int(digit.group(1))
        for marker, number in word_numbers.items():
            if re.search(
                rf"\b(?:number|option|item|choice)\s+{re.escape(marker)}\b",
                value,
                flags=re.IGNORECASE,
            ):
                return number
            if value.strip() == marker:
                return number
        return None

    @classmethod
    def _selection_from_context(
        cls,
        text: str,
        context: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        if not bool(context.get("pending_selection", False)):
            return None

        options = context.get("selection_options")
        if not isinstance(options, list) or not options:
            return {
                "operation": "clarification",
                "message": (
                    "मुझे पिछली selection याद है, लेकिन उसके options उपलब्ध नहीं हैं। "
                    "कृपया item का नाम बोलिए।"
                ),
                "confidence": 0.40,
            }

        number = cls._selection_index(text)
        if number is None:
            return None

        index = number - 1
        if index < 0 or index >= len(options):
            return {
                "operation": "clarification",
                "message": "यह selection number उपलब्ध नहीं है। कृपया मिले हुए options में से सही number बताइए।",
                "confidence": 0.45,
            }

        selected = options[index]
        if isinstance(selected, dict):
            target = str(
                selected.get("path")
                or selected.get("name")
                or selected.get("display_name")
                or ""
            ).strip()
        else:
            target = str(selected or "").strip()

        if not target:
            return {
                "operation": "clarification",
                "message": "मैं selected item की पहचान नहीं कर पाया। कृपया उसका नाम बताइए।",
                "confidence": 0.42,
            }

        return {
            "operation": "open_file" if cls._is_file_target(target) else "open_application",
            "target": target,
            "confidence": 0.96,
            "reference": "pending_selection",
        }

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

    @classmethod
    def _normalize_ui_control_target(cls, target: str) -> str:
        substitutions = {
            "pavar": "power",
            "batan": "button",
            "aikon": "icon",
            "feld": "field",
            "dabba": "box",
        }
        value = cls._normalize(target)
        return re.sub(
            r"\b[A-Za-z]+\b",
            lambda match: substitutions.get(match.group(0).lower(), match.group(0)),
            value,
        )

    @classmethod
    def _is_ui_control_target(cls, target: str) -> bool:
        tokens = set(re.findall(r"\w+", cls._lower(target), flags=re.UNICODE))
        return bool(tokens & {
            "button", "बटन", "box", "बॉक्स", "field", "textbox",
            "tab", "टैब", "menu", "मेन्यू", "link", "लिंक",
            "icon", "आइकन", "checkbox", "dropdown", "toggle", "slider",
        }) or "text box" in cls._lower(target) or "check box" in cls._lower(target)

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

            # A target ending in a generic UI-control noun is not an app name.
            # Route it through UI Automation so open/show requests can ground
            # and invoke the actual visible element rather than launch a fake app.
            control_target = self._normalize_ui_control_target(target)
            if operation == "open" and self._is_ui_control_target(control_target):
                return {
                    "operation": "invoke_ui_element",
                    "target": control_target,
                    "confidence": 0.80,
                    "interpretation": {
                        "operation": "invoke_ui_element",
                        "target_role": "ui_control",
                        "reference": reference.get("reference"),
                    },
                }

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
        leading = re.match(rf"^(?:please\s+)?(?:{phrases})\s+(?:for\s+|ko\s+|को\s+)?(.+)$", value, re.IGNORECASE)
        trailing = re.match(
            rf"^(?:{re.escape(' '.join(self._REFERENCE_PREFIXES))})\s+(.+?)\s+(?:{phrases})(?:\s+(?:karo|kar|करो|कर))?$",
            value, re.IGNORECASE,
        )
        candidate = ""
        if leading:
            candidate = leading.group(1)
        elif trailing:
            candidate = trailing.group(1)
        if not candidate:
            generic = re.search(
                rf"(.+?)\s+(?:{phrases})(?:\s+(?:karo|kar|करो|कर))?\s*$",
                value, flags=re.IGNORECASE,
            )
            if generic:
                candidate = self._strip_reference_prefix(generic.group(1))
        candidate = self._strip_end(candidate)
        candidate = self._strip_reference_prefix(candidate)
        candidate = re.sub(
            r"^(?:please\s+|mujhe\s+|mere\s+liye\s+|for\s+|ko\s+|के\s+)",
            "", candidate, flags=re.IGNORECASE,
        ).strip(" ,.!?")
        # Treat an explicit multi-word phrase before "me/men" as a runtime
        # app qualifier. No application-name alias table is used.
        explicit_application = ""
        app_match = re.match(r"^(.+?)\s+(?:men|mein|me|में)\s+(.+)$", candidate, flags=re.IGNORECASE)
        if app_match:
            possible_app = self._normalize(app_match.group(1)).strip(" ,.!?")
            possible_query = self._normalize(app_match.group(2)).strip(" ,.!?")
            context_app = str(context.get("current_app") or context.get("current_target") or "").strip()
            is_context_target = bool(context_app and score_candidate(possible_app, context_app) >= 0.82)
            if possible_app and possible_query and (len(possible_app.split()) >= 2 or is_context_target):
                explicit_application = possible_app
                candidate = possible_query
        if not candidate:
            return None
        if not self._browser_context(context) and not explicit_application:
            return {"operation": "ui_search", "query": candidate, "confidence": 0.78, "browser": False}
        steps = []
        if explicit_application:
            steps.extend([
                self._action("open_application", target=explicit_application, description="Open or reuse the user-selected application for the search."),
                self._action("wait", target="", args={"seconds": 0.8}, description="Wait for the selected application's window to become ready."),
            ])
        steps.extend([
            self._action("hotkey", target="ctrl+l", args={"keys": ["ctrl", "l"]}, description="Focus the current browser navigation/search surface."),
            self._action("type_text", target=candidate, args={"text": candidate}, description="Enter the user's search query without rewriting it."),
            self._action("keypress", target="enter", args={"key": "enter"}, description="Submit the current search/navigation query."),
        ])
        self._set_ids(steps)
        return {
            "operation": "web_search", "query": candidate, "confidence": 0.88,
            "steps": steps, "browser": True, "application_target": explicit_application or None,
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

    @classmethod
    def _extract_payload(cls, text: str, vocabulary) -> str:
        value = cls._normalize(text)
        phrases = "|".join(
            re.escape(item)
            for item in sorted(vocabulary, key=len, reverse=True)
        )
        match = re.match(
            rf"^(?:please\s+|mujhe\s+|mere\s+liye\s+)?(?:{phrases})\s+(.+?)\s*$",
            value,
            re.IGNORECASE,
        )
        if match:
            return cls._strip_end(match.group(1)).strip(" ,.!?")
        match = re.match(
            rf"^(.+?)\s+(?:{phrases})(?:\s+.*)?$",
            value,
            re.IGNORECASE,
        )
        if match:
            return cls._strip_end(match.group(1)).strip(" ,.!?")
        return ""

    @classmethod
    def _has_action_shape(cls, text: str) -> bool:
        """Recognize generic imperative morphology, not application names."""
        value = cls._lower(text)
        verbs = (
            cls._OPEN + cls._CLOSE + cls._TYPE + cls._CLICK
            + cls._DOUBLE_CLICK + cls._INVOKE + cls._FOCUS
            + cls._SCROLL + cls._SEARCH
        )
        for phrase in sorted(set(verbs), key=len, reverse=True):
            if value == phrase or value.startswith(phrase + " "):
                return True

        command_suffixes = (
            "khol do", "kholdo", "kholo", "kholna", "kholiye", "kholen",
            "band karo", "band kar do", "likho", "likhen", "likh do",
            "type karo", "click karo", "select karo", "dabao", "daba do",
            "खोलो", "खोल दो", "लिखो", "लिखें", "दबाओ", "क्लिक करो",
            "चुनो", "खोजो", "ढूंढो",
        )
        return any(value.endswith(" " + suffix) for suffix in command_suffixes)

    def _semantic_surface_action(
        self,
        text: str,
        context: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        value = self._normalize(text)
        lower = value.lower()

        payload = self._extract_payload(value, self._TYPE)
        if payload:
            return {
                "operation": "type_text",
                "target": "focused_element",
                "args": {"text": self._strip_reference_prefix(payload)},
                "confidence": 0.90,
            }

        payload = self._extract_payload(value, self._DOUBLE_CLICK)
        if payload:
            payload = re.sub(
                r"^(?:on|the|button|link|par)\s+",
                "",
                payload,
                flags=re.IGNORECASE,
            ).strip()
            return {
                "operation": "double_click",
                "target": payload,
                "confidence": 0.84,
            }

        payload = self._extract_payload(value, self._CLICK)
        if payload:
            payload = re.sub(
                r"^(?:on|the|button|link|par)\s+",
                "",
                payload,
                flags=re.IGNORECASE,
            ).strip()
            return {
                "operation": "click_ui_element",
                "target": payload,
                "confidence": 0.84,
            }

        payload = self._extract_payload(value, self._INVOKE)
        if payload:
            key = payload.lower().strip()
            if key in {str(item).lower() for item in self._KEYWORDS}:
                return {
                    "operation": "keypress",
                    "target": payload,
                    "args": {"key": payload},
                    "confidence": 0.88,
                }
            return {
                "operation": (
                    "select_ui_element"
                    if lower.startswith(("select ", "choose ", "chun", "चुन"))
                    else "invoke_ui_element"
                ),
                "target": payload,
                "confidence": 0.83,
            }

        payload = self._extract_payload(value, self._FOCUS)
        if payload:
            return {
                "operation": "focus_ui_element",
                "target": payload,
                "confidence": 0.84,
            }

        payload = self._extract_payload(value, self._INVOKE)
        if payload:
            return {
                "operation": (
                    "select_ui_element"
                    if lower.startswith(("select ", "choose ", "chun", "चुन"))
                    else "invoke_ui_element"
                ),
                "target": payload,
                "confidence": 0.83,
            }

        if lower in {
            "maximize", "maximize karo", "window maximize", "window maximize karo",
            "window ko maximize karo", "बड़ा करो", "अधिकतम करो",
        }:
            return {
                "operation": "hotkey",
                "target": "win+up",
                "args": {"keys": ["win", "up"]},
                "confidence": 0.87,
            }

        if lower in {
            "minimize", "minimize karo", "window minimize",
            "window ko minimize karo", "छोटा करो", "न्यूनतम करो",
        }:
            return {
                "operation": "hotkey",
                "target": "win+down",
                "args": {"keys": ["win", "down"]},
                "confidence": 0.87,
            }

        if lower in {
            "switch window", "switch windows", "next window",
            "window change", "window badlo", "खिड़की बदलो", "विंडो बदलो",
        }:
            return {
                "operation": "hotkey",
                "target": "alt+tab",
                "args": {"keys": ["alt", "tab"]},
                "confidence": 0.84,
            }

        if lower in {
            "screenshot", "take screenshot", "screen shot",
            "screenshot lo", "screen shot lo", "स्क्रीनशॉट", "स्क्रीन शॉट लो",
        }:
            return {
                "operation": "screenshot",
                "target": "",
                "args": {},
                "confidence": 0.90,
            }

        scroll_target = self._strip_end(lower)
        if scroll_target in {
            "scroll down", "scroll neeche", "neeche scroll",
            "नीचे स्क्रॉल", "स्क्रॉल नीचे", "नीचे स्क्रोल",
        }:
            return {
                "operation": "scroll",
                "target": "down",
                "args": {"amount": 3},
                "confidence": 0.86,
            }
        if scroll_target in {
            "scroll up", "scroll upar", "upar scroll",
            "ऊपर स्क्रॉल", "स्क्रॉल ऊपर", "ऊपर स्क्रोल",
        }:
            return {
                "operation": "scroll",
                "target": "up",
                "args": {"amount": -3},
                "confidence": 0.86,
            }

        return None

    def _operation_from_surface(self, text: str) -> Optional[Dict[str, Any]]:
        value = self._normalize(text)
        lower = value.lower()

        if self._fuzzy_phrase(value, self._CLICK):
            return {"operation": "click_ui_element", "target": value}
        if self._fuzzy_phrase(value, self._FOCUS):
            return {"operation": "focus_window", "target": value}
        if self._fuzzy_phrase(value, self._SCROLL):
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

    def _compound_arithmetic_plan(
        self,
        text: str,
        context: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Compile an application-first arithmetic workflow with a verifiable result."""
        value = self._normalize(text)
        opened = self._open_close(value, context=context)
        if not isinstance(opened, dict) or opened.get("operation") != "open_application":
            return None
        target = self._normalize(opened.get("target"))
        if not target:
            return None
        # Application names can contain digits; remove the resolved target first.
        operation_text = re.sub(re.escape(target), " ", value, count=1, flags=re.IGNORECASE)
        numbers = re.findall(r"(?<![\w.])\d+(?:\.\d+)?(?![\w.])", operation_text)
        if len(numbers) < 2:
            return None
        if re.search(r"(?:[+*/-]|\b(?:plus|minus|times|divided|add|subtract|multiply|divide))\s*$", operation_text, flags=re.IGNORECASE):
            return None
        operation_patterns = (
            (r"\b(?:subtract|minus|ghatao|ghata|kam karo)\b|घटाओ|घटाना", "-"),
            (r"\b(?:multiply|multiplied|times|guna|gunaa)\b|गुणा", "*"),
            (r"\b(?:divide|divided|bhag|bhaag)\b|भाग", "/"),
            (r"\b(?:add|addition|plus|sum|jodo|joro|jod|jama)\b|जोड़|जोड़|जमा", "+"),
        )
        operator = None
        for pattern, symbol in operation_patterns:
            if re.search(pattern, operation_text, flags=re.IGNORECASE):
                operator = symbol
                break
        if operator is None and re.search(r"\d\s*[+*/-]\s*\d", operation_text):
            symbol_match = re.search(r"([+*/-])", operation_text)
            operator = symbol_match.group(1) if symbol_match else None
        if operator is None:
            return None
        expression = operator.join(numbers)
        expected_result = None
        try:
            calculated = Decimal(numbers[0])
            for operand in numbers[1:]:
                number = Decimal(operand)
                if operator == "+":
                    calculated += number
                elif operator == "-":
                    calculated -= number
                elif operator == "*":
                    calculated *= number
                elif operator == "/":
                    if number == 0:
                        calculated = None
                        break
                    calculated /= number
            if calculated is not None and calculated.is_finite():
                expected_result = format(calculated.normalize(), "f")
        except (InvalidOperation, ZeroDivisionError, ValueError):
            expected_result = None
        steps = [
            self._action("open_application", target=target, description="Open or reuse the runtime-resolved application."),
            self._action("wait", target="", args={"seconds": 0.8}, description="Allow the requested application to finish loading."),
            self._action("type_text", target="focused_element", args={"text": expression}, description="Enter the user-requested arithmetic expression into the foreground app."),
            self._action(
                "keypress",
                target="enter",
                args={"key": "enter"},
                description="Submit the arithmetic expression and verify the displayed result.",
                verification={
                    "mode": "all",
                    "checks": [{"kind": "contains_visible_text", "value": expected_result}],
                } if expected_result is not None else None,
            ),
        ]
        self._set_ids(steps)
        return {
            "success": True,
            "route": "mission",
            "goal": value,
            "confidence": 0.90,
            "semantic_interpretation": [{
                "text": value,
                "operation": "compound_arithmetic_workflow",
                "expression": expression,
                "expected_result": expected_result,
                "source": "local_semantic_brain",
            }],
            "plan": steps,
            "source": "local_semantic_brain",
            "needs_confirmation": False,
        }

    def _reason_existing_pipeline(
        self,
        goal: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        raw_original = self._normalize(goal)
        ctx = dict(context or {})
        operation_phrases = {
            "open": self._OPEN,
            "close": self._CLOSE,
            "search": self._SEARCH,
            "type": self._TYPE,
            "click": self._CLICK,
            "double_click": self._DOUBLE_CLICK,
            "invoke": self._INVOKE,
            "focus": self._FOCUS,
            "scroll": self._SCROLL,
            "shortcut": tuple(self._SHORTCUTS),
        }
        transcript_recovery = TranscriptRecovery().recover(
            raw_original, operation_phrases, context=ctx
        )
        original = transcript_recovery["text"]

        if not original:
            result = {
                "success": False,
                "route": "clarification",
                "message": "Please tell me what you want me to do.",
                "confidence": 0.0,
                "source": "local_semantic_brain",
            }
            result["raw_transcript"] = raw_original
            result["transcript_recovery"] = transcript_recovery
            result["raw_transcript"] = raw_original
            result["transcript_recovery"] = transcript_recovery
            self.last_result = result
            return result

        arithmetic_plan = self._compound_arithmetic_plan(original, ctx)
        if arithmetic_plan:
            self.last_result = arithmetic_plan
            return arithmetic_plan

        # Compile the full goal before deciding that it is a conversation.
        # Interrogative words may be user data, e.g. "type what I say".
        whole_plan = self._generic_from_context_compiler(original, ctx)
        clauses = [
            self._normalize(item)
            for item in self._CONNECTOR_RE.split(original)
            if self._normalize(item)
        ] or [original]
        action_shaped_clause = any(self._has_action_shape(item) for item in clauses)
        explicit_info_request = bool(re.match(
            r"^(?:please\s+)?(?:tell me|explain|define|describe|give me (?:some )?information about)\b",
            original,
            flags=re.IGNORECASE,
        ))

        if self._is_question(original) and (
            explicit_info_request
            or (not whole_plan and not action_shaped_clause)
        ):
            result = {
                "success": True,
                "route": "conversation",
                "goal": original,
                "confidence": 0.91,
                "semantic_interpretation": "information_question",
                "plan": [],
                "source": "local_semantic_brain",
            }
            result["raw_transcript"] = raw_original
            result["transcript_recovery"] = transcript_recovery
            result["raw_transcript"] = raw_original
            result["transcript_recovery"] = transcript_recovery
            self.last_result = result
            return result

        # Single natural commands are interpreted by the semantic brain
        # itself before the legacy contextual compiler. This is important for
        # pronouns/references: "ye wala kholo" must become a generic
        # open_application action, not a legacy mission step.
        parts = [
            self._normalize(item)
            for item in self._CONNECTOR_RE.split(original)
            if self._normalize(item)
        ] or [original]

        if len(parts) == 1:
            selected = self._selection_from_context(parts[0], ctx)
            if selected and selected.get("operation") != "clarification":
                step = self._action(
                    selected["operation"],
                    target=selected["target"],
                    description="Resolve the user's selection from the previous runtime result.",
                )
                self._set_ids([step])
                result = {
                    "success": True,
                    "route": "capability",
                    "goal": original,
                    "confidence": selected.get("confidence", 0.96),
                    "semantic_interpretation": [{
                        "operation": selected["operation"],
                        "reference": selected.get("reference"),
                    }],
                    "plan": [step],
                    "source": "local_semantic_brain",
                    "needs_confirmation": False,
                }
                result["raw_transcript"] = raw_original
                result["transcript_recovery"] = transcript_recovery
                self.last_result = result
                return result

            opened = self._open_close(parts[0], context=ctx)
            if opened and opened.get("operation") != "clarification":
                step = self._action(
                    opened["operation"],
                    target=opened["target"],
                    description="Resolve and execute the user's requested target at runtime.",
                )
                self._set_ids([step])
                result = {
                    "success": True,
                    "route": "capability",
                    "goal": original,
                    "confidence": opened.get("confidence", 0.94),
                    "semantic_interpretation": [opened.get("interpretation", {})],
                    "plan": [step],
                    "source": "local_semantic_brain",
                    "needs_confirmation": False,
                }
                result["raw_transcript"] = raw_original
                result["transcript_recovery"] = transcript_recovery
                self.last_result = result
                return result

        if len(parts) == 1:
            # Resolve a clear one-step semantic UI command before the legacy
            # whole-goal compiler. This keeps "search box click karo" on the
            # generic capability route instead of converting it to a mission.
            generic = self._semantic_surface_action(parts[0], ctx)
            if generic:
                step = self._action(
                    generic["operation"],
                    target=generic.get("target") or "",
                    args=generic.get("args") or {},
                    description="Interpret the natural-language computer operation locally.",
                )
                self._set_ids([step])
                result = {
                    "success": True,
                    "route": "capability",
                    "goal": original,
                    "confidence": generic.get("confidence", 0.83),
                    "semantic_interpretation": [{
                        "text": original,
                        "operation": generic["operation"],
                        "confidence": generic.get("confidence", 0.83),
                    }],
                    "plan": [step],
                    "source": "local_semantic_brain",
                    "needs_confirmation": False,
                }
                result["raw_transcript"] = raw_original
                result["transcript_recovery"] = transcript_recovery
                self.last_result = result
                return result

        # Reuse the precompiled canonical plan for mixed/compound goals.
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
            result["raw_transcript"] = raw_original
            result["transcript_recovery"] = transcript_recovery
            result["raw_transcript"] = raw_original
            result["transcript_recovery"] = transcript_recovery
            self.last_result = result
            return result

        steps: List[Dict[str, Any]] = []
        interpretations = []
        unresolved = []

        for part in parts:
            # Prefer clear semantic surface actions before the compatibility
            # compiler; otherwise a simple UI click is incorrectly promoted
            # to a multi-step legacy mission.
            generic = self._semantic_surface_action(part, ctx)
            if generic:
                steps.append(
                    self._action(
                        generic["operation"],
                        target=generic.get("target") or "",
                        args=generic.get("args") or {},
                        description="Interpret the natural-language computer operation locally.",
                    )
                )
                interpretations.append({
                    "text": part,
                    "operation": generic["operation"],
                    "confidence": generic.get("confidence", 0.83),
                })
                continue

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

            generic = self._semantic_surface_action(part, ctx)
            if generic:
                steps.append(
                    self._action(
                        generic["operation"],
                        target=generic.get("target") or "",
                        args=generic.get("args") or {},
                        description="Interpret the natural-language computer operation locally.",
                    )
                )
                interpretations.append({
                    "text": part,
                    "operation": generic["operation"],
                    "confidence": generic.get("confidence", 0.83),
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
            result["raw_transcript"] = raw_original
            result["transcript_recovery"] = transcript_recovery
            result["raw_transcript"] = raw_original
            result["transcript_recovery"] = transcript_recovery
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
        result["raw_transcript"] = raw_original
        result["transcript_recovery"] = transcript_recovery
        result["raw_transcript"] = raw_original
        result["transcript_recovery"] = transcript_recovery
        self.last_result = result
        return result

    def reason(
        self,
        goal: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Run the established planner and gate unresolved actions before dispatch.

        M2 attaches a provider-independent meaning frame and converts low-
        confidence action hypotheses or ambiguous runtime targets into a
        terminal clarification with an empty plan. Safe, resolved actions keep
        the established execution route.
        """
        raw_original = self._normalize(goal)
        ctx = dict(context or {})
        result = self._reason_existing_pipeline(goal, context=ctx)
        if not isinstance(result, dict):
            result = {
                "success": False,
                "route": "clarification",
                "message": "The request could not be interpreted safely.",
                "confidence": 0.0,
                "plan": [],
                "source": "local_semantic_brain",
            }

        operation_phrases = {
            "open": self._OPEN,
            "close": self._CLOSE,
            "search": self._SEARCH,
            "type": self._TYPE,
            "click": self._CLICK,
            "double_click": self._DOUBLE_CLICK,
            "invoke": self._INVOKE,
            "focus": self._FOCUS,
            "scroll": self._SCROLL,
            "shortcut": tuple(self._SHORTCUTS),
        }
        recovery = result.get("transcript_recovery")
        if not isinstance(recovery, dict):
            recovery = TranscriptRecovery().recover(
                raw_original, operation_phrases, context=ctx
            )
        result.setdefault("raw_transcript", raw_original)
        result.setdefault("transcript_recovery", recovery)

        meaning_engine = MeaningIntentEngine()
        meaning = meaning_engine.analyze(
            raw_original, result, context=ctx, recovery=recovery
        )
        if (
            meaning.get("requires_clarification")
            and str(result.get("route") or "").lower() in {"capability", "mission"}
        ):
            ambiguities = recovery.get("ambiguities")
            ambiguities = ambiguities if isinstance(ambiguities, list) else []
            ambiguity = ambiguities[0] if ambiguities and isinstance(ambiguities[0], dict) else {}
            if ambiguity:
                observed = str(ambiguity.get("observed") or "").strip()
                candidates = ambiguity.get("candidates")
                names = [
                    str(item.get("value") or "").strip()
                    for item in (candidates if isinstance(candidates, list) else [])
                    if isinstance(item, dict) and str(item.get("value") or "").strip()
                ][:3]
                operation = str(ambiguity.get("operation") or "open").lower()
                verb = "बंद करना" if operation == "close" else "खोलना"
                choices = " या ".join(names)
                message = (
                    f'मैंने "{observed}" सुना, लेकिन एक से अधिक संभावित target मिले'
                    f'{": " + choices if choices else ""}। कृपया स्पष्ट करें कि किसे {verb} है।'
                )
                reason = "ambiguous_runtime_target"
                interpretation = {
                    "operation": operation,
                    "target": observed,
                    "alternatives": names,
                    "reason": reason,
                }
            else:
                message = (
                    "मैं इस निर्देश का अर्थ लेकर पूरी तरह आश्वस्त नहीं हूँ। "
                    "कृपया action या target स्पष्ट करें; मैं अनुमान से action नहीं चलाऊँगा।"
                )
                reason = "low_confidence_action"
                interpretation = {
                    "operation": "unresolved",
                    "target": "",
                    "alternatives": [],
                    "reason": reason,
                }

            semantic_intent = meaning.get("intent")
            semantic_intent = semantic_intent if isinstance(semantic_intent, dict) else {}
            try:
                safe_confidence = float(semantic_intent.get("confidence", 0.0))
                if not 0.0 <= safe_confidence <= 1.0:
                    safe_confidence = 0.0
            except (TypeError, ValueError, OverflowError):
                safe_confidence = 0.0

            result.update({
                "success": True,
                "route": "clarification",
                "message": message,
                "confidence": min(safe_confidence, 0.45),
                "plan": [],
                "needs_confirmation": True,
                "terminal": True,
                "needs_model": False,
                "semantic_interpretation": [interpretation],
            })
            meaning = meaning_engine.analyze(
                raw_original, result, context=ctx, recovery=recovery
            )

        result["meaning"] = meaning
        self.last_result = result
        return result
