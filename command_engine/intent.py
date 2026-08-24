"""
Project : Vyom AI
Version : 1.0
Module  : Intent Engine

Purpose:
    Convert natural language into a lightweight intent.

Important:
    IntentEngine does NOT execute anything.

    It only identifies:
        - intent
        - target
        - selection
        - possible continuation

    AutonomousSession decides what the instruction means
    in the current context.
"""


class IntentEngine:

    # =========================================================
    # NUMBER WORDS
    # =========================================================

    NUMBER_WORDS = {
        "zero": "0",
        "one": "1",
        "two": "2",
        "three": "3",
        "four": "4",
        "five": "5",
        "six": "6",
        "seven": "7",
        "eight": "8",
        "nine": "9",
        "ten": "10",

        "first": "1",
        "second": "2",
        "third": "3",
        "fourth": "4",
        "fifth": "5",

        "पहला": "1",
        "पहली": "1",
        "एक": "1",

        "दूसरा": "2",
        "दूसरी": "2",
        "दो": "2",

        "तीसरा": "3",
        "तीसरी": "3",
        "तीन": "3"
    }

    # =========================================================
    # SELECTION NORMALIZATION
    # =========================================================

    def _detect_selection(self, command):

        text = command.strip().lower()

        # Direct number
        if text.isdigit():
            return text

        # "number one"
        prefixes = [
            "number ",
            "option ",
            "item ",
            "choice ",
            "no "
        ]

        for prefix in prefixes:

            if text.startswith(prefix):

                value = text[len(prefix):].strip()

                if value.isdigit():
                    return value

                if value in self.NUMBER_WORDS:
                    return self.NUMBER_WORDS[value]

        # Direct number word
        if text in self.NUMBER_WORDS:
            return self.NUMBER_WORDS[text]

        return None

    # =========================================================
    # DETECT
    # =========================================================

    def detect(self, command):

        command = str(
            command or ""
        ).strip().lower()

        if not command:

            return {
                "intent": "unknown",
                "target": "",
                "selection": None
            }

        # =====================================================
        # SELECTION
        # =====================================================

        selection = self._detect_selection(
            command
        )

        if selection is not None:

            return {
                "intent": "selection",
                "target": selection,
                "selection": selection
            }

        # =====================================================
        # CLOSE
        # =====================================================

        close_words = [
            "close ",
            "quit ",
            "exit "
        ]

        for word in close_words:

            if command.startswith(word):

                target = command[
                    len(word):
                ].strip()

                return {
                    "intent": "close_app",
                    "target": target,
                    "selection": None
                }

        # =====================================================
        # FIND AND OPEN
        # =====================================================

        open_search_words = [
            "find and open ",
            "search and open "
        ]

        for word in open_search_words:

            if command.startswith(word):

                target = command[
                    len(word):
                ].strip()

                return {
                    "intent": "search_and_open_file",
                    "target": target,
                    "selection": None
                }

        # =====================================================
        # SEARCH
        # =====================================================

        search_words = [
            "search ",
            "find ",
            "look for "
        ]

        for word in search_words:

            if command.startswith(word):

                target = command[
                    len(word):
                ].strip()

                return {
                    "intent": "search_file",
                    "target": target,
                    "selection": None
                }

        # =====================================================
        # OPEN
        # =====================================================

        open_words = [
            "open ",
            "launch ",
            "start ",
            "run "
        ]

        for word in open_words:

            if command.startswith(word):

                target = command[
                    len(word):
                ].strip()

                return {
                    "intent": "open",
                    "target": target,
                    "selection": None
                }

        # =====================================================
        # DIRECT FILE
        # =====================================================

        file_extensions = [
            ".txt",
            ".pdf",
            ".doc",
            ".docx",
            ".xls",
            ".xlsx",
            ".csv",
            ".ppt",
            ".pptx",
            ".jpg",
            ".jpeg",
            ".png",
            ".gif",
            ".mp3",
            ".mp4",
            ".zip",
            ".rar"
        ]

        for extension in file_extensions:

            if command.endswith(extension):

                return {
                    "intent": "open_file",
                    "target": command,
                    "selection": None
                }

        # =====================================================
        # UNKNOWN / NATURAL LANGUAGE GOAL
        # =====================================================

        return {
            "intent": "unknown",
            "target": command,
            "selection": None
            }
