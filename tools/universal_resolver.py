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

            # -----------------------------------------
            # Windows AppsFolder path
            # -----------------------------------------

            if isinstance(path, str):

                if path.lower().startswith(
                    "shell:appsfolder\\"
                ):

                    subprocess.Popen(
                        [
                            "explorer.exe",
                            path
                        ]
                    )

                    return (
                        True,
                        f"Opened successfully: {path}"
                    )

            # -----------------------------------------
            # Normal Windows path
            # -----------------------------------------

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
    # GET START APPS
    #
    # IMPORTANT:
    #
    # Windows itself provides the application list.
    #
    # No application is hard-coded.
    #
    # Example output:
    #
    # Travel    Microsoft.WindowsMaps_...
    # Weather   Microsoft.BingWeather_...
    # Mail      ...
    #
    # Get-StartApps returns:
    #     Name
    #     AppID
    # =================================================

    def get_start_apps(self):

        script = r'''
$ErrorActionPreference = "SilentlyContinue"

try {

    if (
        Get-Command Get-StartApps `
        -ErrorAction SilentlyContinue
    ) {

        Get-StartApps |
        ForEach-Object {

            if (
                $_.Name -ne $null -and
                $_.AppID -ne $null
            ) {

                Write-Output (
                    $_.Name + "`t" + $_.AppID
                )
            }
        }
    }

}
catch {

    exit 1
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
    # FIND START APP
    #
    # Dynamic scan.
    #
    # 1. Exact match
    # 2. Unique partial match
    #
    # No hard-coded application names.
    # =================================================

    def find_start_app(self, target):

        target_name = self.normalize(
            target
        )

        if not target_name:

            return None

        apps = self.get_start_apps()

        if not apps:

            return None

        # -------------------------------------------------
        # EXACT MATCH
        # -------------------------------------------------

        for app in apps:

            app_name = self.normalize(
                app["name"]
            )

            if app_name == target_name:

                return app

        # -------------------------------------------------
        # PARTIAL MATCH
        # -------------------------------------------------

        partial_matches = []

        for app in apps:

            app_name = self.normalize(
                app["name"]
            )

            if target_name in app_name:

                partial_matches.append(
                    app
                )

        # -------------------------------------------------
        # ONLY ONE PARTIAL MATCH
        # -------------------------------------------------

        if len(partial_matches) == 1:

            return partial_matches[0]

        # -------------------------------------------------
        # MULTIPLE PARTIAL MATCHES
        #
        # Do not randomly open an application.
        # -------------------------------------------------

        return None

    # =================================================
    # OPEN START APP
    #
    # IMPORTANT FIX
    #
    # Uses the actual AppID returned by Get-StartApps.
    #
    # Several launch methods are attempted.
    # =================================================

    def open_start_app(self, target):

        app = self.find_start_app(
            target
        )

        if not app:

            return None

        app_name = app["name"]
        app_id = app["app_id"]

        shell_path = (
            "shell:AppsFolder\\"
            + app_id
        )

        # -------------------------------------------------
        # METHOD 1
        #
        # Direct Explorer launch.
        # -------------------------------------------------

        try:

            process = subprocess.Popen(
                [
                    "explorer.exe",
                    shell_path
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

            if process is not None:

                return (
                    True,
                    f"Opened Windows app: {app_name}"
                )

        except (
            OSError,
            Exception
        ):

            pass

        # -------------------------------------------------
        # METHOD 2
        #
        # os.startfile()
        # -------------------------------------------------

        try:

            os.startfile(
                shell_path
            )

            return (
                True,
                f"Opened Windows app: {app_name}"
            )

        except (
            OSError,
            Exception
        ):

            pass

        # -------------------------------------------------
        # METHOD 3
        #
        # PowerShell Start-Process
        #
        # IMPORTANT:
        # AppID is passed correctly through a script
        # parameter block.
        # -------------------------------------------------

        script = r'''
param(
    [string]$AppID
)

$ErrorActionPreference = "Stop"

try {

    $target = "shell:AppsFolder\" + $AppID

    Start-Process `
        -FilePath "explorer.exe" `
        -ArgumentList $target

    exit 0

}
catch {

    exit 1
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
                    "& { " + script + " }",
                    app_id
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )

            stdout, stderr = process.communicate(
                timeout=10
            )

            if process.returncode == 0:

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
    # START MENU SHORTCUT SEARCH
    # =================================================

    def search_start_menu(self, target):

        target_name = self.normalize(
            target
        )

        results = []

        for start_path in self.start_menu_paths:

            if not os.path.exists(
                start_path
            ):

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
                        ):

                            continue

                        filename = os.path.splitext(
                            file
                        )[0].strip().lower()

                        # ---------------------------------
                        # Exact match
                        # ---------------------------------

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

                        # ---------------------------------
                        # Partial match
                        # ---------------------------------

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
    # OLD CODE PRESERVED
    #
    # This is the fallback if Get-StartApps is
    # unavailable on a particular Windows environment.
    # =================================================

    def search_windows_apps(
        self,
        target
    ):

        target_name = self.normalize(
            target
        )

        if not target_name:

            return []

        results = []

        script = r'''
$ErrorActionPreference = "SilentlyContinue"

if (
    Get-Command Get-StartApps `
    -ErrorAction SilentlyContinue
) {

    Get-StartApps |
    ForEach-Object {

        if (
            $_.Name -and
            $_.AppID
        ) {

            Write-Output (
                $_.Name + "`t" + $_.AppID
            )
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

                return (
                    self.search_windows_apps_fallback(
                        target
                    )
                )

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

                app_name = parts[0].strip()
                app_id = parts[1].strip()

                if not app_name or not app_id:

                    continue

                app_normalized = (
                    app_name.lower().strip()
                )

                app_path = (
                    "shell:AppsFolder\\"
                    + app_id
                )

                result = {
                    "name": app_name,
                    "app_id": app_id,
                    "path": app_path
                }

                # -----------------------------------------
                # Exact match
                # -----------------------------------------

                if app_normalized == target_name:

                    results.insert(
                        0,
                        result
                    )

                # -----------------------------------------
                # Partial match
                # -----------------------------------------

                elif target_name in app_normalized:

                    duplicate = False

                    for existing in results:

                        if (
                            existing["app_id"]
                            == app_id
                        ):

                            duplicate = True
                            break

                    if not duplicate:

                        results.append(
                            result
                        )

        except (
            subprocess.TimeoutExpired,
            OSError,
            Exception
        ):

            return (
                self.search_windows_apps_fallback(
                    target
                )
            )

        return results[:20]

    # =================================================
    # WINDOWS APPS FALLBACK
    #
    # OLD CODE PRESERVED
    #
    # Uses shell:AppsFolder through Shell.Application.
    # =================================================

    def search_windows_apps_fallback(
        self,
        target
    ):

        target_name = self.normalize(
            target
        )

        if not target_name:

            return []

        results = []

        script = r'''
$ErrorActionPreference = "SilentlyContinue"

try {

    $shell = New-Object `
        -ComObject Shell.Application

    $folder = $shell.Namespace(
        "shell:AppsFolder"
    )

    if ($folder -ne $null) {

        foreach ($item in $folder.Items()) {

            $name = $item.Name
            $path = $item.Path

            if (
                $name -and
                $path
            ) {

                Write-Output (
                    $name + "`t" + $path
                )
            }
        }
    }

}
catch {

    exit 1
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

                app_name = parts[0].strip()
                app_path = parts[1].strip()

                if not app_name or not app_path:

                    continue

                app_normalized = (
                    app_name.lower().strip()
                )

                if (
                    app_normalized
                    == target_name
                    or
                    target_name
                    in app_normalized
                ):

                    result = {
                        "name": app_name,
                        "app_id": "",
                        "path": app_path
                    }

                    duplicate = False

                    for existing in results:

                        if (
                            existing["path"]
                            == app_path
                        ):

                            duplicate = True
                            break

                    if not duplicate:

                        if (
                            app_normalized
                            == target_name
                        ):

                            results.insert(
                                0,
                                result
                            )

                        else:

                            results.append(
                                result
                            )

        except (
            subprocess.TimeoutExpired,
            OSError,
            Exception
        ):

            return []

        return results[:20]

    # =================================================
    # OPEN WINDOWS APP BY PATH
    #
    # OLD FUNCTION PRESERVED
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
        # METHOD 1
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

                return (
                    True,
                    f"Opened successfully: {app_path}"
                )

        except (
            OSError,
            Exception
        ):

            pass

        # -------------------------------------------------
        # METHOD 2
        # -------------------------------------------------

        try:

            os.startfile(
                app_path
            )

            return (
                True,
                f"Opened successfully: {app_path}"
            )

        except Exception as e:

            return (
                False,
                f"Error opening Windows app: {e}"
            )

    # =================================================
    # OPEN WINDOWS APP
    #
    # IMPORTANT:
    #
    # 1. First use Get-StartApps
    # 2. If unavailable/fails, use old AppsFolder
    # 3. No hard-coded app names
    # =================================================

    def open_windows_app(
        self,
        target
    ):

        # -------------------------------------------------
        # FIRST:
        # New dynamic Get-StartApps scanner
        # -------------------------------------------------

        start_app = self.find_start_app(
            target
        )

        if start_app:

            success, message = (
                self.open_windows_app_by_path(
                    start_app["path"]
                )
            )

            if success:

                return (
                    True,
                    f"Opened Windows app: "
                    f"{start_app['name']}"
                )

            # If first launch method failed,
            # use direct launcher.

            direct_result = (
                self.open_start_app(
                    target
                )
            )

            if direct_result:

                return direct_result

        # -------------------------------------------------
        # SECOND:
        # OLD WINDOWS APPSFOLDER SEARCH
        #
        # This keeps old functionality.
        # -------------------------------------------------

        results = self.search_windows_apps(
            target
        )

        if not results:

            return None

        # -------------------------------------------------
        # ONE APP
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

                        # ---------------------------------
                        # Exact filename
                        # ---------------------------------

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

                        # ---------------------------------
                        # Filename without extension
                        # ---------------------------------

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

                        # ---------------------------------
                        # Explicit extension
                        # ---------------------------------

                        elif (
                            target_original.endswith(
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
    #
    # IMPORTANT:
    #
    # Windows Apps are NOT mixed into the normal
    # filesystem results.
    #
    # This preserves old behavior.
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
        # 3. START MENU .LNK / .EXE
        # -------------------------------------------------

        start_results = (
            self.search_start_menu(
                target
            )
        )

        for item in start_results:

            if item not in results:

                results.append(
                    item
                )

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

                results.append(
                    item
                )

        return results[:20]

    # =================================================
    # OPEN
    # =================================================

    def open(self, target):

        target = target.strip()

        if not target:

            return (
                "Please tell me what you want "
                "to open."
            )

        # -------------------------------------------------
        # FIRST:
        # DYNAMIC WINDOWS APP SCAN
        #
        # This is the important part.
        #
        # Vyom scans the actual Windows application
        # list before searching normal files.
        # -------------------------------------------------

        windows_app_result = (
            self.open_windows_app(
                target
            )
        )

        if windows_app_result:

            # ---------------------------------------------
            # One app opened successfully
            # ---------------------------------------------

            if len(windows_app_result) == 2:

                success, message = (
                    windows_app_result
                )

                if success:

                    return message

                # Do not immediately stop if the app
                # launcher itself failed.
                #
                # Normal file search will continue.

            # ---------------------------------------------
            # Multiple apps
            # ---------------------------------------------

            elif len(windows_app_result) == 3:

                success, message, app_results = (
                    windows_app_result
                )

                return message

        # -------------------------------------------------
        # SECOND:
        # NORMAL FILE / FOLDER / EXE / LNK
        # -------------------------------------------------

        results = self.find(
            target
        )

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
        # NOTHING FOUND
        # -------------------------------------------------

        return (
            f"I could not find "
            f"'{target}'."
        )

    # =================================================
    # SEARCH AND OPEN
    # =================================================

    def search_and_open(
        self,
        target
    ):

        target = target.strip()

        if not target:

            return (
                "Please tell me what you want "
                "to open."
            )

        # -------------------------------------------------
        # FIRST:
        # DYNAMIC WINDOWS APP SEARCH
        # -------------------------------------------------

        windows_app_result = (
            self.open_windows_app(
                target
            )
        )

        if windows_app_result:

            if len(windows_app_result) == 2:

                success, message = (
                    windows_app_result
                )

                if success:

                    return message

            elif len(windows_app_result) == 3:

                success, message, app_results = (
                    windows_app_result
                )

                return message

        # -------------------------------------------------
        # SECOND:
        # NORMAL FILE / FOLDER / EXE / LNK
        # -------------------------------------------------

        results = self.find(
            target
        )

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
        # MULTIPLE NORMAL RESULTS
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
        # NOTHING FOUND
        # -------------------------------------------------

        return (
            f"I could not find "
            f"'{target}'."
        )

    # =================================================
    # OPEN SELECTED RESULT
    #
    # Supports:
    #     Normal Windows paths
    #     Windows Apps dictionaries
    #     shell:AppsFolder paths
    # =================================================

    def open_selected(
        self,
        results,
        number
    ):

        try:

            index = int(number) - 1

        except ValueError:

            return (
                "Please enter a valid number."
            )

        if (
            index < 0
            or index >= len(results)
        ):

            return "Invalid selection."

        selected = results[index]

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
