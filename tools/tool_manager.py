"""
Project : Vyom AI
Version : 0.10
Module : Tool Manager

Purpose:
    Connect Vyom intents with:
    - Universal Windows Resolver
    - File Manager
    - Process Manager
    - Selection Memory
"""

from windows_agent.process_manager import ProcessManager
from tools.file_manager import FileManager
from tools.universal_resolver import UniversalResolver
from memory.selection_manager import SelectionManager


class ToolManager:

    def __init__(self):

        self.process_manager = ProcessManager()
        self.file_manager = FileManager()
        self.resolver = UniversalResolver()
        self.selection_manager = SelectionManager()

    # =================================================
    # SAVE AND DISPLAY MULTIPLE RESULTS
    # =================================================

    def _save_multiple_results(self, target, results):

        self.selection_manager.save(results)

        message = (
            f"Multiple items found for '{target}':\n"
        )

        for index, path in enumerate(
            results,
            start=1
        ):

            message += (
                f"{index}. {path}\n"
            )

        message += (
            "\nPlease select a number."
        )

        return message

    # =================================================
    # OPEN TARGET
    # =================================================

    def _open_target(self, target):

        results = self.resolver.find(target)

        if not results:

            self.selection_manager.clear()

            return (
                f"I could not find "
                f"'{target}'."
            )

        # -------------------------------------------------
        # ONE RESULT
        # -------------------------------------------------

        if len(results) == 1:

            self.selection_manager.clear()

            return self.resolver.open_selected(
                results,
                1
            )

        # -------------------------------------------------
        # MULTIPLE RESULTS
        # -------------------------------------------------

        return self._save_multiple_results(
            target,
            results
        )

    # =================================================
    # SEARCH AND OPEN
    # =================================================

    def _search_and_open(self, target):

        results = self.resolver.find(target)

        if not results:

            self.selection_manager.clear()

            return (
                f"I could not find "
                f"'{target}'."
            )

        # -------------------------------------------------
        # ONE RESULT
        # -------------------------------------------------

        if len(results) == 1:

            self.selection_manager.clear()

            return self.resolver.open_selected(
                results,
                1
            )

        # -------------------------------------------------
        # MULTIPLE RESULTS
        # -------------------------------------------------

        return self._save_multiple_results(
            target,
            results
        )

    # =================================================
    # HANDLE NUMBER SELECTION
    # =================================================

    def _handle_selection(self, number):

        if not self.selection_manager.has_results():

            return (
                "There is no pending selection."
            )

        selected_path = self.selection_manager.get(
            number
        )

        if selected_path is None:

            return (
                "Invalid selection. "
                "Please choose a valid number."
            )

        results = self.selection_manager.results

        result = self.resolver.open_selected(
            results,
            number
        )

        self.selection_manager.clear()

        return result

    # =================================================
    # EXECUTE INTENT
    # =================================================

    def execute(self, intent):

        intent_type = intent.get(
            "intent",
            "unknown"
        )

        target = intent.get(
            "target",
            ""
        ).strip()

        # -------------------------------------------------
        # NUMBER SELECTION
        # -------------------------------------------------

        if (
            intent_type == "unknown"
            and target.isdigit()
        ):

            return self._handle_selection(
                target
            )

        # -------------------------------------------------
        # OPEN APPLICATION / FILE / FOLDER
        # -------------------------------------------------

        if intent_type == "open":

            return self._open_target(
                target
            )

        # -------------------------------------------------
        # OPEN FILE
        # -------------------------------------------------

        if intent_type == "open_file":

            return self._open_target(
                target
            )

        # -------------------------------------------------
        # SEARCH AND OPEN
        # -------------------------------------------------

        if intent_type == "search_and_open_file":

            return self._search_and_open(
                target
            )

        # -------------------------------------------------
        # SEARCH FILE
        # -------------------------------------------------

        if intent_type == "search_file":

            results = self.file_manager.search(
                target
            )

            if not results:

                self.selection_manager.clear()

                return (
                    f"File '{target}' "
                    f"was not found."
                )

            # ONE RESULT

            if len(results) == 1:

                self.selection_manager.clear()

                return results[0]

            # MULTIPLE RESULTS

            return self._save_multiple_results(
                target,
                results
            )

        # -------------------------------------------------
        # CLOSE APPLICATION
        # -------------------------------------------------

        if intent_type == "close_app":

            self.selection_manager.clear()

            return self.process_manager.close_app(
                target
            )

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

        return (
            f"No tool available for "
            f"'{intent_type}'."
        )
