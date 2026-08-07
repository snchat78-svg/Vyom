"""
Project : Vyom AI
Version : 0.7
Module  : Intent Engine
"""

class IntentEngine:

    def detect(self, command):

        command = command.lower()

        if "open" in command:
            return {
                "intent": "open_app",
                "target": command.replace("open", "").strip()
            }

        if "close" in command:
            return {
                "intent": "close_app",
                "target": command.replace("close", "").strip()
            }

        if "search" in command:
            return {
                "intent": "search_file",
                "target": command.replace("search", "").strip()
            }

        return {
            "intent": "unknown",
            "target": command
        }
