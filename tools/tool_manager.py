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

        intent_name = intent.get("intent", "")
        target = intent.get("target", "").strip()

        # -------------------------------------------------
        # OPEN APPLICATION
        # -------------------------------------------------

        if intent_name == "open_app":

            return self.launcher.open_app(target)

        # -------------------------------------------------
        # CLOSE APPLICATION
        # -------------------------------------------------

        elif intent_name == "close_app":

            return self.process_manager.close_app(target)

        # -------------------------------------------------
        # SEARCH FILE
        # -------------------------------------------------

        elif intent_name == "search_file":

            results = self.file_manager.search(target)

            if not results:

                return f"File not found: {target}"

            return "\n".join(results)

        # -------------------------------------------------
        # OPEN FILE
        # -------------------------------------------------

        elif intent_name == "open_file":

            return self.file_manager.open_file(target)

        # -------------------------------------------------
        # SEARCH AND OPEN FILE
        # -------------------------------------------------

        elif intent_name == "search_and_open_file":

            return self.file_manager.search_and_open(target)

        # -------------------------------------------------
        # OPEN FILE OR APPLICATION
        # -------------------------------------------------

        elif intent_name == "open":

            # First try Windows application launcher
            result = self.launcher.open_app(target)

            if "could not be found" not in result.lower():

                return result

            # If it was not an application, search for a file
            return self.file_manager.search_and_open(target)

        # -------------------------------------------------
        # UNKNOWN INTENT
        # -------------------------------------------------

        return f"No tool available for {intent_name}"
