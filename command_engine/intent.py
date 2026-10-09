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
from ai_core.goal_router import GoalRouter
from voice.command_normalizer import VoiceCommandNormalizer


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
        # Romanized Hindi number words commonly produced by speech recognition.
        "ek": "1", "one": "1", "do": "2", "teen": "3", "char": "4", "chaar": "4",
        "paanch": "5", "panch": "5", "che": "6", "chhe": "6", "chhah": "6",
        "saat": "7", "aath": "8", "nau": "9", "das": "10", "dus": "10",
        "pahla": "1", "pehla": "1", "pehli": "1", "pehle": "1",
        "dusra": "2", "doosra": "2", "dusri": "2", "doosri": "2",
        "teesra": "3", "tisra": "3", "teesri": "3",
        "chautha": "4", "choutha": "4", "chauthi": "4",
        "panchva": "5", "panchwan": "5",
        # Common Hindi spellings of spoken English number words.
        "वन": "1", "टू": "2", "थ्री": "3", "फोर": "4",
        "फाइव": "5", "सिक्स": "6", "सेवन": "7", "एट": "8",
        "नाइन": "9", "टेन": "10",
    }

    CONVERSATION_PHRASES = {
        "hello": "greeting", "hi": "greeting", "hey": "greeting",
        "नमस्ते": "greeting", "नमस्कार": "greeting", "हैलो": "greeting", "हेलो": "greeting",
        "राम राम": "greeting", "good morning": "greeting", "good evening": "greeting",
        "good afternoon": "greeting", "शुभ प्रभात": "greeting",
        "how are you": "status", "how are u": "status", "how are things": "status",
        "kya kar rahe ho": "activity", "kya kar rahe hain": "activity",
        "tumhara nam kya hai": "identity", "tumhara naam kya hai": "identity",
        "aapka nam kya hai": "identity", "aapka naam kya hai": "identity",
        "mera nam kya hai": "user_name", "mera naam kya hai": "user_name",
        "hindi men bat karo": "language_preference", "hindi mein baat karo": "language_preference",
        "hindi me baat karo": "language_preference", "hindi men baat karo": "language_preference",
        "हिंदी में बात करो": "language_preference", "हिन्दी में बात करो": "language_preference",
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
        self.goal_router = GoalRouter()
        self.voice_normalizer = VoiceCommandNormalizer()

    def _normalize(self, text: Any) -> str:
        value = str(text or "").strip().lower()
        return re.sub(r"\s+", " ", value)

    @staticmethod
    def _is_incomplete_location_fragment(text: str) -> bool:
        value = re.sub(r"\s+", " ", str(text or "").strip().lower())
        tokens = value.split()
        if len(tokens) < 2 or len(tokens) > 4:
            return False
        if tokens[-1] not in {
            "in", "men", "mein", "me", "में", "का", "की", "के", "par", "पर",
            "about", "of", "ke",
        }:
            return False
        action_words = {
            "open", "launch", "start", "run", "close", "stop", "search", "find",
            "click", "type", "write", "send", "select", "choose", "khol", "kholo",
            "karo", "करो", "खोलो", "बंद", "लिखो", "भेजो",
        }
        return not any(token in action_words for token in tokens)

    def _conversation(self, text: str):
        if text in self.CONVERSATION_PHRASES:
            return self.CONVERSATION_PHRASES[text]

        patterns = [
            # Conversation recognition must also work after the voice boundary
            # has normalized Hindi speech into Roman/Hinglish text.
            (r"^(?:hi|hello|hey|helo|namaste|namaskar|pranam)\b.*", "greeting"),
            (r"^(?:good morning|good afternoon|good evening)\b.*", "greeting"),
            (r"^(?:कैसे हो|क्या हाल है|कैसा चल रहा है)\b.*", "status"),
            (r"^(?:kaise ho|kaise hain|kya haal|sab thik|sab theek)$", "status"),
            (r"^(?:tum|aap)\s+(?:kaise ho|kaise|kya haal|sab thik|theek ho).*", "status"),
            (r"^(?:तुम|आप)\s+(?:कैसे|क्या हाल).*", "status"),
            (r"^(?:what|tell me)\s+(?:can|could)\s+you\s+do.*", "capabilities"),
            (r"^(?:tum|aap)\s+(?:kya kar sakte ho|kya karte ho|kya kar sakte).*", "capabilities"),
            (r"^(?:तुम|आप)\s+क्या\s+कर\s+सकते.*", "capabilities"),
            (r"^(?:who are you|what are you).*", "identity"),
            (r"^(?:tum|aap)\s+(?:kaun ho|kaun hain).*", "identity"),
            (r"^(?:तुम कौन हो|आप कौन हैं).*", "identity"),
            (r"^(?:tumhara|aapka|apka)\\s+(?:nam|naam)\\s+kya hai$", "identity"),
            (r"^(?:mera|meri)\\s+(?:nam|naam)\\s+kya hai$", "user_name"),
            (r"^(?:hindi|हिंदी|हिन्दी)(?:\\s+(?:mein|me|men|में))?\\s+(?:baat|bat)\\s+(?:karo|kijiye|kiji|करो|करें)$", "language_preference"),
            (r"^(?:(?:tum|aap)\\s+)?kya kar rahe (?:ho|hain)$", "activity"),
        ]
        for pattern, kind in patterns:
            if re.match(pattern, text, flags=re.IGNORECASE):
                return kind
        return None

    def _selection_value(self, value: str):
        candidate = self._normalize(value).strip()
        if not candidate:
            return None
        if candidate.isdigit():
            return candidate
        mapped = self.NUMBER_WORDS.get(candidate)
        if mapped is not None:
            return mapped
        return None

    def _strip_selection_suffix(self, value: str) -> str:
        candidate = self._normalize(value).strip()
        if not candidate:
            return ""

        suffixes = (
            "open it", "open", "select", "choose", "pick",
            "please", "pls", "kholo", "khol", "kholen",
            "khol do", "kholdo", "open karo", "open kar",
            "select karo", "select kar", "chuno", "chun lo",
            "चुनो", "चुनिए", "चुन लो", "खोलो", "खोलना",
            "खोलिए", "खोलिये", "खोल दो", "खोल दें",
            "कर दो", "करो"
        )
        changed = True
        while changed and candidate:
            changed = False
            for suffix in sorted(suffixes, key=len, reverse=True):
                if candidate == suffix:
                    return ""
                marker = " " + suffix
                if candidate.endswith(marker):
                    candidate = candidate[:-len(marker)].strip()
                    changed = True
                    break
        return candidate

    def _detect_selection(self, command: str):
        text = self._normalize(command)
        if not text:
            return None

        direct = self._selection_value(text)
        if direct is not None:
            return direct

        # Prefix selections:
        #   number 1
        #   number 1 kholo
        #   option one open
        #   no 2 select
        prefix_match = re.match(
            r"^(?:number|nambar|नंबर|क्रमांक|option|item|choice|no)\s+(.+)$",
            text,
            flags=re.IGNORECASE,
        )
        if prefix_match:
            candidate = self._strip_selection_suffix(prefix_match.group(1))
            direct = self._selection_value(candidate)
            if direct is not None:
                return direct

            # Spoken number followed by extra action words.
            first_token = candidate.split(" ", 1)[0] if candidate else ""
            direct = self._selection_value(first_token)
            if direct is not None and len(candidate.split()) <= 3:
                return direct

        # Bare numeric selection followed by a generic action:
        #   1
        #   1 kholo
        #   2 open karo
        numeric_match = re.match(
            r"^(\d+)(?:\s+.+)?$",
            text,
            flags=re.IGNORECASE,
        )
        if numeric_match:
            return numeric_match.group(1)

        cleaned = self._strip_selection_suffix(text)

        # Ordinal / number phrases such as:
        #   first one open
        #   second option
        #   पहला वाला खोलो
        if cleaned in (
            "first one", "first option", "first item",
            "second one", "second option", "second item",
            "third one", "third option", "third item",
            "fourth one", "fourth option", "fourth item",
            "fifth one", "fifth option", "fifth item",
            "पहला वाला", "पहली वाली", "पहले वाला", "पहले वाली",
            "दूसरा वाला", "दूसरी वाली", "दूसरे वाला",
            "तीसरा वाला", "तीसरी वाली", "तीसरे वाला",
            "चौथा वाला", "चौथी वाली",
            "पांचवां वाला", "पाँचवाँ वाला",
        ):
            return {
                "first one": "1", "first option": "1", "first item": "1",
                "second one": "2", "second option": "2", "second item": "2",
                "third one": "3", "third option": "3", "third item": "3",
                "fourth one": "4", "fourth option": "4", "fourth item": "4",
                "fifth one": "5", "fifth option": "5", "fifth item": "5",
                "पहला वाला": "1", "पहली वाली": "1", "पहले वाला": "1", "पहले वाली": "1",
                "दूसरा वाला": "2", "दूसरी वाली": "2", "दूसरे वाला": "2",
                "तीसरा वाला": "3", "तीसरी वाली": "3", "तीसरे वाला": "3",
                "चौथा वाला": "4", "चौथी वाली": "4",
                "पांचवां वाला": "5", "पाँचवाँ वाला": "5",
            }[cleaned]

        # Natural "open the first/second/third" forms.
        ordinal_patterns = (
            r"^(?:open|select|choose|pick)\s+the\s+(first|second|third|fourth|fifth)$",
            r"^(first|second|third|fourth|fifth)\s+(?:one|option|item)$",
        )
        for pattern in ordinal_patterns:
            match = re.match(pattern, cleaned, flags=re.IGNORECASE)
            if match:
                return self.NUMBER_WORDS.get(match.group(1))

        # Romanized Hindi ordinals produced by the voice boundary.
        roman_ordinal = self._selection_value(cleaned)
        if roman_ordinal is not None:
            return roman_ordinal

        # Generic "number/option/item ..." forms with a trailing action.
        generic_match = re.match(
            r"^(?:number|nambar|नंबर|क्रमांक|option|item|choice|no)\s+(.+)$",
            text,
            flags=re.IGNORECASE,
        )
        if generic_match:
            candidate = self._strip_selection_suffix(generic_match.group(1))
            return self._selection_value(candidate)

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
            r"^(?:please\s+|मेरे\s+लिए\s+|मुझे\s+|जरा\s+|ज़रा\s+)?(.+?)\s+(?:open|launch|start|run|खोल|खोलो|खोलना|खोलिए|खोलिये|चालू करो|चालू|चलाओ|चला दो|चला|khol|kholo|kholna|kholiye|kholen|khol do|kholdo|chalu|chalu karo|chalao|open karo|open kar|launch karo|start karo|ओपन|खोल दो|ओपन करो)(?:\s+.*)?$",
            text,
            flags=re.IGNORECASE,
        )
        if open_after:
            target = self._strip_polite_suffix(open_after.group(1))
            target = re.sub(r"^(?:the|a|an)\s+", "", target, flags=re.IGNORECASE)
            if target:
                return "open", target

        open_before = re.match(
            r"^(?:please\s+)?(?:open|launch|start|run|खोलो?|खोलना|खोलिए|खोलिये|खोल दो|चालू करो|चालू|चलाओ|चला दो|khol|kholo|kholna|kholiye|kholen|khol do|kholdo|chalu|chalu karo|chalao|open karo|open kar|launch karo|start karo|opan|opn)\s+(.+?)$",
            text,
            flags=re.IGNORECASE,
        )
        if open_before:
            target = self._strip_polite_suffix(open_before.group(1))
            target = re.sub(r"^(?:the|a|an|मेरे लिए|मुझे)\s+", "", target, flags=re.IGNORECASE)
            if target:
                return "open", target

        close_after = re.match(
            r"^(?:please\s+|मेरे\s+लिए\s+|मुझे\s+)?(.+?)\s+(?:close|exit|quit|stop|बंद|बंद करो|बंद कर|बंद कर दो|बन्द|रोक|रोक दो|क्लोज|क्लोज करो|band|band karo|band kar|band kar do|rok|rok do|close karo|close kar|close kar do)(?:\s+.*)?$",
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

    def detect(self, command: Any, metadata: Any = None) -> Dict[str, Any]:
        original = str(command or "").strip()
        voice_meta = self.voice_normalizer.normalize(original)

        # Preserve voice-origin information that is not present in the
        # normalized Romanized command. This lets downstream response
        # generation choose the user's actual spoken language.
        if isinstance(metadata, dict):
            external_voice = metadata.get("voice")
            if isinstance(external_voice, dict):
                voice_meta = dict(voice_meta)
                for key in ("raw_text", "recognized_language", "language", "roman_text"):
                    value = external_voice.get(key)
                    if value not in (None, ""):
                        voice_meta[key] = value
        normalized_input = str(voice_meta.get("text") or original).strip()
        text = self._normalize(normalized_input)
        if not text:
            return {"intent": "unknown", "target": "", "selection": None, "voice": voice_meta}

        selection = self._detect_selection(text)
        if selection is not None:
            return {"intent": "selection", "target": selection, "selection": selection, "voice": voice_meta}

        conversation = self._conversation(text)
        if conversation:
            return {
                "intent": "conversation",
                "target": conversation,
                "conversation_type": conversation,
                "voice": voice_meta,
            }

        # STT may return only the location/topic prefix of a longer question.
        # Ask for the rest rather than routing this fragment to a capability.
        if self._is_incomplete_location_fragment(text):
            return {
                "intent": "conversation",
                "target": "clarification",
                "conversation_type": "clarification",
                "voice": voice_meta,
            }

        if text in (
            "close", "close it", "close this", "stop it",
            "बंद करो", "बंद कर दो", "इसे बंद करो", "इसे बंद कर दो",
            "इसे बंद कर", "इसे रोक दो", "band karo", "band kar do"
        ):
            return {"intent": "close_current", "target": "", "voice": voice_meta}

        if text in ("exit", "quit", "stop"):
            return {"intent": "close_app", "target": "", "voice": voice_meta}

        # Explicit file-search language remains on the proven
        # file-search fast path. General searches continue to semantic
        # reasoning instead.
        file_search_match = re.match(
            r"^(?:search|find)\s+(?:file|document)\s+(.+)$",
            text,
            flags=re.IGNORECASE,
        )
        if file_search_match:
            return {
                "intent": "search_file",
                "target": self._strip_polite_suffix(file_search_match.group(1)),
                "voice": voice_meta,
            }

        # A bare open command is still a known command. Return a missing
        # target so the executor can ask what should be opened instead of
        # sending the input down the unknown-goal path.
        if text in (
            "open", "launch", "start", "run",
            "open karo", "launch karo", "start karo", "run karo",
            "खोल", "खोलो", "खोलना", "खोलिए", "खोलिये",
            "खोल दो", "ओपन", "ओपन करो",
            "चालू", "चालू करो", "चलाओ",
            "khol", "kholo", "kholna", "kholiye", "kholen", "khol do", "kholdo",
            "chalu", "chalu karo", "chalao",
        ):
            return {"intent": "open", "target": "", "voice": voice_meta}

        # ---------------------------------------------------------
        # COMMAND / GOAL BOUNDARY
        # ---------------------------------------------------------
        # Run this before the natural open/close regexes. Those regexes are
        # intentionally permissive for single actions; without this boundary
        # a compound request could be reduced to its first action.
        route = self.goal_router.classify(text)
        if route.get("route") == "goal":
            return {
                "intent": "goal",
                "target": original,
                "goal": original,
                "route_reason": route.get("reason", "goal"),
                "compound": bool(route.get("compound", False)),
                "voice": voice_meta,
            }

        natural = self._natural_family(normalized_input)
        if natural:
            family, target = natural
            return {
                "intent": "open" if family == "open" else "close_app",
                "target": target,
                "voice": voice_meta,
            }

        if text.startswith("find and open ") or text.startswith("search and open "):
            prefix = "find and open " if text.startswith("find and open ") else "search and open "
            return {"intent": "search_and_open_file", "target": text[len(prefix):].strip(), "voice": voice_meta}

        try:
            converted = self.multilingual.convert(original)
        except Exception:
            converted = {"success": False, "intent": "unknown", "target": ""}

        if converted.get("success"):
            family = converted.get("intent")
            target = self._strip_polite_suffix(str(converted.get("target") or "").strip())
            if family == "open":
                return {"intent": "open", "target": target, "voice": voice_meta}
            if family == "close":
                return {"intent": "close_app", "target": target, "voice": voice_meta}
            if family == "search":
                match = re.search(
                    r"([^\s]+\.(?:txt|pdf|doc|docx|xls|xlsx|csv|ppt|pptx|jpg|jpeg|png|gif|mp3|mp4|zip|rar|py|json|xml))$",
                    original,
                    flags=re.IGNORECASE,
                )
                if match:
                    target = match.group(1)
                    target = re.sub(r"^(?:फाइल|फ़ाइल|file)\s+", "", target, flags=re.IGNORECASE).strip()
                    return {"intent": "search_file", "target": target, "voice": voice_meta}

                if re.search(r"\b(?:search|find)\s+(?:file|document)\b", text, flags=re.IGNORECASE):
                    return {
                        "intent": "search_file",
                        "target": self._strip_polite_suffix(target),
                        "voice": voice_meta,
                    }

                # General search requests are not file-search requests.
                # Preserve the complete utterance for semantic reasoning.
                return {
                    "intent": "unknown",
                    "target": original,
                    "voice": voice_meta,
                }

        file_extensions = (
            ".txt", ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".csv",
            ".ppt", ".pptx", ".jpg", ".jpeg", ".png", ".gif", ".mp3",
            ".mp4", ".zip", ".rar", ".py", ".json", ".xml"
        )
        if any(text.endswith(ext) for ext in file_extensions):
            return {"intent": "open_file", "target": text, "voice": voice_meta}

        return {"intent": "unknown", "target": original, "voice": voice_meta}
