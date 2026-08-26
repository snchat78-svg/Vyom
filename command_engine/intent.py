"""
Project : Vyom AI
Version : 1.1
Module  : Intent Engine

Purpose:
    Convert natural Hindi, English and Hinglish user speech into
    the existing Vyom intent format without executing commands.

Stage 3:
    - Natural Hindi/Hinglish command understanding
    - Contextual selection phrases
    - Existing English command compatibility
    - Conversation intents for simple assistant dialogue

Execution remains in Executor/AutonomousAgent/ToolManager.
"""

import re
from typing import Any, Dict

from command_engine.multilingual_command import MultilingualCommand


class IntentEngine:

    NUMBER_WORDS = {
        "zero": "0", "one": "1", "first": "1",
        "two": "2", "second": "2", "three": "3", "third": "3",
        "four": "4", "fourth": "4", "five": "5", "fifth": "5",
        "six": "6", "sixth": "6", "seven": "7", "seventh": "7",
        "eight": "8", "eighth": "8", "nine": "9", "ninth": "9",
        "ten": "10", "tenth": "10",
        "शून्य": "0", "एक": "1", "पहला": "1", "पहली": "1", "पहला वाला": "1", "पहली वाली": "1", "पहले वाला": "1", "पहले वाली": "1",
        "पहले": "1", "प्रथम": "1", "दो": "2", "दूसरा": "2",
        "दूसरी": "2", "दूसरे": "2", "तीन": "3", "तीसरा": "3",
        "तीसरी": "3", "तीसरे": "3", "चार": "4", "चौथा": "4",
        "चौथी": "4", "चौथे": "4", "पांच": "5", "पाँच": "5",
        "पांचवा": "5", "पाँचवा": "5", "छह": "6", "छः": "6",
        "सात": "7", "आठ": "8", "नौ": "9", "दस": "10",
    }

    CONVERSATION_PHRASES = {
        "hello": "greeting", "hi": "greeting", "hey": "greeting",
        "नमस्ते": "greeting", "नमस्कार": "greeting", "हैलो": "greeting",
        "हेलो": "greeting", "राम राम": "greeting",
        "how are you": "status", "how are u": "status",
        "कैसे हो": "status", "कैसा चल रहा है": "status", "क्या हाल है": "status",
        "what can you do": "capabilities", "what can you do for me": "capabilities",
        "तुम क्या कर सकते हो": "capabilities", "आप क्या कर सकते हैं": "capabilities",
        "तुम मेरे लिए क्या कर सकते हो": "capabilities",
        "thank you": "thanks", "thanks": "thanks", "धन्यवाद": "thanks",
        "शुक्रिया": "thanks", "थैंक यू": "thanks",
        "okay": "acknowledge", "ok": "acknowledge", "ठीक है": "acknowledge",
        "अच्छा": "acknowledge", "ठीक": "acknowledge",
    }

    def __init__(self):
        self.multilingual = MultilingualCommand()

    def _normalize(self, text: Any) -> str:
        value = str(text or "").strip().lower()
        value = re.sub(r"\s+", " ", value)
        return value

    def _detect_selection(self, command: str):
        text = self._normalize(command)
        if text.isdigit():
            return text

        if text in self.NUMBER_WORDS:
            return self.NUMBER_WORDS[text]

        # Common spoken forms: "पहला वाला खोलो", "first one open".
        selection_only = re.sub(
            r"\s+(?:खोलो|खोलना|खोलिए|खोलिये|खोल दो|खोल दें|open|open it|open karo|open kar do)$",
            "",
            text,
            flags=re.IGNORECASE
        ).strip()
        if selection_only in self.NUMBER_WORDS:
            return self.NUMBER_WORDS[selection_only]

        # Natural selection forms used after Vyom presents options.
        # Allow a selection together with a conversational action, e.g.
        # "पहला वाला खोलो" / "first one open it".
        selection_text = re.sub(
            r"(?:\s+(?:खोलो|खोलना|खोलिए|खोलिये|खोल दो|खोल दें|open|open it|open karo|open kar do))$",
            "",
            text,
            flags=re.IGNORECASE
        ).strip()
        if selection_text in self.NUMBER_WORDS:
            return self.NUMBER_WORDS[selection_text]

        patterns = [
            r"^(?:number|option|item|choice|no)\s+(.+)$",
            r"^(?:select|choose|pick)\s+(.+)$",
            r"^(?:the\s+)?(.+?)\s+(?:one|option|item)$",
            r"^(.+?)\s+वाला$",
            r"^(.+?)\s+वाली$",
            r"^(.+?)\s+वाले$",
            r"^(.+?)\s+चुनो$",
            r"^(.+?)\s+चुनिए$",
            r"^(.+?)\s+चुन लो$",
        ]

        for pattern in patterns:
            match = re.match(pattern, text)
            if not match:
                continue
            value = match.group(1).strip()
            if value in self.NUMBER_WORDS:
                return self.NUMBER_WORDS[value]
            if value.isdigit():
                return value

        return None

    def _conversation(self, text: str):
        # Exact/near-exact short phrases only. Normal commands are left
        # for the multilingual command parser.
        if text in self.CONVERSATION_PHRASES:
            return self.CONVERSATION_PHRASES[text]
        return None

    def detect(self, command: Any) -> Dict[str, Any]:
        original = str(command or "").strip()
        text = self._normalize(original)

        if not text:
            return {"intent": "unknown", "target": "", "selection": None}

        selection = self._detect_selection(text)
        if selection is not None:
            return {"intent": "selection", "target": selection, "selection": selection}

        conversation = self._conversation(text)
        if conversation:
            return {
                "intent": "conversation",
                "target": conversation,
                "conversation_type": conversation,
            }

        # Contextual commands that refer to the currently active app/task.
        if text in (
            "close", "close it", "close this", "stop it",
            "बंद करो", "बंद कर दो", "इसे बंद करो", "इसे बंद कर दो",
            "इसे बंद कर", "इसे रोक दो"
        ):
            return {"intent": "close_current", "target": ""}

        # Preserve the old exact English parser first for compatibility.
        if text.startswith("close ") or text in ("exit", "quit", "stop"):
            target = text[6:].strip() if text.startswith("close ") else ""
            return {"intent": "close_app", "target": target}

        if text.startswith("find and open ") or text.startswith("search and open "):
            prefix = "find and open " if text.startswith("find and open ") else "search and open "
            return {"intent": "search_and_open_file", "target": text[len(prefix):].strip()}

        # Use the repository's existing multilingual parser. This keeps
        # application names dynamic and does not create an app list here.
        try:
            converted = self.multilingual.convert(original)
        except Exception:
            converted = {"success": False, "intent": "unknown", "target": ""}

        if converted.get("success"):
            family = converted.get("intent")
            target = str(converted.get("target") or "").strip()

            # Speech often appends polite Hindi/Hinglish auxiliaries such as
            # "दो", "करो", or "कर दो" after the actual target.
            target = re.sub(
                r"\s+(?:कर दो|करदो|करो|कर|करें|करिये|करिए|दो|दे दो|देना)$",
                "",
                target,
                flags=re.IGNORECASE
            ).strip()

            if family == "open":
                return {"intent": "open", "target": target}
            if family == "close":
                return {"intent": "close_app", "target": target}
            if family == "search":
                # Preserve filenames such as report.pdf that the multilingual
                # normalizer may have tokenized at the punctuation.
                match = re.search(
                    r"([^\s]+\.(?:txt|pdf|doc|docx|xls|xlsx|csv|ppt|pptx|jpg|jpeg|png|gif|mp3|mp4|zip|rar|py|json|xml))$",
                    original,
                    flags=re.IGNORECASE
                )
                if match:
                    target = match.group(1)
                target = re.sub(r"^(?:फाइल|फ़ाइल|file)\s+", "", target, flags=re.IGNORECASE).strip()
                return {"intent": "search_file", "target": target}

        # Direct file/path compatibility.
        file_extensions = (
            ".txt", ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".csv",
            ".ppt", ".pptx", ".jpg", ".jpeg", ".png", ".gif", ".mp3",
            ".mp4", ".zip", ".rar", ".py", ".json", ".xml"
        )
        if any(text.endswith(ext) for ext in file_extensions):
            return {"intent": "open_file", "target": text}

        return {"intent": "unknown", "target": original}
