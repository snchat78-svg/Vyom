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


IMPORTANT:

    Application opening and File/Folder opening are kept
    separate so that adding UniversalAppLauncher does not
    break the old file/folder functionality.
"""

import os

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
        # Universal Application Launcher
        # -----------------------------------------------------

        self.app_launcher = UniversalAppLauncher()

        # -----------------------------------------------------
        # Selection memory
        # -----------------------------------------------------

        self.selection_manager = SelectionManager()

        # -----------------------------------------------------
        # IMPORTANT
        #
        # Remember which tool produced the current selection.
        #
        # Possible values:
        #
        #     "app"
        #     "resolver"
        #     "file"
        # -----------------------------------------------------

        self.selection_source = None

    # =========================================================
    # CLEAR SELECTION
    # =========================================================

    def _clear_selection(self):

        self.selection_manager.clear()

        self.selection_source = None

    # =========================================================
    # SAVE MULTIPLE RESULTS
    # =========================================================

    def _save_multiple_results(
        self,
        target,
        results,
        source="resolver"
    ):

        self.selection_manager.save(
            results
        )

        self.selection_source = source

        message = (
            f"Multiple items found for "
            f"'{target}':\n"
        )

        for index, item in enumerate(
            results,
            start=1
        ):

            # -------------------------------------------------
            # Application launcher record
            # -------------------------------------------------

            if isinstance(
                item,
                dict
            ):

                name = str(
                    item.get(
                        "name",
                        ""
                    )
                ).strip()

                path = str(
                    item.get(
                        "path",
                        ""
                    )
                ).strip()

                app_type = str(
                    item.get(
                        "type",
                        ""
                    )
                ).strip()

                if name:

                    if app_type:

                        message += (
                            f"{index}. "
                            f"{name} "
                            f"[{app_type}]\n"
                        )

                    else:

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
            # Normal resolver/file result
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
    # CONVERT RESULT TO MESSAGE
    # =========================================================

    def _result_to_message(
        self,
        result
    ):

        if isinstance(
            result,
            dict
        ):

            return str(
                result.get(
                    "message",
                    result
                )
            )

        return str(
            result
        )

    # =========================================================
    # CHECK WHETHER TARGET LOOKS LIKE FILE/FOLDER
    # =========================================================

    def _looks_like_file_or_folder(
        self,
        target
    ):

        if not target:

            return False

        target = str(
            target
        ).strip()

        if not target:

            return False

        # -----------------------------------------------------
        # Existing path
        # -----------------------------------------------------

        try:

            if os.path.exists(target):

                return True

        except Exception:

            pass

        # -----------------------------------------------------
        # Windows path
        #
        # Examples:
        #
        # C:\Users\...
        # D:\Files\...
        # \\server\folder
        # -----------------------------------------------------

        if (
            len(target) >= 2
            and target[1] == ":"
        ):

            return True

        if target.startswith(
            "\\\\"
        ):

            return True

        # -----------------------------------------------------
        # Common file extensions
        # -----------------------------------------------------

        file_extensions = (
            # Images
            ".jpg",
            ".jpeg",
            ".png",
            ".gif",
            ".bmp",
            ".webp",
            ".tif",
            ".tiff",

            # Documents
            ".pdf",
            ".doc",
            ".docx",
            ".xls",
            ".xlsx",
            ".ppt",
            ".pptx",
            ".txt",
            ".rtf",
            ".csv",

            # Audio
            ".mp3",
            ".wav",
            ".wma",
            ".aac",
            ".m4a",
            ".flac",

            # Video
            ".mp4",
            ".avi",
            ".mkv",
            ".mov",
            ".wmv",
            ".3gp",

            # Archive
            ".zip",
            ".rar",
            ".7z",
            ".tar",
            ".gz",

            # Web
            ".html",
            ".htm",

            # Code
            ".py",
            ".dart",
            ".java",
            ".js",
            ".json",
            ".xml",
            ".css",

            # Windows
            ".exe",
            ".com",
            ".bat",
            ".cmd",
            ".lnk"
        )

        lower_target = target.lower()

        for extension in file_extensions:

            if lower_target.endswith(
                extension
            ):

                return True

        return False

    # =========================================================
    # OPEN USING UNIVERSAL RESOLVER
    #
    # This is the OLD file/folder path.
    #
    # Do not send normal files to Application Launcher.
    # =========================================================

    def _open_resolver_target(
        self,
        target
    ):

        if not target:

            self._clear_selection()

            return (
                "Please tell me what "
                "you want me to open."
            )

        results = self.resolver.find(
            target
        )

        if not results:

            self._clear_selection()

            return (
                f"I could not find "
                f"'{target}'."
            )

        # -----------------------------------------------------
        # ONE FILE / FOLDER / RESOLVER RESULT
        # -----------------------------------------------------

        if len(results) == 1:

            self._clear_selection()

            result = self.resolver.open_selected(
                results,
                1
            )

            return self._result_to_message(
                result
            )

        # -----------------------------------------------------
        # MULTIPLE FILE / FOLDER RESULTS
        # -----------------------------------------------------

        return self._save_multiple_results(
            target,
            results,
            source="resolver"
        )

    # =========================================================
    # OPEN USING APPLICATION LAUNCHER
    # =========================================================

    def _open_application(
        self,
        target
    ):

        if not target:

            self._clear_selection()

            return (
                "Please tell me which "
                "application to open."
            )

        response = self.app_launcher.open(
            target
        )

        # -----------------------------------------------------
        # Normalize launcher response
        # -----------------------------------------------------

        if not isinstance(
            response,
            dict
        ):

            self._clear_selection()

            return str(
                response
            )

        # -----------------------------------------------------
        # SUCCESS
        # -----------------------------------------------------

        if response.get(
            "success",
            False
        ):

            self._clear_selection()

            return response.get(
                "message",
                f"Opened {target}."
            )

        # -----------------------------------------------------
        # MULTIPLE APPLICATIONS
        # -----------------------------------------------------

        results = response.get(
            "results",
            []
        )

        if results:

            return self._save_multiple_results(
                target,
                results,
                source="app"
            )

        # -----------------------------------------------------
        # SUGGESTIONS
        #
        # Convert suggestions into records.
        # -----------------------------------------------------

        suggestions = response.get(
            "suggestions",
            []
        )

        if suggestions:

            suggestion_results = []

            for name in suggestions:

                if not name:

                    continue

                suggestion_results.append(
                    {
                        "name": str(name),
                        "path": "",
                        "app_id": "",
                        "aumid": "",
                        "type": "suggestion"
                    }
                )

            if suggestion_results:

                return self._save_multiple_results(
                    target,
                    suggestion_results,
                    source="app"
                )

        # -----------------------------------------------------
        # Nothing found
        # -----------------------------------------------------

        self._clear_selection()

        return response.get(
            "message",
            f"I could not find '{target}'."
        )

    # =========================================================
    # UNIVERSAL OPEN
    #
    # IMPORTANT:
    #
    # FILE/FOLDER  -> UniversalResolver FIRST
    #
    # APPLICATION   -> UniversalAppLauncher FIRST
    #
    # This prevents JPG/PDF/MP3/FOLDER etc. from being
    # incorrectly treated as applications.
    # =========================================================

    def _open_target(
        self,
        target
    ):

        if not target:

            self._clear_selection()

            return (
                "Please tell me what "
                "you want me to open."
            )

        # =====================================================
        # STEP 1
        #
        # Detect obvious file/folder/path.
        # =====================================================

        if self._looks_like_file_or_folder(
            target
        ):

            return self._open_resolver_target(
                target
            )

        # =====================================================
        # STEP 2
        #
        # Application Launcher
        # =====================================================

        launcher_response = self.app_launcher.open(
            target
        )

        if isinstance(
            launcher_response,
            dict
        ):

            # -------------------------------------------------
            # Application opened
            # -------------------------------------------------

            if launcher_response.get(
                "success",
                False
            ):

                self._clear_selection()

                return launcher_response.get(
                    "message",
                    f"Opened {target}."
                )

            # -------------------------------------------------
            # Multiple applications
            #
            # STOP here.
            #
            # Do not send the same target to resolver.
            # -------------------------------------------------

            if launcher_response.get(
                "results"
            ):

                return self._handle_launcher_response(
                    target,
                    launcher_response
                )

            # -------------------------------------------------
            # Suggestions
            # -------------------------------------------------

            if launcher_response.get(
                "suggestions"
            ):

                return self._handle_launcher_response(
                    target,
                    launcher_response
                )

        # =====================================================
        # STEP 3
        #
        # Application launcher could not find it.
        #
        # Give UniversalResolver a chance.
        #
        # This preserves old behaviour for:
        #
        #     shortcuts
        #     folders
        #     files without extension
        #     shell targets
        # =====================================================

        return self._open_resolver_target(
            target
        )

    # =========================================================
    # HANDLE LAUNCHER RESPONSE
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

        # -----------------------------------------------------
        # Success
        # -----------------------------------------------------

        if response.get(
            "success",
            False
        ):

            self._clear_selection()

            return response.get(
                "message",
                f"Opened {target}."
            )

        # -----------------------------------------------------
        # Multiple application records
        # -----------------------------------------------------

        results = response.get(
            "results",
            []
        )

        if results:

            return self._save_multiple_results(
                target,
                results,
                source="app"
            )

        # -----------------------------------------------------
        # Suggestions
        # -----------------------------------------------------

        suggestions = response.get(
            "suggestions",
            []
        )

        if suggestions:

            suggestion_results = []

            for name in suggestions:

                if not name:

                    continue

                suggestion_results.append(
                    {
                        "name": str(name),
                        "path": "",
                        "app_id": "",
                        "aumid": "",
                        "type": "suggestion"
                    }
                )

            if suggestion_results:

                return self._save_multiple_results(
                    target,
                    suggestion_results,
                    source="app"
                )

        # -----------------------------------------------------
        # Nothing
        # -----------------------------------------------------

        self._clear_selection()

        return response.get(
            "message",
            f"I could not find '{target}'."
        )

    # =========================================================
    # SEARCH AND OPEN
    #
    # File/folder search stays with UniversalResolver.
    # =========================================================

    def _search_and_open(
        self,
        target
    ):

        return self._open_resolver_target(
            target
        )

    # =========================================================
    # HANDLE NUMBER SELECTION
    #
    # VERY IMPORTANT:
    #
    # We use selection_source instead of guessing based on
    # whether the result is a dictionary.
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

        source = self.selection_source

        # =====================================================
        # APPLICATION SELECTION
        # =====================================================

        if source == "app":

            result = self.app_launcher.open_selected(
                results,
                number
            )

            message = self._result_to_message(
                result
            )

            # Clear only after processing
            self._clear_selection()

            return message

        # =====================================================
        # RESOLVER SELECTION
        # =====================================================

        if source == "resolver":

            result = self.resolver.open_selected(
                results,
                number
            )

            message = self._result_to_message(
                result
            )

            self._clear_selection()

            return message

        # =====================================================
        # FILE SELECTION
        #
        # Currently FileManager results are normally returned
        # directly for one result. Multiple file search results
        # are kept compatible with UniversalResolver.
        # =====================================================

        if source == "file":

            result = self.resolver.open_selected(
                results,
                number
            )

            message = self._result_to_message(
                result
            )

            self._clear_selection()

            return message

        # =====================================================
        # SAFETY FALLBACK
        # =====================================================

        # If source somehow disappeared, determine by result
        # type instead of blindly using Application Launcher.

        if isinstance(
            selected,
            dict
        ):

            result = self.app_launcher.open_selected(
                results,
                number
            )

        else:

            result = self.resolver.open_selected(
                results,
                number
            )

        message = self._result_to_message(
            result
        )

        self._clear_selection()

        return message

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
        # Automatically decides:
        #
        # File/Folder -> Resolver
        # Application -> App Launcher
        # =====================================================

        if intent_type == "open":

            return self._open_target(
                target
            )

        # =====================================================
        # OPEN FILE
        #
        # ALWAYS use resolver.
        #
        # This is important for JPG, PNG, PDF, MP3, MP4,
        # DOCX, folders etc.
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

                self._clear_selection()

                return (
                    f"File '{target}' "
                    f"was not found."
                )

            # -------------------------------------------------
            # ONE RESULT
            # -------------------------------------------------

            if len(results) == 1:

                self._clear_selection()

                # Try resolver to actually open the result.
                #
                # If FileManager already returns a path, resolver
                # should preserve normal Windows file opening.

                result = results[0]

                resolver_results = self.resolver.find(
                    str(result)
                )

                if len(resolver_results) == 1:

                    opened = self.resolver.open_selected(
                        resolver_results,
                        1
                    )

                    return self._result_to_message(
                        opened
                    )

                return str(
                    result
                )

            # -------------------------------------------------
            # MULTIPLE RESULTS
            # -------------------------------------------------

            return self._save_multiple_results(
                target,
                results,
                source="file"
            )

        # =====================================================
        # CLOSE APPLICATION
        # =====================================================

        if intent_type == "close_app":

            self._clear_selection()

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
