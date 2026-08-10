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
"""

import os
import shutil
import subprocess


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
    # OPEN PATH
    # =================================================

    def _open(self, path):

        try:

            os.startfile(path)

            return (
                True,
                f"Opened successfully: {path}"
            )

        except Exception as e:

            return (
                False,
                f"Error opening '{path}': {e}"
            )

    # =================================================
    # EXACT PATH
    # =================================================

    def find_exact_path(self, target):

        target = target.strip()
        target = target.strip('"')
        target = target.strip("'")

        if os.path.exists(target):

            return target

        return None

    # =================================================
    # WINDOWS PATH / EXE
    # =================================================

    def find_in_path(self, target):

        name = self.normalize(target)

        result = shutil.which(name)

        if result:

            return result

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
                            or lower_file.endswith(".exe")
                        ):

                            continue

                        filename = os.path.splitext(
                            file
                        )[0].strip().lower()

                        # Exact match first
                        if filename == target_name:

                            full_path = os.path.join(
                                root,
                                file
                            )

                            if full_path not in results:

                                results.insert(
                                    0,
                                    full_path
                                )

                        # Partial match
                        elif target_name in filename:

                            full_path = os.path.join(
                                root,
                                file
                            )

                            if full_path not in results:

                                results.append(
                                    full_path
                                )

            except (
                PermissionError,
                OSError
            ):

                continue

        return results

    # =================================================
    # WINDOWS APPSFOLDER SEARCH
    #
    # This is for Windows built-in / Store apps
    # such as Maps, Camera, Calendar, Bing etc.
    # =================================================

    def search_windows_apps(self, target):

        target_name = self.normalize(target)

        if not target_name:

            return []

        results = []

        # -------------------------------------------------
        # PowerShell script
        #
        # Uses Windows Shell AppsFolder.
        # This avoids manually registering every app.
        # -------------------------------------------------

        script = r'''
$shell = New-Object -ComObject Shell.Application
$folder = $shell.Namespace("shell:AppsFolder")

if ($folder -ne $null) {

    foreach ($item in $folder.Items()) {

        $name = $item.Name

        if ($name -ne $null) {

            Write-Output $name
        }
    }
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
                timeout=15
            )

            if process.returncode != 0:

                return []

            for line in stdout.splitlines():

                app_name = line.strip()

                if not app_name:

                    continue

                app_normalized = (
                    app_name.lower().strip()
                )

                # Exact match
                if app_normalized == target_name:

                    results.insert(
                        0,
                        app_name
                    )

                # Partial match
                elif target_name in app_normalized:

                    if app_name not in results:

                        results.append(
                            app_name
                        )

        except (
            subprocess.TimeoutExpired,
            OSError,
            Exception
        ):

            return []

        return results[:20]

    # =================================================
    # OPEN WINDOWS APP
    # =================================================

    def open_windows_app(self, target):

        target_name = self.normalize(target)

        if not target_name:

            return None

        # -------------------------------------------------
        # PowerShell script
        #
        # Finds the application in shell:AppsFolder
        # and invokes it.
        # -------------------------------------------------

        script = r'''
param(
    [string]$Target
)

$shell = New-Object -ComObject Shell.Application
$folder = $shell.Namespace("shell:AppsFolder")

if ($folder -eq $null) {
    exit 2
}

$targetLower = $Target.ToLower()

foreach ($item in $folder.Items()) {

    $name = $item.Name

    if ($name -ne $null) {

        $nameLower = $name.ToLower()

        if (
            $nameLower -eq $targetLower
            -or
            $nameLower.Contains($targetLower)
        ) {

            try {

                $item.InvokeVerb()

                Write-Output "SUCCESS"
                Write-Output $name

                exit 0

            }
            catch {

                exit 3
            }
        }
    }
}

exit 1
'''

        try:

            process = subprocess.Popen(
                [
                    "powershell.exe",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-Command",
                    script,
                    "-Target",
                    target_name
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )

            stdout, stderr = process.communicate(
                timeout=15
            )

            if (
                process.returncode == 0
                and "SUCCESS" in stdout
            ):

                lines = [
                    line.strip()
                    for line in stdout.splitlines()
                    if line.strip()
                ]

                app_name = target

                if len(lines) >= 2:

                    app_name = lines[-1]

                return (
                    True,
                    f"Opened Windows app: {app_name}"
                )

        except (
            subprocess.TimeoutExpired,
            OSError,
            Exception
        ):

            pass

        return None

    # =================================================
    # COMMON FILE / FOLDER SEARCH
    # =================================================

    def search_common_locations(self, target):

        target_original = (
            target
            .strip()
            .strip('"')
            .strip("'")
            .lower()
        )

        target_name = self.normalize(
            target_original
        )

        results = []

        for base_path in self.common_paths:

            if not os.path.exists(base_path):

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

                        # Exact filename
                        if (
                            file_lower
                            == target_original
                        ):

                            full_path = os.path.join(
                                root,
                                file
                            )

                            if full_path not in results:

                                results.insert(
                                    0,
                                    full_path
                                )

                        # Target without extension
                        elif (
                            filename_without_ext
                            == target_name
                        ):

                            full_path = os.path.join(
                                root,
                                file
                            )

                            if full_path not in results:

                                results.append(
                                    full_path
                                )

                        # If user specifically gave an extension
                        elif (
                            target_original
                            .endswith(
                                tuple(
                                    self.file_extensions
                                )
                            )
                            and
                            file_lower
                            == target_original
                        ):

                            full_path = os.path.join(
                                root,
                                file
                            )

                            if full_path not in results:

                                results.append(
                                    full_path
                                )

                    if len(results) >= 20:

                        return results

            except (
                PermissionError,
                OSError
            ):

                continue

        return results

    # =================================================
    # FIND EVERYTHING
    # =================================================

    def find(self, target):

        target = target.strip()

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
        # 2. NORMAL WINDOWS PATH
        # -------------------------------------------------

        path_result = self.find_in_path(
            target
        )

        if path_result:

            results.append(
                path_result
            )

        # -------------------------------------------------
        # 3. START MENU
        # -------------------------------------------------

        start_results = self.search_start_menu(
            target
        )

        for item in start_results:

            if item not in results:

                results.append(item)

        # -------------------------------------------------
        # 4. COMMON FILES / FOLDERS
        # -------------------------------------------------

        common_results = (
            self.search_common_locations(
                target
            )
        )

        for item in common_results:

            if item not in results:

                results.append(item)

        return results[:20]

    # =================================================
    # OPEN
    # =================================================

    def open(self, target):

        target = target.strip()

        if not target:

            return "Please tell me what you want to open."

        # -------------------------------------------------
        # FIRST: NORMAL FILE / FOLDER / EXE / START MENU
        # -------------------------------------------------

        results = self.find(target)

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
        # SECOND: WINDOWS BUILT-IN / STORE APP
        # -------------------------------------------------

        windows_app_result = (
            self.open_windows_app(
                target
            )
        )

        if windows_app_result:

            success, message = (
                windows_app_result
            )

            if success:

                return message

        # -------------------------------------------------
        # NOTHING FOUND
        # -------------------------------------------------

        return (
            f"I could not find "
            f"'{target}'."
        )

    # =================================================
    # SEARCH AND OPEN
    # =================================================

    def search_and_open(self, target):

        target = target.strip()

        if not target:

            return "Please tell me what you want to open."

        results = self.find(target)

        # -------------------------------------------------
        # ONE NORMAL RESULT
        # -------------------------------------------------

        if len(results) == 1:

            success, message = self._open(
                results[0]
            )

            if success:

                return message

        # -------------------------------------------------
        # MULTIPLE RESULTS
        # -------------------------------------------------

        if len(results) > 1:

            message = (
                f"I found multiple items "
                f"for '{target}':\n"
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
        # WINDOWS APP
        # -------------------------------------------------

        windows_app_result = (
            self.open_windows_app(
                target
            )
        )

        if windows_app_result:

            success, message = (
                windows_app_result
            )

            if success:

                return message

        return (
            f"I could not find "
            f"'{target}'."
        )

    # =================================================
    # OPEN SELECTED RESULT
    # =================================================

    def open_selected(self, results, number):

        try:

            index = int(number) - 1

        except ValueError:

            return "Please enter a valid number."

        if (
            index < 0
            or index >= len(results)
        ):

            return "Invalid selection."

        path = results[index]

        success, message = self._open(
            path
        )

        return message
