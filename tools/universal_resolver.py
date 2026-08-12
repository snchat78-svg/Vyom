"""
Project : Vyom AI
Version : 0.9
Module : Universal Windows Resolver

Purpose:
    Find and open Windows applications, files, folders,
    Start Menu applications and Windows Apps without
    manually registering every application.

Designed for:
    Windows 8 / 8.1 / 10 / 11

Features:
    - Normal EXE applications
    - Start Menu .LNK shortcuts
    - Windows Store / Modern Apps
    - AppsFolder
    - AppID / AUMID based launching
    - Program Files scanning
    - PATH applications
    - Common files/folders
    - Duplicate result handling
    - Similar-name / spelling suggestions
    - Numbered selection
"""

import os
import shutil
import subprocess
import difflib
import ctypes


class UniversalResolver:

    def __init__(self):

        # -------------------------------------------------
        # START MENU LOCATIONS
        # -------------------------------------------------

        self.start_menu_paths = [
            os.path.join(
                os.environ.get("APPDATA", ""),
                "Microsoft",
                "Windows",
                "Start Menu",
                "Programs"
            ),

            os.path.join(
                os.environ.get("PROGRAMDATA", ""),
                "Microsoft",
                "Windows",
                "Start Menu",
                "Programs"
            )
        ]

        # -------------------------------------------------
        # COMMON USER LOCATIONS
        # -------------------------------------------------

        user_profile = os.environ.get(
            "USERPROFILE",
            ""
        )

        self.common_paths = [
            os.path.join(
                user_profile,
                "Desktop"
            ),

            os.path.join(
                user_profile,
                "Documents"
            ),

            os.path.join(
                user_profile,
                "Downloads"
            ),

            os.path.join(
                user_profile,
                "Pictures"
            ),

            os.path.join(
                user_profile,
                "Videos"
            ),

            os.path.join(
                user_profile,
                "Music"
            )
        ]

        # -------------------------------------------------
        # PROGRAM FILE LOCATIONS
        # -------------------------------------------------

        self.program_paths = []

        program_files = os.environ.get(
            "ProgramFiles",
            ""
        )

        program_files_x86 = os.environ.get(
            "ProgramFiles(x86)",
            ""
        )

        program_data = os.environ.get(
            "ProgramData",
            ""
        )

        if program_files:
            self.program_paths.append(
                program_files
            )

        if program_files_x86:
            self.program_paths.append(
                program_files_x86
            )

        # -------------------------------------------------
        # COMMON FILE EXTENSIONS
        # -------------------------------------------------

        self.file_extensions = [
            ".txt",
            ".pdf",
            ".doc",
            ".docx",
            ".xls",
            ".xlsx",
            ".csv",
            ".ppt",
            ".pptx",
            ".jpg",
            ".jpeg",
            ".png",
            ".gif",
            ".bmp",
            ".webp",
            ".mp3",
            ".wav",
            ".mp4",
            ".avi",
            ".mkv",
            ".zip",
            ".rar",
            ".7z"
        ]

        # -------------------------------------------------
        # APPLICATION EXTENSIONS
        # -------------------------------------------------

        self.application_extensions = [
            ".exe",
            ".com",
            ".bat",
            ".cmd",
            ".lnk"
        ]

        # -------------------------------------------------
        # MAXIMUM RESULTS
        # -------------------------------------------------

        self.max_results = 20

    # =================================================
    # NORMALIZE NAME
    # =================================================

    def normalize(self, name):

        name = str(name)

        name = name.strip()
        name = name.strip('"')
        name = name.strip("'")
        name = name.lower()

        if name.endswith(".exe"):

            name = name[:-4]

        return name.strip()

    # =================================================
    # CLEAN TARGET
    # =================================================

    def clean_target(self, target):

        if target is None:

            return ""

        target = str(target)

        target = target.strip()
        target = target.strip('"')
        target = target.strip("'")

        return target.strip()

    # =================================================
    # OPEN PATH
    #
    # Strong launcher for normal files/folders/LNK/EXE.
    # =================================================

    def _open(self, path):

        try:

            if not path:

                return (
                    False,
                    "Invalid path."
                )

            # -----------------------------------------
            # Windows AppsFolder path
            # -----------------------------------------

            if isinstance(path, str):

                if path.lower().startswith(
                    "shell:appsfolder\\"
                ):

                    success = (
                        self._launch_appsfolder_path(
                            path
                        )
                    )

                    if success:

                        return (
                            True,
                            f"Opened successfully: {path}"
                        )

            # -----------------------------------------
            # Normal existing path
            # -----------------------------------------

            if not os.path.exists(path):

                return (
                    False,
                    f"Path does not exist: {path}"
                )

            # -----------------------------------------
            # METHOD 1:
            # os.startfile
            # -----------------------------------------

            try:

                os.startfile(path)

                return (
                    True,
                    f"Opened successfully: {path}"
                )

            except Exception:

                pass

            # -----------------------------------------
            # METHOD 2:
            # Windows ShellExecute
            # -----------------------------------------

            try:

                result = ctypes.windll.shell32.ShellExecuteW(
                    None,
                    "open",
                    path,
                    None,
                    None,
                    1
                )

                # ShellExecute returns > 32 on success
                if result > 32:

                    return (
                        True,
                        f"Opened successfully: {path}"
                    )

            except Exception:

                pass

            # -----------------------------------------
            # METHOD 3:
            # CMD START
            # -----------------------------------------

            try:

                subprocess.Popen(
                    [
                        "cmd.exe",
                        "/c",
                        "start",
                        "",
                        path
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )

                return (
                    True,
                    f"Opened successfully: {path}"
                )

            except Exception:

                pass

        except Exception as e:

            return (
                False,
                f"Error opening '{path}': {e}"
            )

        return (
            False,
            f"Could not open: {path}"
        )

    # =================================================
    # LAUNCH APPSFOLDER PATH
    # =================================================

    def _launch_appsfolder_path(
        self,
        app_path
    ):

        if not app_path:

            return False

        # -------------------------------------------------
        # METHOD 1:
        # explorer.exe
        # -------------------------------------------------

        try:

            process = subprocess.Popen(
                [
                    "explorer.exe",
                    app_path
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

            if process is not None:

                return True

        except Exception:

            pass

        # -------------------------------------------------
        # METHOD 2:
        # ShellExecute
        # -------------------------------------------------

        try:

            result = ctypes.windll.shell32.ShellExecuteW(
                None,
                "open",
                "explorer.exe",
                app_path,
                None,
                1
            )

            if result > 32:

                return True

        except Exception:

            pass

        return False

    # =================================================
    # EXACT PATH
    # =================================================

    def find_exact_path(self, target):

        target = self.clean_target(target)

        if not target:

            return None

        if os.path.exists(target):

            return target

        return None

    # =================================================
    # WINDOWS PATH / EXE
    # =================================================

    def find_in_path(self, target):

        name = self.normalize(target)

        if not name:

            return None

        # -----------------------------------------
        # Direct PATH lookup
        # -----------------------------------------

        result = shutil.which(name)

        if result:

            return result

        # -----------------------------------------
        # EXE
        # -----------------------------------------

        result = shutil.which(
            name + ".exe"
        )

        if result:

            return result

        return None

    # =================================================
    # START MENU SEARCH
    # =================================================

    def search_start_menu(self, target):

        target_name = self.normalize(target)

        if not target_name:

            return []

        results = []

        for start_path in self.start_menu_paths:

            if not os.path.exists(start_path):

                continue

            try:

                for root, dirs, files in os.walk(
                    start_path
                ):

                    for file in files:

                        lower_file = file.lower()

                        if not (
                            lower_file.endswith(".lnk")
                            or
                            lower_file.endswith(".exe")
                            or
                            lower_file.endswith(".bat")
                            or
                            lower_file.endswith(".cmd")
                        ):

                            continue

                        filename = os.path.splitext(
                            file
                        )[0].strip().lower()

                        full_path = os.path.join(
                            root,
                            file
                        )

                        # ---------------------------------
                        # Exact
                        # ---------------------------------

                        if filename == target_name:

                            if full_path not in results:

                                results.insert(
                                    0,
                                    full_path
                                )

                        # ---------------------------------
                        # Partial
                        # ---------------------------------

                        elif target_name in filename:

                            if full_path not in results:

                                results.append(
                                    full_path
                                )

            except (
                PermissionError,
                OSError
            ):

                continue

        return results[:self.max_results]

    # =================================================
    # GET WINDOWS START APPS
    #
    # Uses Get-StartApps where available.
    # =================================================

    def get_start_apps(self):

        script = r'''
$ErrorActionPreference = "SilentlyContinue"

try {

    if (Get-Command Get-StartApps -ErrorAction SilentlyContinue) {

        Get-StartApps |
        ForEach-Object {

            if ($_.Name -and $_.AppID) {

                Write-Output (
                    $_.Name + "`t" + $_.AppID
                )
            }
        }
    }

}
catch {

}
'''

        try:

            process = subprocess.Popen(
                [
                    "powershell.exe",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-Command",
                    script
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )

            stdout, stderr = process.communicate(
                timeout=20
            )

            apps = []

            for line in stdout.splitlines():

                line = line.strip()

                if not line:

                    continue

                parts = line.split(
                    "\t",
                    1
                )

                if len(parts) != 2:

                    continue

                name = parts[0].strip()
                app_id = parts[1].strip()

                if not name or not app_id:

                    continue

                apps.append(
                    {
                        "name": name,
                        "app_id": app_id,
                        "path": (
                            "shell:AppsFolder\\"
                            + app_id
                        )
                    }
                )

            return apps

        except (
            subprocess.TimeoutExpired,
            OSError,
            Exception
        ):

            return []

    # =================================================
    # APPSFOLDER COM SCAN
    #
    # IMPORTANT FOR WINDOWS 8 / 8.1
    #
    # Finds Store / Modern apps dynamically.
    # =================================================

    def get_appsfolder_apps(self):

        script = r'''
$ErrorActionPreference = "SilentlyContinue"

try {

    $shell = New-Object -ComObject Shell.Application

    $folder = $shell.Namespace(
        "shell:AppsFolder"
    )

    if ($folder -ne $null) {

        foreach ($item in $folder.Items()) {

            $name = $item.Name
            $path = $item.Path

            if ($name -and $path) {

                Write-Output (
                    $name + "`t" + $path
                )
            }
        }
    }

}
catch {

}
'''

        try:

            process = subprocess.Popen(
                [
                    "powershell.exe",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-Command",
                    script
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )

            stdout, stderr = process.communicate(
                timeout=25
            )

            apps = []

            for line in stdout.splitlines():

                line = line.strip()

                if not line:

                    continue

                parts = line.split(
                    "\t",
                    1
                )

                if len(parts) != 2:

                    continue

                name = parts[0].strip()
                path = parts[1].strip()

                if not name or not path:

                    continue

                apps.append(
                    {
                        "name": name,
                        "app_id": "",
                        "path": path
                    }
                )

            return apps

        except (
            subprocess.TimeoutExpired,
            OSError,
            Exception
        ):

            return []

    # =================================================
    # SEARCH WINDOWS APPS
    #
    # Combines:
    #   1. Get-StartApps
    #   2. AppsFolder COM
    #
    # No hard-coded app names.
    # =================================================

    def search_windows_apps(self, target):

        target_name = self.normalize(target)

        if not target_name:

            return []

        all_apps = []

        # -------------------------------------------------
        # FIRST: Get-StartApps
        # -------------------------------------------------

        start_apps = self.get_start_apps()

        for app in start_apps:

            exists = False

            for existing in all_apps:

                if (
                    existing["name"].lower()
                    == app["name"].lower()
                    and
                    existing["path"].lower()
                    == app["path"].lower()
                ):

                    exists = True
                    break

            if not exists:

                all_apps.append(app)

        # -------------------------------------------------
        # SECOND: AppsFolder
        # -------------------------------------------------

        appsfolder_apps = (
            self.get_appsfolder_apps()
        )

        for app in appsfolder_apps:

            exists = False

            for existing in all_apps:

                if (
                    existing["name"].lower()
                    == app["name"].lower()
                ):

                    exists = True
                    break

            if not exists:

                all_apps.append(app)

        # -------------------------------------------------
        # MATCHING
        # -------------------------------------------------

        exact = []
        partial = []

        for app in all_apps:

            app_name = self.normalize(
                app["name"]
            )

            if not app_name:

                continue

            # Exact
            if app_name == target_name:

                exact.append(app)

            # Partial
            elif target_name in app_name:

                partial.append(app)

        # -------------------------------------------------
        # Exact results first
        # -------------------------------------------------

        results = []

        for app in exact + partial:

            duplicate = False

            for existing in results:

                if (
                    existing["name"].lower()
                    == app["name"].lower()
                    and
                    existing["path"].lower()
                    == app["path"].lower()
                ):

                    duplicate = True
                    break

            if not duplicate:

                results.append(app)

        return results[:self.max_results]

    # =================================================
    # OPEN WINDOWS APP BY PATH
    # =================================================

    def open_windows_app_by_path(
        self,
        app_path
    ):

        if not app_path:

            return (
                False,
                "Invalid Windows app path."
            )

        # -------------------------------------------------
        # AppsFolder path
        # -------------------------------------------------

        if app_path.lower().startswith(
            "shell:appsfolder\\"
        ):

            if self._launch_appsfolder_path(
                app_path
            ):

                return (
                    True,
                    f"Opened successfully: {app_path}"
                )

        # -------------------------------------------------
        # Normal application path
        # -------------------------------------------------

        success, message = self._open(
            app_path
        )

        return (
            success,
            message
        )

    # =================================================
    # OPEN WINDOWS APP
    # =================================================

    def open_windows_app(self, target):

        results = self.search_windows_apps(
            target
        )

        if not results:

            return None

        # -------------------------------------------------
        # EXACT / ONE APP
        # -------------------------------------------------

        if len(results) == 1:

            app = results[0]

            success, message = (
                self.open_windows_app_by_path(
                    app["path"]
                )
            )

            if success:

                return (
                    True,
                    f"Opened Windows app: "
                    f"{app['name']}"
                )

            return (
                False,
                message
            )

        # -------------------------------------------------
        # MULTIPLE APPS
        # -------------------------------------------------

        message = (
            f"Multiple Windows apps found "
            f"for '{target}':\n"
        )

        for index, app in enumerate(
            results,
            start=1
        ):

            message += (
                f"{index}. "
                f"{app['name']}\n"
            )

        message += (
            "\nPlease select a number."
        )

        return (
            False,
            message,
            results
        )

    # =================================================
    # COMMON FILE / FOLDER SEARCH
    # =================================================

    def search_common_locations(
        self,
        target
    ):

        target_original = (
            self.clean_target(
                target
            ).lower()
        )

        target_name = self.normalize(
            target_original
        )

        if not target_original:

            return []

        results = []

        for base_path in self.common_paths:

            if not os.path.exists(
                base_path
            ):

                continue

            try:

                for root, dirs, files in os.walk(
                    base_path,
                    onerror=lambda error: None
                ):

                    # ---------------------------------
                    # FOLDERS
                    # ---------------------------------

                    for directory in dirs:

                        directory_lower = (
                            directory.lower()
                        )

                        if (
                            directory_lower
                            == target_original
                        ):

                            full_path = os.path.join(
                                root,
                                directory
                            )

                            if full_path not in results:

                                results.insert(
                                    0,
                                    full_path
                                )

                        elif (
                            target_name
                            and
                            target_name
                            in directory_lower
                        ):

                            full_path = os.path.join(
                                root,
                                directory
                            )

                            if full_path not in results:

                                results.append(
                                    full_path
                                )

                    # ---------------------------------
                    # FILES
                    # ---------------------------------

                    for file in files:

                        file_lower = file.lower()

                        filename_without_ext = (
                            os.path.splitext(
                                file_lower
                            )[0]
                        )

                        full_path = os.path.join(
                            root,
                            file
                        )

                        # Exact filename
                        if (
                            file_lower
                            == target_original
                        ):

                            if full_path not in results:

                                results.insert(
                                    0,
                                    full_path
                                )

                        # Filename without extension
                        elif (
                            filename_without_ext
                            == target_name
                        ):

                            if full_path not in results:

                                results.append(
                                    full_path
                                )

                        # Partial filename
                        elif (
                            target_name
                            and
                            target_name
                            in filename_without_ext
                        ):

                            if full_path not in results:

                                results.append(
                                    full_path
                                )

                    if len(results) >= self.max_results:

                        return results[
                            :self.max_results
                        ]

            except (
                PermissionError,
                OSError
            ):

                continue

        return results[
            :self.max_results
        ]

    # =================================================
    # PROGRAM FILES SEARCH
    #
    # Finds applications installed outside PATH.
    # =================================================

    def search_program_files(
        self,
        target
    ):

        target_name = self.normalize(
            target
        )

        if not target_name:

            return []

        results = []

        for base_path in self.program_paths:

            if not os.path.exists(
                base_path
            ):

                continue

            try:

                for root, dirs, files in os.walk(
                    base_path,
                    onerror=lambda error: None
                ):

                    # ---------------------------------
                    # Limit excessive recursion
                    # ---------------------------------

                    # Remove obvious cache/temp folders
                    dirs[:] = [
                        d
                        for d in dirs
                        if d.lower()
                        not in (
                            "cache",
                            "temp",
                            "__pycache__"
                        )
                    ]

                    for file in files:

                        lower_file = file.lower()

                        if not lower_file.endswith(
                            ".exe"
                        ):

                            continue

                        filename = os.path.splitext(
                            lower_file
                        )[0]

                        full_path = os.path.join(
                            root,
                            file
                        )

                        # Exact
                        if filename == target_name:

                            if full_path not in results:

                                results.insert(
                                    0,
                                    full_path
                                )

                        # Partial
                        elif target_name in filename:

                            if full_path not in results:

                                results.append(
                                    full_path
                                )

                    if len(results) >= self.max_results:

                        return results[
                            :self.max_results
                        ]

            except (
                PermissionError,
                OSError
            ):

                continue

        return results[
            :self.max_results
        ]

    # =================================================
    # FIND EVERYTHING
    # =================================================

    def find(self, target):

        target = self.clean_target(
            target
        )

        if not target:

            return []

        results = []

        # -------------------------------------------------
        # 1. EXACT PATH
        # -------------------------------------------------

        exact = self.find_exact_path(
            target
        )

        if exact:

            return [exact]

        # -------------------------------------------------
        # 2. NORMAL WINDOWS PATH / PATH ENVIRONMENT
        # -------------------------------------------------

        path_result = self.find_in_path(
            target
        )

        if path_result:

            results.append(
                path_result
            )

        # -------------------------------------------------
        # 3. START MENU .LNK / .EXE
        # -------------------------------------------------

        start_results = (
            self.search_start_menu(
                target
            )
        )

        for item in start_results:

            if item not in results:

                results.append(item)

        # -------------------------------------------------
        # 4. PROGRAM FILES
        # -------------------------------------------------

        program_results = (
            self.search_program_files(
                target
            )
        )

        for item in program_results:

            if item not in results:

                results.append(item)

        # -------------------------------------------------
        # 5. COMMON FILES / FOLDERS
        # -------------------------------------------------

        common_results = (
            self.search_common_locations(
                target
            )
        )

        for item in common_results:

            if item not in results:

                results.append(item)

        return results[
            :self.max_results
        ]

    # =================================================
    # BUILD SEARCH CANDIDATES
    #
    # Used for spelling errors / suggestions.
    # =================================================

    def get_all_search_names(self):

        names = []

        # -------------------------------------------------
        # Start Menu
        # -------------------------------------------------

        for start_path in self.start_menu_paths:

            if not os.path.exists(start_path):

                continue

            try:

                for root, dirs, files in os.walk(
                    start_path
                ):

                    for file in files:

                        lower_file = file.lower()

                        if lower_file.endswith(
                            (
                                ".lnk",
                                ".exe",
                                ".bat",
                                ".cmd"
                            )
                        ):

                            name = os.path.splitext(
                                file
                            )[0].strip()

                            if name:

                                names.append(
                                    name
                                )

            except (
                PermissionError,
                OSError
            ):

                continue

        # -------------------------------------------------
        # Windows Apps
        # -------------------------------------------------

        start_apps = self.get_start_apps()

        for app in start_apps:

            if app.get("name"):

                names.append(
                    app["name"]
                )

        # -------------------------------------------------
        # AppsFolder
        # -------------------------------------------------

        appsfolder_apps = (
            self.get_appsfolder_apps()
        )

        for app in appsfolder_apps:

            if app.get("name"):

                names.append(
                    app["name"]
                )

        # -------------------------------------------------
        # Remove duplicates
        # -------------------------------------------------

        unique = []

        seen = set()

        for name in names:

            key = name.lower().strip()

            if key not in seen:

                seen.add(key)

                unique.append(name)

        return unique

    # =================================================
    # SIMILAR NAME SUGGESTIONS
    # =================================================

    def find_similar(
        self,
        target,
        limit=8
    ):

        target_clean = self.clean_target(
            target
        )

        target_name = self.normalize(
            target_clean
        )

        if not target_name:

            return []

        names = self.get_all_search_names()

        normalized_map = {}

        for name in names:

            normalized = self.normalize(
                name
            )

            if normalized:

                if normalized not in normalized_map:

                    normalized_map[
                        normalized
                    ] = name

        candidates = list(
            normalized_map.keys()
        )

        # -------------------------------------------------
        # difflib fuzzy matching
        # -------------------------------------------------

        matches = difflib.get_close_matches(
            target_name,
            candidates,
            n=limit,
            cutoff=0.35
        )

        results = []

        for match in matches:

            display_name = (
                normalized_map.get(
                    match,
                    match
                )
            )

            if display_name not in results:

                results.append(
                    display_name
                )

        return results

    # =================================================
    # SUGGESTION MESSAGE
    # =================================================

    def suggestion_message(
        self,
        target,
        suggestions
    ):

        if not suggestions:

            return (
                f"I could not find "
                f"'{target}'."
            )

        message = (
            f"I could not find "
            f"'{target}'.\n\n"
            f"Did you mean:\n"
        )

        for index, name in enumerate(
            suggestions,
            start=1
        ):

            message += (
                f"{index}. {name}\n"
            )

        message += (
            "\nPlease select a number."
        )

        return message

    # =================================================
    # OPEN
    # =================================================

    def open(self, target):

        target = self.clean_target(
            target
        )

        if not target:

            return (
                "Please tell me what "
                "you want to open."
            )

        # -------------------------------------------------
        # 1. WINDOWS APPS FIRST
        #
        # This is important for:
        # Camera
        # Weather
        # Money
        # Maps
        # Mail
        # Calendar
        # etc.
        #
        # We do this BEFORE normal Start Menu search
        # so Store/Modern Apps get their real AppID.
        # -------------------------------------------------

        windows_app_result = (
            self.open_windows_app(
                target
            )
        )

        if windows_app_result:

            if len(
                windows_app_result
            ) == 2:

                success, message = (
                    windows_app_result
                )

                if success:

                    return message

            elif len(
                windows_app_result
            ) == 3:

                success, message, app_results = (
                    windows_app_result
                )

                return message

        # -------------------------------------------------
        # 2. NORMAL FILE / FOLDER / EXE / LNK
        # -------------------------------------------------

        results = self.find(
            target
        )

        # -------------------------------------------------
        # EXACT / ONE RESULT
        # -------------------------------------------------

        if len(results) == 1:

            success, message = self._open(
                results[0]
            )

            if success:

                return message

        # -------------------------------------------------
        # MULTIPLE NORMAL RESULTS
        # -------------------------------------------------

        if len(results) > 1:

            message = (
                f"Multiple items found for "
                f"'{target}':\n"
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

        # -------------------------------------------------
        # 3. SIMILAR SPELLING
        # -------------------------------------------------

        suggestions = (
            self.find_similar(
                target
            )
        )

        return self.suggestion_message(
            target,
            suggestions
        )

    # =================================================
    # SEARCH AND OPEN
    # =================================================

    def search_and_open(
        self,
        target
    ):

        return self.open(
            target
        )

    # =================================================
    # OPEN SELECTED RESULT
    #
    # Supports:
    #   Normal paths
    #   Windows Apps
    #   Dictionaries
    # =================================================

    def open_selected(
        self,
        results,
        number
    ):

        try:

            index = int(
                number
            ) - 1

        except (
            ValueError,
            TypeError
        ):

            return (
                "Please enter a valid number."
            )

        if (
            index < 0
            or
            index >= len(results)
        ):

            return (
                "Invalid selection."
            )

        selected = results[
            index
        ]

        # -------------------------------------------------
        # Windows App dictionary
        # -------------------------------------------------

        if isinstance(
            selected,
            dict
        ):

            app_path = selected.get(
                "path"
            )

            app_name = selected.get(
                "name",
                "Windows app"
            )

            success, message = (
                self.open_windows_app_by_path(
                    app_path
                )
            )

            if success:

                return (
                    f"Opened Windows app: "
                    f"{app_name}"
                )

            return message

        # -------------------------------------------------
        # Normal path
        # -------------------------------------------------

        success, message = self._open(
            selected
        )

        return message

    # =================================================
    # OPEN SUGGESTION
    #
    # If user selects a spelling suggestion,
    # Vyom searches again using that real name.
    # =================================================

    def open_suggestion(
        self,
        suggestions,
        number
    ):

        try:

            index = int(
                number
            ) - 1

        except (
            ValueError,
            TypeError
        ):

            return (
                "Please enter a valid number."
            )

        if (
            index < 0
            or
            index >= len(suggestions)
        ):

            return (
                "Invalid selection."
            )

        selected_name = suggestions[
            index
        ]

        return self.open(
            selected_name
        )
