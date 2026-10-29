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

    IMPORTANT FIX:

    Application Launcher is tried first for application names.

    If Application Launcher cannot actually open the target,
    UniversalResolver gets a chance before launcher
    suggestions are displayed.

    This preserves old behaviour for:

        JPG
        JPEG
        PNG
        PDF
        MP3
        WAV
        MP4
        DOC
        DOCX
        XLS
        XLSX
        PPT
        PPTX
        folders
        files without extension
        shortcuts
        normal Windows paths

    while also supporting applications such as:

        Facebook
        Chrome
        WhatsApp
        Notepad
        Calculator
        etc.
"""

import os
import re
import time

from windows_agent.process_manager import ProcessManager
from windows_agent.window_manager import WindowManager
from tools.phonetic_matcher import score_candidate

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
        self.window_manager = WindowManager()

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
                        "display_name",
                        item.get("name", "")
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

            if os.path.exists(
                target
            ):

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
        #
        # All these files must go through UniversalResolver.
        # -----------------------------------------------------

        file_extensions = (

            # -------------------------------------------------
            # Images
            # -------------------------------------------------

            ".jpg",
            ".jpeg",
            ".png",
            ".gif",
            ".bmp",
            ".webp",
            ".tif",
            ".tiff",
            ".ico",
            ".svg",
            ".raw",
            ".heic",
            ".heif",

            # -------------------------------------------------
            # Documents
            # -------------------------------------------------

            ".pdf",
            ".doc",
            ".docx",
            ".docm",
            ".dot",
            ".dotx",
            ".xls",
            ".xlsx",
            ".xlsm",
            ".xlt",
            ".xltx",
            ".ppt",
            ".pptx",
            ".pptm",
            ".pps",
            ".ppsx",
            ".txt",
            ".rtf",
            ".csv",
            ".tsv",
            ".odt",
            ".ods",
            ".odp",
            ".pages",
            ".numbers",
            ".key",

            # -------------------------------------------------
            # Audio
            # -------------------------------------------------

            ".mp3",
            ".wav",
            ".wma",
            ".aac",
            ".m4a",
            ".flac",
            ".ogg",
            ".oga",
            ".opus",
            ".mid",
            ".midi",
            ".aiff",
            ".aif",

            # -------------------------------------------------
            # Video
            # -------------------------------------------------

            ".mp4",
            ".avi",
            ".mkv",
            ".mov",
            ".wmv",
            ".3gp",
            ".mpeg",
            ".mpg",
            ".m4v",
            ".webm",
            ".flv",
            ".ts",
            ".mts",
            ".m2ts",

            # -------------------------------------------------
            # Archives
            # -------------------------------------------------

            ".zip",
            ".rar",
            ".7z",
            ".tar",
            ".gz",
            ".bz2",
            ".xz",
            ".iso",

            # -------------------------------------------------
            # Web
            # -------------------------------------------------

            ".html",
            ".htm",
            ".mht",
            ".mhtml",

            # -------------------------------------------------
            # Code / Text
            # -------------------------------------------------

            ".py",
            ".dart",
            ".java",
            ".js",
            ".ts",
            ".jsx",
            ".tsx",
            ".json",
            ".xml",
            ".css",
            ".scss",
            ".sass",
            ".less",
            ".c",
            ".cpp",
            ".h",
            ".hpp",
            ".cs",
            ".php",
            ".sql",
            ".sh",
            ".yaml",
            ".yml",
            ".ini",
            ".cfg",
            ".log",

            # -------------------------------------------------
            # Windows files
            # -------------------------------------------------

            ".exe",
            ".com",
            ".bat",
            ".cmd",
            ".lnk",
            ".msi",
            ".url"
        )

        lower_target = target.lower()

        for extension in file_extensions:

            if lower_target.endswith(
                extension
            ):

                return True

        return False

    # =========================================================
    # DIRECT WINDOWS OPEN FALLBACK
    #
    # Used only when UniversalResolver has a valid path but
    # cannot open/resolve it correctly.
    #
    # This helps preserve old Windows behaviour for:
    #
    # JPG
    # MP3
    # PDF
    # DOCX
    # MP4
    # folders
    # etc.
    # =========================================================

    def _direct_windows_open(
        self,
        target
    ):

        if not target:

            return None

        try:

            if os.path.exists(
                str(target)
            ):

                os.startfile(
                    str(target)
                )

                return (
                    f"Opened successfully: "
                    f"{target}"
                )

        except Exception as e:

            return (
                f"Error opening "
                f"'{target}': {e}"
            )

        return None

    # =========================================================
    # OPEN USING UNIVERSAL RESOLVER
    #
    # This is the old file/folder path.
    #
    # Files, folders, documents, audio, video and images
    # are handled here.
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

        # -----------------------------------------------------
        # First try UniversalResolver.
        # -----------------------------------------------------

        results = self.resolver.find(
            target
        )

        # -----------------------------------------------------
        # Resolver did not find anything.
        #
        # If target itself is an existing Windows path,
        # use direct Windows opening as fallback.
        # -----------------------------------------------------

        if not results:

            direct_result = self._direct_windows_open(
                target
            )

            if direct_result:

                self._clear_selection()

                return direct_result

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
        # Suggestions are not treated as confirmed apps.
        #
        # IMPORTANT:
        #
        # We do NOT immediately display suggestions here.
        # The universal resolver must get a chance first.
        # -----------------------------------------------------

        suggestions = response.get(
            "suggestions",
            []
        )

        # -----------------------------------------------------
        # Try resolver before showing suggestions.
        #
        # This fixes:
        #
        #     open pic samu
        #
        # where Application Launcher may return:
        #
        #     Pictures
        #     PC Settings
        #     Scan
        #
        # while UniversalResolver can find:
        #
        #     pic samu.jpg
        # -----------------------------------------------------

        file_only_finder = getattr(self.resolver, "find_file_or_folder", None)
        if callable(file_only_finder):
            resolver_results = file_only_finder(target)
        else:
            # Compatibility with resolver adapters created by older callers.
            resolver_results = self.resolver.find(target)

        if resolver_results:

            if len(resolver_results) == 1:

                self._clear_selection()

                result = self.resolver.open_selected(
                    resolver_results,
                    1
                )

                return self._result_to_message(
                    result
                )

            return self._save_multiple_results(
                target,
                resolver_results,
                source="resolver"
            )

        # -----------------------------------------------------
        # Only after resolver fails, show application
        # suggestions.
        # -----------------------------------------------------

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
    # IMPORTANT ORDER:
    #
    # 1. Obvious file/folder/path -> Resolver
    #
    # 2. Application Launcher -> exact application
    #
    # 3. If launcher only gives suggestions -> Resolver
    #
    # 4. If resolver also fails -> show app suggestions
    #
    # This combines the old and new behaviour.
    # =========================================================

    def _foreground_snapshot(self):
        try:
            return self.window_manager.get_foreground() or {}
        except Exception:
            return {}

    @staticmethod
    def _title_segments(title):
        value = str(title or "").strip()
        if not value:
            return []
        pieces = [piece.strip() for piece in re.split(r"\s+(?:-|—|–|\|)\s+", value) if piece.strip()]
        return pieces or [value]

    @staticmethod
    def _same_runtime_target(target, candidate):
        target_text = str(target or "").strip().lower()
        candidate_text = str(candidate or "").strip().lower()
        if not target_text or not candidate_text:
            return False
        if target_text == candidate_text:
            return True
        if target_text in candidate_text or candidate_text in target_text:
            return False
        return score_candidate(target_text, candidate_text) >= 0.80

    def _foreground_matches_target(self, target, window):
        title = str(window.get("title") or "").strip() if isinstance(window, dict) else ""
        return any(self._same_runtime_target(target, segment) for segment in self._title_segments(title))

    def _verify_open_effect(self, target, before, raw_result):
        """Observe the resulting foreground window after a legacy open route."""
        source = raw_result if isinstance(raw_result, dict) else {}
        candidates = [str(target or "").strip()]
        records = source.get("results") if isinstance(source, dict) else None
        if isinstance(records, list):
            for item in records:
                if isinstance(item, dict):
                    name = str(item.get("name") or "").strip()
                    if name and name not in candidates:
                        candidates.append(name)

        before_hwnd = before.get("hwnd") if isinstance(before, dict) else None
        after = {}
        deadline = time.monotonic() + 2.0
        while time.monotonic() < deadline:
            after = self._foreground_snapshot()
            title = str(after.get("title") or "").strip()
            after_hwnd = after.get("hwnd")
            if after_hwnd and title:
                if before_hwnd and after_hwnd != before_hwnd:
                    return True, after, "foreground_window_changed"
                for candidate in candidates:
                    # Match each caption segment so app captions remain discoverable.
                    if candidate and self._foreground_matches_target(candidate, after):
                        return True, after, "foreground_title_match"
            time.sleep(0.15)
        return False, after, "foreground_change_not_observed"

    def _open_result_contract(self, target, before, raw_result):
        if isinstance(raw_result, dict):
            if self.selection_manager.has_results():
                return {
                    "success": False,
                    "status": "needs_selection",
                    "stage": "needs_selection",
                    "message": str(raw_result.get("message") or "कृपया एक विकल्प चुनें।"),
                    "selection_options": list(self.selection_manager.results),
                    "result": raw_result,
                    "verification": {"verified": False, "reason": "Selection is pending."},
                }
            launch_succeeded = bool(raw_result.get("success", False))
        else:
            # Legacy callers return display text. Accept only explicit success
            # wording; a foreground change alone cannot turn "not found" into
            # a successful application launch.
            legacy_message = str(raw_result or "").strip().lower()
            launch_succeeded = legacy_message.startswith((
                "opened successfully",
                "opened windows application",
                "opened ",
            ))

        if self.selection_manager.has_results():
            return {
                "success": False,
                "status": "needs_selection",
                "stage": "needs_selection",
                "message": str(raw_result or "कृपया एक विकल्प चुनें।"),
                "selection_options": list(self.selection_manager.results),
                "result": raw_result,
                "verification": {"verified": False, "reason": "Selection is pending."},
            }

        verified, after, method = self._verify_open_effect(target, before, raw_result)
        success = bool(verified and launch_succeeded)
        if success:
            message = (
                "हाँ, %s खोल दिया है। अब बताइए, आगे क्या करना है।"
                % str((after or {}).get("title") or target).strip()
            )
        else:
            message = (
                "मैंने खोलने का अनुरोध किया, लेकिन स्क्रीन पर उसका खुलना verify नहीं कर पाया। "
                "कृपया देखें कि ऐप खुला है या नहीं।"
            )
        return {
            "success": success,
            "status": "success" if success else "failed",
            "stage": "verified" if success else "launch_unverified",
            "message": message,
            "result": raw_result,
            "verification": {
                "verified": success,
                "verification_level": "foreground_state",
                "method": method,
                "window_before": before or {},
                "window_after": after or {},
            },
        }

    def _open_target(self, target, structured=False):
        # Preserve the established string-returning contract for old callers.
        # The unified executor opts into a structured, observation-backed
        # result so a missing app cannot be reported as a false success.
        if not structured:
            return self._open_target_legacy(target)
        before = self._foreground_snapshot()
        if self._foreground_matches_target(target, before):
            title = str(before.get("title") or target).strip()
            message = "%s is already active; reusing the existing window." % title
            return {
                "success": True,
                "status": "success",
                "stage": "verified",
                "message": message,
                "result": {"success": True, "reused_existing_window": True, "message": message},
                "verification": {
                    "verified": True,
                    "verification_level": "foreground_state",
                    "method": "existing_foreground_match",
                    "window_before": before,
                    "window_after": before,
                },
            }
        raw_result = self._open_target_legacy(target)
        return self._open_result_contract(target, before, raw_result)

    def _open_target_legacy(
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
        #
        # This allows:
        #
        #     Facebook
        #     Chrome
        #     WhatsApp
        #     Notepad
        #     Calculator
        #
        # to open normally.
        # =====================================================

        launcher_response = self.app_launcher.open(
            target
        )

        # -----------------------------------------------------
        # Non-dictionary response
        # -----------------------------------------------------

        if not isinstance(
            launcher_response,
            dict
        ):

            # -------------------------------------------------
            # Even if launcher returns a text response,
            # preserve old resolver behaviour.
            # -------------------------------------------------

            resolver_result = self._open_resolver_target(
                target
            )

            return resolver_result

        # =====================================================
        # APPLICATION OPENED SUCCESSFULLY
        # =====================================================

        if launcher_response.get(
            "success",
            False
        ):

            self._clear_selection()

            return launcher_response.get(
                "message",
                f"Opened {target}."
            )

        # =====================================================
        # STEP 3
        #
        # APPLICATION LAUNCHER FOUND MULTIPLE REAL
        # APPLICATION RECORDS
        #
        # These are actual application records, not merely
        # suggestions.
        # =====================================================

        application_results = launcher_response.get(
            "results",
            []
        )

        if application_results:

            return self._handle_launcher_response(
                target,
                launcher_response
            )

        # =====================================================
        # STEP 4
        #
        # LAUNCHER FAILED OR ONLY RETURNED SUGGESTIONS
        #
        # IMPORTANT FIX:
        #
        # DO NOT STOP HERE.
        #
        # Give the old UniversalResolver a chance.
        #
        # This is what fixes:
        #
        #     open pic samu
        #     open my song
        #     open my document
        #     open pictures
        #     open folder name
        #
        # when the target has no extension.
        # =====================================================

        resolver_results = self.resolver.find(
            target
        )

        if resolver_results:

            # -------------------------------------------------
            # ONE RESOLVER RESULT
            # -------------------------------------------------

            if len(resolver_results) == 1:

                self._clear_selection()

                result = self.resolver.open_selected(
                    resolver_results,
                    1
                )

                return self._result_to_message(
                    result
                )

            # -------------------------------------------------
            # MULTIPLE RESOLVER RESULTS
            # -------------------------------------------------

            return self._save_multiple_results(
                target,
                resolver_results,
                source="resolver"
            )

        # =====================================================
        # STEP 5
        #
        # ONLY NOW DISPLAY APPLICATION SUGGESTIONS.
        #
        # Example:
        #
        #     open calc
        #
        # if exact application wasn't found but launcher
        # has useful suggestions.
        # =====================================================

        suggestions = launcher_response.get(
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

        # =====================================================
        # STEP 6
        #
        # FINAL FALLBACK
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
        #
        # IMPORTANT:
        #
        # Suggestions alone do not prove that the target is
        # an application.
        #
        # Therefore try UniversalResolver first.
        # -----------------------------------------------------

        suggestions = response.get(
            "suggestions",
            []
        )

        resolver_results = self.resolver.find(
            target
        )

        if resolver_results:

            if len(resolver_results) == 1:

                self._clear_selection()

                result = self.resolver.open_selected(
                    resolver_results,
                    1
                )

                return self._result_to_message(
                    result
                )

            return self._save_multiple_results(
                target,
                resolver_results,
                source="resolver"
            )

        # -----------------------------------------------------
        # Resolver also failed.
        #
        # Now convert suggestions into selectable records.
        # -----------------------------------------------------

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
    # IMPORTANT:
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
        # FileManager results are normally paths.
        #
        # UniversalResolver remains responsible for opening
        # them so existing behaviour is preserved.
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
        intent,
        structured=False,
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
        # File/Folder/Media/Document -> Resolver
        # Application -> App Launcher
        # =====================================================

        if intent_type == "open":

            return self._open_target(
                target,
                structured=structured,
            )

        # =====================================================
        # OPEN FILE
        #
        # ALWAYS use resolver.
        #
        # Supports:
        #
        # JPG
        # PNG
        # PDF
        # MP3
        # MP4
        # DOCX
        # XLSX
        # PPTX
        # folders
        # etc.
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

                result = results[0]

                # -------------------------------------------------
                # First try UniversalResolver.
                # -------------------------------------------------

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

                # -------------------------------------------------
                # Direct Windows fallback
                #
                # If UniversalResolver does not recognize a
                # valid FileManager path, open it directly.
                #
                # This keeps:
                #
                # MP3
                # PDF
                # DOCX
                # JPG
                # PNG
                # MP4
                # etc.
                #
                # working.
                # -------------------------------------------------

                direct_result = self._direct_windows_open(
                    str(result)
                )

                if direct_result:

                    return direct_result

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
