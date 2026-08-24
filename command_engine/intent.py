"""
Project : Vyom AI
Version : 1.0
Module : Intent Engine

Purpose:
    Detect basic command intents and conversational selections.

    This module does not execute commands.
"""


class IntentEngine:

    # =========================================================
    # NUMBER WORDS
    # =========================================================

    NUMBER_WORDS = {

        "zero": "0",

        "one": "1",
        "first": "1",

        "two": "2",
        "second": "2",

        "three": "3",
        "third": "3",

        "four": "4",
        "fourth": "4",

        "five": "5",
        "fifth": "5",

        "six": "6",

        "seven": "7",

        "eight": "8",

        "nine": "9",

        "ten": "10",

        # Hindi
        "एक": "1",
        "पहला": "1",
        "पहली": "1",

        "दो": "2",
        "दूसरा": "2",
        "दूसरी": "2",

        "तीन": "3",
        "तीसरा": "3",
        "तीसरी": "3"
    }

    # =========================================================
    # SELECTION
    # =========================================================

    def _detect_selection(
        self,
        command
    ):

        text = command.strip().lower()

        # Direct number
        if text.isdigit():

            return text

        # Direct number word
        if text in self.NUMBER_WORDS:

            return self.NUMBER_WORDS[text]

        # number one / option one / item one
        prefixes = [
            "number ",
            "option ",
            "item ",
            "choice ",
            "no "
        ]

        for prefix in prefixes:

            if text.startswith(prefix):

                value = text[
                    len(prefix):
                ].strip()

                if value.isdigit():

                    return value

                if value in self.NUMBER_WORDS:

                    return self.NUMBER_WORDS[value]

        return None

    # =========================================================
    # DETECT
    # =========================================================

    def detect(
        self,
        command
    ):

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
                    "target": target
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
                    "target": target
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
                    "target": target
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
                    "target": target
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
                    "target": command
                }

        # =====================================================
        # UNKNOWN NATURAL-LANGUAGE GOAL
        # =====================================================

        return {
            "intent": "unknown",
            "target": command
    }
