"""
Project : Vyom AI
Version : 0.9
Module : Tool Manager
"""

from windows_agent.process_manager import ProcessManager
from tools.file_manager import FileManager
from tools.universal_resolver import UniversalResolver


class ToolManager:

    def __init__(self):

        self.process_manager = ProcessManager()
        self.file_manager = FileManager()
        self.resolver = UniversalResolver()

    # =================================================
    # EXECUTE INTENT
    # =================================================

    def execute(self, intent):

        intent_type = intent.get("intent")
        target = intent.get("target", "").strip()

        # -------------------------------------------------
        # OPEN APPLICATION / FILE / FOLDER
        # -------------------------------------------------

        if intent_type == "open":

            return self.resolver.open(target)

        # -------------------------------------------------
        # OPEN FILE
        # -------------------------------------------------

        if intent_type == "open_file":

            return self.resolver.open(target)

        # -------------------------------------------------
        # SEARCH AND OPEN
        # -------------------------------------------------

        if intent_type == "search_and_open_file":

            return self.resolver.search_and_open(target)

        # -------------------------------------------------
        # SEARCH FILE
        # -------------------------------------------------

        if intent_type == "search_file":

            results = self.file_manager.search(target)

            if not results:

                return f"File '{target}' was not found."

            if len(results) == 1:

                return results[0]

            return (
                f"Multiple results found for '{target}':\n"
                + "\n".join(
                    f"{i + 1}. {path}"
                    for i, path in enumerate(results)
                )
            )

        # -------------------------------------------------
        # CLOSE APPLICATION
        # -------------------------------------------------

        if intent_type == "close_app":

            return self.process_manager.close_app(target)

        # -------------------------------------------------
        # UNKNOWN COMMAND
        # -------------------------------------------------

        if intent_type == "unknown":

            return (
                f"I don't understand the command: "
                f"{target}"
            )

        # -------------------------------------------------
        # UNSUPPORTED INTENT
        # -------------------------------------------------

        return f"No tool available for '{intent_type}'."
