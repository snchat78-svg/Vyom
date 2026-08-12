"""
Project : Vyom AI
Version : 0.11
Module : Tool Manager

Purpose:
    Connect Vyom intents with:

    - Universal Application Launcher
    - Universal Windows Resolver
    - File Manager
    - Process Manager
    - Selection Memory

Architecture:

    Vyom Intent
        |
        v
    ToolManager
        |
        +---- Application ---> UniversalAppLauncher
        |
        +---- File/Folder ---> UniversalResolver
        |
        +---- File Search ---> FileManager
        |
        +---- Close App ----> ProcessManager
        |
        +---- Selection ----> SelectionManager
"""

from windows_agent.process_manager import ProcessManager

from tools.file_manager import FileManager

from tools.universal_resolver import UniversalResolver

from tools.universal_app_launcher import UniversalAppLauncher

from memory.selection_manager import SelectionManager


class ToolManager:

    # =========================================================
    # INITIALIZATION
    # =========================================================

    def __init__(self):

        # -----------------------------------------------------
        # Existing tools
        # -----------------------------------------------------

        self.process_manager = ProcessManager()

        self.file_manager = FileManager()

        self.resolver = UniversalResolver()

        # -----------------------------------------------------
        # NEW UNIVERSAL APPLICATION LAUNCHER
        # -----------------------------------------------------

        self.app_launcher = UniversalAppLauncher()

        # -----------------------------------------------------
        # Selection memory
        # -----------------------------------------------------

        self.selection_manager = SelectionManager()

    # =========================================================
    # SAVE MULTIPLE RESULTS
    # =========================================================

    def _save_multiple_results(
        self,
        target,
        results
    ):

        self.selection_manager.save(
            results
        )

        message = (
            f"Multiple items found for "
            f"'{target}':\n"
        )

        for index, item in enumerate(
            results,
            start=1
        ):

            # -------------------------------------------------
            # Application launcher result
            # -------------------------------------------------

            if isinstance(
                item,
                dict
            ):

                name = item.get(
                    "name",
                    ""
                )

                path = item.get(
                    "path",
                    ""
                )

                app_type = item.get(
                    "type",
                    ""
                )

                if app_type:

                    message += (
                        f"{index}. "
                        f"{name} "
                        f"[{app_type}]\n"
                    )

                elif name:

                    message += (
                        f"{index}. "
                        f"{name}\n"
                    )

                elif path:

                    message += (
                        f"{index}. "
                        f"{path}\n"
                    )

                else:

                    message += (
                        f"{index}. "
                        f"Unknown item\n"
                    )

            # -------------------------------------------------
            # Existing resolver/file result
            # -------------------------------------------------

            else:

                message += (
                    f"{index}. "
                    f"{item}\n"
                )

        message += (
            "\nPlease select a number."
        )

        return message

    # =========================================================
    # CONVERT APP LAUNCHER RESPONSE TO TOOL MANAGER RESPONSE
    # =========================================================

    def _handle_launcher_response(
        self,
        target,
        response
    ):

        if not isinstance(
            response,
            dict
        ):

            return str(
                response
            )

        success = response.get(
            "success",
            False
        )

        message = response.get(
            "message",
            ""
        )

        results = response.get(
            "results",
            []
        )

        suggestions = response.get(
            "suggestions",
            []
        )

        # -----------------------------------------------------
        # SUCCESS
        # -----------------------------------------------------

        if success:

            self.selection_manager.clear()

            return message

        # -----------------------------------------------------
        # MULTIPLE APPLICATIONS
        # -----------------------------------------------------

        if results:

            return self._save_multiple_results(
                target,
                results
            )

        # -----------------------------------------------------
        # SUGGESTIONS
        #
        # Convert suggestions into application records so
        # numbered selection can still work.
        # -----------------------------------------------------

        if suggestions:

            suggestion_results = []

            for name in suggestions:

                if not name:

                    continue

                suggestion_results.append(
                    {
                        "name": name,
                        "path": "",
                        "app_id": "",
                        "aumid": "",
                        "type": "suggestion"
                    }
                )

            if suggestion_results:

                return self._save_multiple_results(
                    target,
                    suggestion_results
                )

        # -----------------------------------------------------
        # NOTHING FOUND
        # -----------------------------------------------------

        return message

    # =========================================================
    # OPEN USING UNIVERSAL APPLICATION LAUNCHER
    # =========================================================

    def _open_application(
        self,
        target
    ):

        if not target:

            return (
                "Please tell me which "
                "application to open."
            )

        response = self.app_launcher.open(
            target
        )

        return self._handle_launcher_response(
            target,
            response
        )

    # =========================================================
    # OPEN USING UNIVERSAL RESOLVER
    # =========================================================

    def _open_resolver_target(
        self,
        target
    ):

        results = self.resolver.find(
            target
        )

        if not results:

            self.selection_manager.clear()

            return (
                f"I could not find "
                f"'{target}'."
            )

        # -----------------------------------------------------
        # ONE RESULT
        # -----------------------------------------------------

        if len(results) == 1:

            self.selection_manager.clear()

            result = self.resolver.open_selected(
                results,
                1
            )

            return self._result_to_message(
                result
            )

        # -----------------------------------------------------
        # MULTIPLE RESULTS
        # -----------------------------------------------------

        return self._save_multiple_results(
            target,
            results
        )

    # =========================================================
    # UNIVERSAL OPEN
    #
    # Application launcher is tried FIRST.
    #
    # If application launcher cannot find the target,
    # UniversalResolver gets a chance.
    # =========================================================

    def _open_target(
        self,
        target
    ):

        if not target:

            return (
                "Please tell me what "
                "you want me to open."
            )

        # -----------------------------------------------------
        # STEP 1
        # Universal Application Launcher
        # -----------------------------------------------------

        launcher_response = self.app_launcher.open(
            target
        )

        # -----------------------------------------------------
        # Launcher success
        # -----------------------------------------------------

        if (
            isinstance(
                launcher_response,
                dict
            )
            and
            launcher_response.get(
                "success",
                False
            )
        ):

            self.selection_manager.clear()

            return launcher_response.get(
                "message",
                f"Opened {target}."
            )

        # -----------------------------------------------------
        # Launcher found multiple applications
        #
        # IMPORTANT:
        # Do NOT fall through to resolver.
        #
        # User must select the application.
        # -----------------------------------------------------

        if (
            isinstance(
                launcher_response,
                dict
            )
            and
            launcher_response.get(
                "results"
            )
        ):

            return self._handle_launcher_response(
                target,
                launcher_response
            )

        # -----------------------------------------------------
        # Launcher suggestions
        # -----------------------------------------------------

        if (
            isinstance(
                launcher_response,
                dict
            )
            and
            launcher_response.get(
                "suggestions"
            )
        ):

            return self._handle_launcher_response(
                target,
                launcher_response
            )

        # -----------------------------------------------------
        # STEP 2
        # UniversalResolver fallback
        #
        # This preserves the old file/folder/shortcut
        # functionality.
        # -----------------------------------------------------

        return self._open_resolver_target(
            target
        )

    # =========================================================
    # SEARCH AND OPEN
    #
    # This remains file/resolver based.
    # =========================================================

    def _search_and_open(
        self,
        target
    ):

        results = self.resolver.find(
            target
        )

        if not results:

            self.selection_manager.clear()

            return (
                f"I could not find "
                f"'{target}'."
            )

        # -----------------------------------------------------
        # ONE RESULT
        # -----------------------------------------------------

        if len(results) == 1:

            self.selection_manager.clear()

            result = self.resolver.open_selected(
                results,
                1
            )

            return self._result_to_message(
                result
            )

        # -----------------------------------------------------
        # MULTIPLE RESULTS
        # -----------------------------------------------------

        return self._save_multiple_results(
            target,
            results
        )

    # =========================================================
    # HANDLE NUMBER SELECTION
    #
    # Supports:
    #
    # 1. UniversalAppLauncher records
    # 2. UniversalResolver results
    # =========================================================

    def _handle_selection(
        self,
        number
    ):

        if not self.selection_manager.has_results():

            return (
                "There is no pending selection."
            )

        selected = self.selection_manager.get(
            number
        )

        if selected is None:

            return (
                "Invalid selection. "
                "Please choose a valid number."
            )

        results = (
            self.selection_manager.results
        )

        # -----------------------------------------------------
        # Application launcher result
        # -----------------------------------------------------

        if isinstance(
            selected,
            dict
        ):

            result = self.app_launcher.open_selected(
                results,
                number
            )

            success = False

            if isinstance(
                result,
                dict
            ):

                success = result.get(
                    "success",
                    False
                )

            self.selection_manager.clear()

            return self._result_to_message(
                result
            )

        # -----------------------------------------------------
        # UniversalResolver result
        # -----------------------------------------------------

        result = self.resolver.open_selected(
            results,
            number
        )

        self.selection_manager.clear()

        return self._result_to_message(
            result
        )

    # =========================================================
    # RESULT TO MESSAGE
    #
    # Different modules may return:
    #
    # - string
    # - dictionary
    #
    # Keep ToolManager output consistent.
    # =========================================================

    def _result_to_message(
        self,
        result
    ):

        if isinstance(
            result,
            dict
        ):

            return result.get(
                "message",
                str(result)
            )

        return str(
            result
        )

    # =========================================================
    # EXECUTE INTENT
    # =========================================================

    def execute(
        self,
        intent
    ):

        if not isinstance(
            intent,
            dict
        ):

            return (
                "Invalid intent."
            )

        intent_type = intent.get(
            "intent",
            "unknown"
        )

        target = intent.get(
            "target",
            ""
        )

        if target is None:

            target = ""

        target = str(
            target
        ).strip()

        # =====================================================
        # NUMBER SELECTION
        # =====================================================

        if (
            intent_type == "unknown"
            and
            target.isdigit()
        ):

            return self._handle_selection(
                target
            )

        # =====================================================
        # OPEN
        #
        # Application Launcher FIRST
        # UniversalResolver SECOND
        # =====================================================

        if intent_type == "open":

            return self._open_target(
                target
            )

        # =====================================================
        # OPEN FILE
        #
        # Keep old resolver behaviour.
        # =====================================================

        if intent_type == "open_file":

            return self._open_resolver_target(
                target
            )

        # =====================================================
        # SEARCH AND OPEN FILE
        # =====================================================

        if intent_type == "search_and_open_file":

            return self._search_and_open(
                target
            )

        # =====================================================
        # SEARCH FILE
        # =====================================================

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

            # -------------------------------------------------
            # ONE RESULT
            # -------------------------------------------------

            if len(results) == 1:

                self.selection_manager.clear()

                return results[0]

            # -------------------------------------------------
            # MULTIPLE RESULTS
            # -------------------------------------------------

            return self._save_multiple_results(
                target,
                results
            )

        # =====================================================
        # CLOSE APPLICATION
        # =====================================================

        if intent_type == "close_app":

            self.selection_manager.clear()

            result = self.process_manager.close_app(
                target
            )

            return self._result_to_message(
                result
            )

        # =====================================================
        # UNKNOWN COMMAND
        # =====================================================

        if intent_type == "unknown":

            return (
                f"I don't understand the command: "
                f"{target}"
            )

        # =====================================================
        # UNSUPPORTED INTENT
        # =====================================================

        return (
            f"No tool available for "
            f"'{intent_type}'."
            )
