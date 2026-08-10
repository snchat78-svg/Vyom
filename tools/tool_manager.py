"""
Project : Vyom AI
Version : 0.9
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

    # =================================================
    # EXECUTE INTENT
    # =================================================

    def execute(self, intent):

        intent_type = intent.get("intent")
        target = intent.get("target", "").strip()

        # -------------------------------------------------
        # OPEN APPLICATION / FILE
        # -------------------------------------------------

        if intent_type == "open":

            # First try application / shortcut
            result = self.launcher.open_app(target)

            # If application was not found,
            # search for a file with the same name.
            if "was not found" in result.lower():

                return self.file_manager.search_and_open(
                    target
                )

            return result

        # -------------------------------------------------
        # OPEN FILE
        # -------------------------------------------------

        if intent_type == "open_file":

            return self.file_manager.search_and_open(
                target
            )

        # -------------------------------------------------
        # SEARCH FILE
        # -------------------------------------------------

        if intent_type == "search_file":

            results = self.file_manager.search(target)

            if not results:

                return f"File '{target}' was not found."

            return "\n".join(results)

        # -------------------------------------------------
        # SEARCH AND OPEN FILE
        # -------------------------------------------------

        if intent_type == "search_and_open_file":

            return self.file_manager.search_and_open(
                target
            )

        # -------------------------------------------------
        # CLOSE APPLICATION
        # -------------------------------------------------

        if intent_type == "close_app":

            return self.process_manager.close_app(
                target
            )

        # -------------------------------------------------
        # UNKNOWN
        # -------------------------------------------------

        if intent_type == "unknown":

            return (
                f"I don't understand the command: "
                f"{target}"
            )

        return f"No tool available for {intent_type}"
