"""
Project : Vyom AI
Version : 0.8
Module : Tool Manager
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

        intent_type = intent.get("intent")
        target = intent.get("target", "").strip()

        # -----------------------------------------
        # OPEN APPLICATION / FILE
        # -----------------------------------------

        if intent_type in ["open", "open_app", "open_file"]:

            return self.launcher.open_app(target)

        # -----------------------------------------
        # CLOSE APPLICATION
        # -----------------------------------------

        if intent_type == "close_app":

            return self.process_manager.close_app(target)

        # -----------------------------------------
        # SEARCH FILE
        # -----------------------------------------

        if intent_type == "search_file":

            results = self.file_manager.search(target)

            if not results:

                return f"File '{target}' not found."

            return "\n".join(results)

        # -----------------------------------------
        # SEARCH AND OPEN FILE
        # -----------------------------------------

        if intent_type == "search_and_open_file":

            results = self.file_manager.search(target)

            if not results:

                return f"File '{target}' not found."

            first_file = results[0]

            return self.launcher.open_app(first_file)

        # -----------------------------------------
        # UNKNOWN
        # -----------------------------------------

        return f"I don't know how to perform '{intent_type}'."
