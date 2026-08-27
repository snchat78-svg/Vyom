"""
Project : Vyom AI
Version : 1.2
Module  : Intent Engine

Purpose:
    Understand common natural Hindi, English and Hinglish commands
    while preserving the existing MultilingualCommand parser.

This module only interprets commands. It never executes them.
"""

import re
from typing import Any, Dict

from command_engine.multilingual_command import MultilingualCommand


class IntentEngine:

    NUMBER_WORDS = {
        "zero": "0", "one": "1", "first": "1", "two": "2", "second": "2",
        "three": "3", "third": "3", "four": "4", "fourth": "4", "five": "5",
        "fifth": "5", "six": "6", "sixth": "6", "seven": "7", "seventh": "7",
        "eight": "8", "eighth": "8", "nine": "9", "ninth": "9", "ten": "10",
        "tenth": "10",
        "शून्य": "0", "एक": "1", "पहला": "1", "पहली": "1", "पहले": "1",
        "प्रथम": "1", "दूसरा": "2", "दूसरी": "2", "दूसरे": "2", "तीन": "3",
        "तीसरा": "3", "तीसरी": "3", "तीसरे": "3", "चार": "4", "चौथा": "4",
        "चौथी": "4", "चौथे": "4", "पांच": "5", "पाँच": "5", "पांचवा": "5",
        "पाँचवा": "5", "छह": "6", "छः": "6", "सात": "7", "आठ": "8",
        "नौ": "9", "दस": "10",
    }

    CONVERSATION_PHRASES = {
        "hello": "greeting", "hi": "greeting", "hey": "greeting",
        "नमस्ते": "greeting", "नमस्कार": "greeting", "हैलो": "greeting", "हेलो": "greeting",
        "राम राम": "greeting", "good morning": "greeting", "good evening": "greeting",
        "good afternoon": "greeting", "शुभ प्रभात": "greeting",
        "how are you": "status", "how are u": "status", "how are things": "status",
        "कैसे हो": "status", "कैसा चल रहा है": "status", "क्या हाल है": "status",
        "what can you do": "capabilities", "what can you do for me": "capabilities",
        "तुम क्या कर सकते हो": "capabilities", "आप क्या कर सकते हैं": "capabilities",
        "तुम मेरे लिए क्या कर सकते हो": "capabilities",
        "who are you": "identity", "what are you": "identity", "तुम कौन हो": "identity",
        "आप कौन हैं": "identity", "तुम्हारा नाम क्या है": "identity", "आपका नाम क्या है": "identity",
        "help": "help", "मदद": "help", "मेरी मदद करो": "help", "help me": "help",
        "thank you": "thanks", "thanks": "thanks", "धन्यवाद": "thanks", "शुक्रिया": "thanks", "थैंक यू": "thanks",
        "okay": "acknowledge", "ok": "acknowledge", "ठीक है": "acknowledge", "अच्छा": "acknowledge", "ठीक": "acknowledge",
    }

    def __init__(self):
        self.multilingual = MultilingualCommand()

    def _normalize(self, text: Any) -> str:
        value = str(text or "").strip().lower()
        return re.sub(r"\s+", " ", value)

    def _conversation(self, text: str):
        if text in self.CONVERSATION_PHRASES:
            return self.CONVERSATION_PHRASES[text]

        patterns = [
            (r"^(?:hi|hello|hey)\b.*", "greeting"),
            (r"^(?:good morning|good afternoon|good evening)\b.*", "greeting"),
            (r"^(?:कैसे हो|क्या हाल है|कैसा चल रहा है)\b.*", "status"),
            (r"^(?:तुम|आप)\s+(?:कैसे|क्या हाल).*", "status"),
            (r"^(?:what|tell me)\s+(?:can|could)\s+you\s+do.*", "capabilities"),
            (r"^(?:तुम|आप)\s+क्या\s+कर\s+सकते.*", "capabilities"),
            (r"^(?:who are you|what are you).*", "identity"),
            (r"^(?:तुम कौन हो|आप कौन हैं).*", "identity"),
        ]
        for pattern, kind in patterns:
            if re.match(pattern, text, flags=re.IGNORECASE):
                return kind
        return None

    def _detect_selection(self, command: str):
        text = self._normalize(command)
        if text.isdigit():
            return text
        if text in self.NUMBER_WORDS:
            return self.NUMBER_WORDS[text]

        value = re.sub(
            r"(?:^|\s)(?:number|option|item|choice|no)\s+",
            "",
            text,
            count=1,
            flags=re.IGNORECASE,
        ).strip()
        value = re.sub(
            r"\s+(?:please|pls|open|open it|select|choose|pick|खोलो|खोलना|खोलिए|खोलिये|खोल दो|खोल दें|चुनो|चुनिए|चुन लो|कर दो|करो)$",
            "",
            value,
            flags=re.IGNORECASE,
        ).strip()
        if value in self.NUMBER_WORDS:
            return self.NUMBER_WORDS[value]
        if value in (
            "first one", "first option", "first item",
            "second one", "second option", "second item",
            "third one", "third option", "third item",
            "fourth one", "fourth option", "fourth item",
            "fifth one", "fifth option", "fifth item",
        ):
            return {
                "first one": "1", "first option": "1", "first item": "1",
                "second one": "2", "second option": "2", "second item": "2",
                "third one": "3", "third option": "3", "third item": "3",
                "fourth one": "4", "fourth option": "4", "fourth item": "4",
                "fifth one": "5", "fifth option": "5", "fifth item": "5",
            }[value]

        if value in (
            "पहला वाला", "पहली वाली", "पहले वाला", "पहले वाली",
            "दूसरा वाला", "दूसरी वाली", "दूसरे वाला",
            "तीसरा वाला", "तीसरी वाली", "तीसरे वाला",
            "चौथा वाला", "चौथी वाली", "पांचवां वाला", "पाँचवाँ वाला",
        ):
            return {
                "पहला वाला": "1", "पहली वाली": "1", "पहले वाला": "1", "पहले वाली": "1",
                "दूसरा वाला": "2", "दूसरी वाली": "2", "दूसरे वाला": "2",
                "तीसरा वाला": "3", "तीसरी वाली": "3", "तीसरे वाला": "3",
                "चौथा वाला": "4", "चौथी वाली": "4",
                "पांचवां वाला": "5", "पाँचवाँ वाला": "5",
            }[value]
        if value.isdigit():
            return value

        patterns = [
            r"^(?:the\s+)?(.+?)\s+(?:one|option|item)$",
            r"^(.+?)\s+वाला$", r"^(.+?)\s+वाली$", r"^(.+?)\s+वाले$",
            r"^(.+?)\s+चुनो$", r"^(.+?)\s+चुनिए$", r"^(.+?)\s+चुन लो$",
        ]
        for pattern in patterns:
            match = re.match(pattern, text)
            if match:
                candidate = match.group(1).strip()
                if candidate in self.NUMBER_WORDS:
                    return self.NUMBER_WORDS[candidate]
                if candidate.isdigit():
                    return candidate
        return None

    def _strip_polite_suffix(self, target: str) -> str:
        value = str(target or "").strip()
        value = re.sub(
            r"\s+(?:कर दो|करदो|करो|कर|करें|करिये|करिए|दो|दे दो|देना|please|pls)$",
            "",
            value,
            flags=re.IGNORECASE,
        )
        return value.strip()

    def _natural_family(self, original: str):
        text = self._normalize(original)

        # Open: action may appear before OR after the target.
        open_after = re.match(
            r"^(?:please\s+|मेरे\s+लिए\s+|मुझे\s+|जरा\s+|ज़रा\s+)?(.+?)\s+(?:open|launch|start|run|खोल|खोलो|खोलना|खोलिए|खोलिये|चालू करो|चालू|चलाओ|चला दो|चला|khol|kholo|kholna|chalu|chalu karo|chalao|open karo|launch karo|start karo)(?:\s+.*)?$",
            text,
            flags=re.IGNORECASE,
        )
        if open_after:
            target = self._strip_polite_suffix(open_after.group(1))
            target = re.sub(r"^(?:the|a|an)\s+", "", target, flags=re.IGNORECASE)
            if target:
                return "open", target

        open_before = re.match(
            r"^(?:please\s+)?(?:open|launch|start|run|खोलो?|खोलना|खोलिए|खोलिये|चालू करो|चालू|चलाओ|चला दो|khol|kholo|chalu|chalao|open karo|launch karo|start karo)\s+(.+?)$",
            text,
            flags=re.IGNORECASE,
        )
        if open_before:
            target = self._strip_polite_suffix(open_before.group(1))
            target = re.sub(r"^(?:the|a|an|मेरे लिए|मुझे)\s+", "", target, flags=re.IGNORECASE)
            if target:
                return "open", target

        close_after = re.match(
            r"^(?:please\s+|मेरे\s+लिए\s+|मुझे\s+)?(.+?)\s+(?:close|exit|quit|stop|बंद|बंद करो|बंद कर|बंद कर दो|बन्द|रोक|रोक दो|band|band karo|band kar|band kar do|rok|rok do|close karo|close kar|close kar do)(?:\s+.*)?$",
            text,
            flags=re.IGNORECASE,
        )
        if close_after:
            target = self._strip_polite_suffix(close_after.group(1))
            if target:
                return "close", target

        close_before = re.match(
            r"^(?:please\s+)?(?:close|exit|quit|stop|बंद करो|बंद कर दो|बन्द करो|रोक दो|band karo|band kar do|close karo|close kar do)\s+(.+?)$",
            text,
            flags=re.IGNORECASE,
        )
        if close_before:
            target = self._strip_polite_suffix(close_before.group(1))
            if target:
                return "close", target

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

        if text in (
            "close", "close it", "close this", "stop it",
            "बंद करो", "बंद कर दो", "इसे बंद करो", "इसे बंद कर दो",
            "इसे बंद कर", "इसे रोक दो", "band karo", "band kar do"
        ):
            return {"intent": "close_current", "target": ""}

        if text in ("exit", "quit", "stop"):
            return {"intent": "close_app", "target": ""}

        natural = self._natural_family(original)
        if natural:
            family, target = natural
            return {
                "intent": "open" if family == "open" else "close_app",
                "target": target,
            }

        if text.startswith("find and open ") or text.startswith("search and open "):
            prefix = "find and open " if text.startswith("find and open ") else "search and open "
            return {"intent": "search_and_open_file", "target": text[len(prefix):].strip()}

        try:
            converted = self.multilingual.convert(original)
        except Exception:
            converted = {"success": False, "intent": "unknown", "target": ""}

        if converted.get("success"):
            family = converted.get("intent")
            target = self._strip_polite_suffix(str(converted.get("target") or "").strip())
            if family == "open":
                return {"intent": "open", "target": target}
            if family == "close":
                return {"intent": "close_app", "target": target}
            if family == "search":
                match = re.search(
                    r"([^\s]+\.(?:txt|pdf|doc|docx|xls|xlsx|csv|ppt|pptx|jpg|jpeg|png|gif|mp3|mp4|zip|rar|py|json|xml))$",
                    original,
                    flags=re.IGNORECASE,
                )
                if match:
                    target = match.group(1)
                target = re.sub(r"^(?:फाइल|फ़ाइल|file)\s+", "", target, flags=re.IGNORECASE).strip()
                return {"intent": "search_file", "target": target}

        file_extensions = (
            ".txt", ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".csv",
            ".ppt", ".pptx", ".jpg", ".jpeg", ".png", ".gif", ".mp3",
            ".mp4", ".zip", ".rar", ".py", ".json", ".xml"
        )
        if any(text.endswith(ext) for ext in file_extensions):
            return {"intent": "open_file", "target": text}

        return {"intent": "unknown", "target": original}
