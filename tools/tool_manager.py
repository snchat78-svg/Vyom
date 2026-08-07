"""
Project : Vyom AI
Version : 0.6
Module  : Tool Manager
"""

from windows_agent.launcher import WindowsLauncher
from windows_agent.process_manager import ProcessManager


class ToolManager:

    def __init__(self):

        self.launcher = WindowsLauncher()
        self.process_manager = ProcessManager()

    def execute(self, intent):

        if intent["intent"] == "open_app":

            return self.launcher.open_app(intent["target"])

        elif intent["intent"] == "close_app":

            return self.process_manager.close_app(intent["target"])

        return f"No tool available for {intent['intent']}"
