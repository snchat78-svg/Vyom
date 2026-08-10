"""
Project : Vyom AI
Version : 0.8
Module : Intent Engine
"""


class IntentEngine:

    def detect(self, command):

        command = command.strip().lower()

        if not command:
            return {
                "intent": "unknown",
                "target": ""
            }

        # -------------------------------------------------
        # CLOSE APPLICATION
        # -------------------------------------------------

        close_words = [
            "close ",
            "quit ",
            "exit "
        ]

        for word in close_words:

            if command.startswith(word):

                target = command[len(word):].strip()

                return {
                    "intent": "close_app",
                    "target": target
                }

        # -------------------------------------------------
        # SEARCH FILE
        # -------------------------------------------------

        search_words = [
            "search ",
            "find ",
            "look for "
        ]

        for word in search_words:

            if command.startswith(word):

                target = command[len(word):].strip()

                return {
                    "intent": "search_file",
                    "target": target
                }

        # -------------------------------------------------
        # SEARCH AND OPEN FILE
        # -------------------------------------------------

        open_search_words = [
            "find and open ",
            "search and open "
        ]

        for word in open_search_words:

            if command.startswith(word):

                target = command[len(word):].strip()

                return {
                    "intent": "search_and_open_file",
                    "target": target
                }

        # -------------------------------------------------
        # OPEN APPLICATION / FILE
        # -------------------------------------------------

        open_words = [
            "open ",
            "launch ",
            "start ",
            "run "
        ]

        for word in open_words:

            if command.startswith(word):

                target = command[len(word):].strip()

                return {
                    "intent": "open",
                    "target": target
                }

        # -------------------------------------------------
        # DIRECT FILE EXTENSIONS
        # -------------------------------------------------

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

        # -------------------------------------------------
        # UNKNOWN COMMAND
        # -------------------------------------------------

        return {
            "intent": "unknown",
            "target": command
                }
