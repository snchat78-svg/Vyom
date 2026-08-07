"""
Project : Vyom AI
Version : 0.7
Module  : Tool Manager
"""

from windows_agent.launcher import WindowsLauncher
from windows_agent.process_manager import ProcessManager
from tools.file_manager import FileManager


class ToolManager:

    def __init__(self):

        self.launcher = WindowsLauncher()
        self.process_manager = ProcessManager()
        self.file_manager = FileManager()

    def execute(self, intent):

        if intent["intent"] == "open_app":
            return self.launcher.open_app(intent["target"])

        elif intent["intent"] == "close_app":
            return self.process_manager.close_app(intent["target"])

        elif intent["intent"] == "search_file":

            results = self.file_manager.search(intent["target"])

            if not results:
                return "File not found."

            return "\n".join(results)

        return f"No tool available for {intent['intent']}"
