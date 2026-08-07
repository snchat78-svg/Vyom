"""
Project : Vyom AI
Version : 0.2
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

        return {
            "intent": "unknown",
            "target": command
        }
