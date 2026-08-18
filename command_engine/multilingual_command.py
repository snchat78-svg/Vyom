# ============================================================
# Project : Vyom AI
# Module  : multilingual_command.py
# Version : 0.2
#
# Purpose:
#     Generic multilingual / Hinglish command normalization
#     foundation for Vyom AI.
#
# IMPORTANT:
#     This module does NOT contain a fixed application list.
#
#     Examples such as:
#
#         WhatsApp खोलो
#         Chrome खोल दो
#         Calculator khol do
#
#     are only examples.
#
#     Any application name can be passed to this module.
#
#     Actual application discovery and launching is handled by:
#
#         UniversalAppLauncher
#
# Supported command families:
#
#     OPEN
#     CLOSE
#     SEARCH
#
# Examples:
#
#     "WhatsApp खोलो"
#     "व्हाट्सऐप खोल दो"
#     "WhatsApp khol do"
#     "Open WhatsApp"
#     "please open WhatsApp"
#     "क्रोम चला दो"
#     "Calculator बंद करो"
#     "WhatsApp search karo"
#
# Result:
#
#     intent = open
#     target = whatsapp
#
# ============================================================


import re


class MultilingualCommand:

    # ========================================================
    # INITIALIZATION
    # ========================================================

    def __init__(self):

        # ----------------------------------------------------
        # IMPORTANT
        #
        # These are command-language expressions only.
        #
        # Application names are NEVER stored here.
        # ----------------------------------------------------

        self.open_phrases = [

            # English
            "open",
            "launch",
            "start",
            "run",

            # Hindi
            "खोल",
            "खोलो",
            "खोलना",
            "खोलिए",
            "खोलिये",
            "चालू",
            "चालू करो",
            "चला",
            "चलाओ",
            "चलाओ",

            # Hinglish
            "khol",
            "kholo",
            "kholna",
            "kholiye",
            "chalu",
            "chalu karo",
            "chalao",
            "chala",
            "start karo",
            "open karo",
            "open kar",
            "open kr",
            "launch karo",
            "launch kar",
            "run karo",
            "run kar",
        ]

        self.close_phrases = [

            # English
            "close",
            "exit",
            "quit",
            "stop",

            # Hindi
            "बंद",
            "बंद करो",
            "बंद कर",
            "बंद कर दो",
            "बन्द",
            "बन्द करो",
            "बन्द कर दो",
            "रोक",
            "रोक दो",

            # Hinglish
            "band",
            "band karo",
            "band kar",
            "band kar do",
            "bnd",
            "rok",
            "rok do",
            "close karo",
            "close kar",
            "close kar do",
            "exit karo",
            "stop karo",
        ]

        self.search_phrases = [

            # English
            "search",
            "find",
            "look for",
            "look up",

            # Hindi
            "खोज",
            "खोजो",
            "खोजना",
            "ढूंढ",
            "ढूंढो",
            "ढूँढ",
            "ढूँढो",
            "ढूंढना",
            "तलाश",
            "तलाशो",
            "पता करो",
            "पता लगाओ",

            # Hinglish
            "search karo",
            "search kar",
            "search kr",
            "find karo",
            "find kar",
            "dhund",
            "dhundo",
            "dhundna",
            "dhoond",
            "dhoondo",
            "dhoondna",
            "talash",
            "talasho",
        ]

        # ----------------------------------------------------
        # Generic conversational/filler words.
        #
        # These are NOT application names.
        # ----------------------------------------------------

        self.filler_phrases = [

            # English
            "please",
            "pls",
            "could you",
            "can you",
            "would you",
            "i want you to",
            "i need you to",

            # Hindi
            "कृपया",
            "जरा",
            "ज़रा",
            "मेरे लिए",
            "मुझे",
            "आप",
            "आपको",
            "कर दो",
            "करदो",
            "कर दें",
            "करदें",

            # Hinglish
            "please",
            "mere liye",
            "mujhe",
            "aap",
            "aapko",
            "zara",
            "jara",
            "karo",
            "kar do",
            "kar",
            "kr",
            "do",
        ]

        # ----------------------------------------------------
        # Sort longest phrases first.
        #
        # Example:
        #
        # "open kar do"
        #
        # must be processed before:
        #
        # "open"
        # ----------------------------------------------------

        self.open_phrases = self._sort_phrases(
            self.open_phrases
        )

        self.close_phrases = self._sort_phrases(
            self.close_phrases
        )

        self.search_phrases = self._sort_phrases(
            self.search_phrases
        )

        self.filler_phrases = self._sort_phrases(
            self.filler_phrases
        )

    # ========================================================
    # SORT PHRASES
    # ========================================================

    def _sort_phrases(self, phrases):

        unique = []

        seen = set()

        for phrase in phrases:

            phrase = str(
                phrase
            ).strip().lower()

            if not phrase:
                continue

            if phrase in seen:
                continue

            seen.add(
                phrase
            )

            unique.append(
                phrase
            )

        unique.sort(
            key=len,
            reverse=True
        )

        return unique

    # ========================================================
    # NORMALIZE TEXT
    # ========================================================

    def normalize_text(self, text):

        if text is None:

            return ""

        text = str(
            text
        ).strip().lower()

        # ----------------------------------------------------
        # Unicode normalization is intentionally kept simple.
        #
        # Python 3 handles Unicode text natively.
        # ----------------------------------------------------

        text = re.sub(
            r"\s+",
            " ",
            text
        )

        return text.strip()

    # ========================================================
    # NORMALIZE PUNCTUATION
    # ========================================================

    def normalize_punctuation(self, text):

        if not text:

            return ""

        # Keep Unicode letters/numbers.
        #
        # Remove command punctuation that commonly appears
        # in speech-to-text results.
        #

        text = text.replace(
            ",",
            " "
        )

        text = text.replace(
            ".",
            " "
        )

        text = text.replace(
            "?",
            " "
        )

        text = text.replace(
            "!",
            " "
        )

        text = text.replace(
            "।",
            " "
        )

        text = text.replace(
            ":",
            " "
        )

        text = re.sub(
            r"\s+",
            " ",
            text
        )

        return text.strip()

    # ========================================================
    # PHRASE BOUNDARY CHECK
    # ========================================================

    def _phrase_pattern(self, phrase):

        escaped = re.escape(
            phrase
        )

        # ----------------------------------------------------
        # English/Latin words use word boundaries.
        #
        # For Unicode scripts such as Hindi, normal whitespace
        # boundaries are safer.
        # ----------------------------------------------------

        if re.search(
            r"[a-zA-Z]",
            phrase
        ):

            return (
                r"(?<![a-zA-Z0-9_])"
                + escaped
                + r"(?![a-zA-Z0-9_])"
            )

        return escaped

    # ========================================================
    # REMOVE PHRASES
    # ========================================================

    def remove_phrases(
        self,
        text,
        phrases
    ):

        result = text

        for phrase in phrases:

            pattern = self._phrase_pattern(
                phrase
            )

            result = re.sub(
                pattern,
                " ",
                result,
                flags=re.IGNORECASE
            )

        result = re.sub(
            r"\s+",
            " ",
            result
        )

        return result.strip()

    # ========================================================
    # FIND INTENT
    # ========================================================

    def detect_intent(self, text):

        text = self.normalize_text(
            text
        )

        text = self.normalize_punctuation(
            text
        )

        if not text:

            return "unknown"

        # ----------------------------------------------------
        # Priority
        #
        # CLOSE
        # SEARCH
        # OPEN
        #
        # This prevents a generic word from being interpreted
        # incorrectly when a more specific command exists.
        # ----------------------------------------------------

        for phrase in self.close_phrases:

            if re.search(
                self._phrase_pattern(
                    phrase
                ),
                text,
                flags=re.IGNORECASE
            ):

                return "close"

        for phrase in self.search_phrases:

            if re.search(
                self._phrase_pattern(
                    phrase
                ),
                text,
                flags=re.IGNORECASE
            ):

                return "search"

        for phrase in self.open_phrases:

            if re.search(
                self._phrase_pattern(
                    phrase
                ),
                text,
                flags=re.IGNORECASE
            ):

                return "open"

        return "unknown"

    # ========================================================
    # EXTRACT TARGET
    # ========================================================

    def extract_target(
        self,
        text,
        intent
    ):

        text = self.normalize_text(
            text
        )

        text = self.normalize_punctuation(
            text
        )

        if not text:

            return ""

        # ----------------------------------------------------
        # Remove the detected command family.
        # ----------------------------------------------------

        if intent == "open":

            text = self.remove_phrases(
                text,
                self.open_phrases
            )

        elif intent == "close":

            text = self.remove_phrases(
                text,
                self.close_phrases
            )

        elif intent == "search":

            text = self.remove_phrases(
                text,
                self.search_phrases
            )

        # ----------------------------------------------------
        # Remove generic conversational words.
        # ----------------------------------------------------

        text = self.remove_phrases(
            text,
            self.filler_phrases
        )

        # ----------------------------------------------------
        # Remove repeated spaces.
        # ----------------------------------------------------

        text = re.sub(
            r"\s+",
            " ",
            text
        )

        return text.strip()

    # ========================================================
    # CONVERT
    # ========================================================

    def convert(self, text):

        original = self.normalize_text(
            text
        )

        if not original:

            return {
                "success": False,
                "original": "",
                "intent": "unknown",
                "target": "",
                "command": "",
            }

        intent = self.detect_intent(
            original
        )

        if intent == "unknown":

            return {
                "success": False,
                "original": original,
                "intent": "unknown",
                "target": "",
                "command": "",
            }

        target = self.extract_target(
            original,
            intent
        )

        # ----------------------------------------------------
        # No target means the command is incomplete.
        # ----------------------------------------------------

        if not target:

            return {
                "success": False,
                "original": original,
                "intent": intent,
                "target": "",
                "command": intent,
            }

        command = (
            intent
            + " "
            + target
        )

        return {
            "success": True,
            "original": original,
            "intent": intent,
            "target": target,
            "command": command,
        }

    # ========================================================
    # SIMPLE COMMAND
    # ========================================================

    def normalize_command(self, text):

        result = self.convert(
            text
        )

        if not result.get(
            "success"
        ):

            return ""

        return result.get(
            "command",
            ""
        )


# ============================================================
# STANDALONE TEST
#
# IMPORTANT:
#     Application names below are TEST INPUT ONLY.
#
#     They are NOT stored inside the class.
# ============================================================

def main():

    print("=" * 70)
    print("Vyom AI - Multilingual Command Normalizer v0.2")
    print("=" * 70)
    print("")
    print(
        "Type any command. Type 'exit' to stop."
    )
    print("")

    converter = MultilingualCommand()

    while True:

        try:

            text = input(
                "You : "
            ).strip()

        except (
            KeyboardInterrupt,
            EOFError
        ):

            print("")
            break

        if not text:

            continue

        if text.lower() in (
            "exit",
            "quit"
        ):

            break

        result = converter.convert(
            text
        )

        print(
            "Intent  : "
            + result.get(
                "intent",
                ""
            )
        )

        print(
            "Target  : "
            + result.get(
                "target",
                ""
            )
        )

        print(
            "Command : "
            + result.get(
                "command",
                ""
            )
        )

        print("")


if __name__ == "__main__":

    main()
