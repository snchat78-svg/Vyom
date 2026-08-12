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
import difflib


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

        # -------------------------------------------------
        # PENDING RESULTS
        #
        # Used when user must select a number.
        # -------------------------------------------------

        self.pending_results = []

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
    # START MENU SEARCH
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

                        full_path = os.path.join(
                            root,
                            file
                        )

                        # ---------------------------------
                        # Exact match
                        # ---------------------------------

                        if filename == target_name:

                            if full_path not in results:

                                results.insert(
                                    0,
                                    full_path
                                )

                        # ---------------------------------
                        # Partial match
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

        return results

    # =================================================
    # DIRECT WINDOWS APPSFOLDER SCAN
    #
    # IMPORTANT:
    #
    # This is the main Windows App scanner.
    #
    # It directly uses:
    #
    #     shell:AppsFolder
    #
    # This is especially important for:
    #
    # Windows 8
    # Windows 8.1
    # Windows 10
    # Windows 11
    #
    # It does NOT require hard-coded app names.
    # =================================================

    def scan_apps_folder(self):

        script = r'''
$ErrorActionPreference = "SilentlyContinue"

try {

    $shell = New-Object -ComObject Shell.Application

    $folder = $shell.Namespace("shell:AppsFolder")

    if ($folder -eq $null) {
        exit 2
    }

    foreach ($item in $folder.Items()) {

        try {

            $name = $item.Name
            $path = $item.Path

            if ($name) {

                if (-not $path) {
                    $path = ""
                }

                Write-Output (
                    $name + "`t" + $path
                )
            }

        }
        catch {
            continue
        }
    }

}
catch {

    exit 1
}
'''

        apps = []

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

            if process.returncode != 0:

                return []

            for line in stdout.splitlines():

                line = line.strip()

                if not line:

                    continue

                parts = line.split(
                    "\t",
                    1
                )

                if len(parts) == 1:

                    app_name = parts[0].strip()
                    app_path = ""

                else:

                    app_name = parts[0].strip()
                    app_path = parts[1].strip()

                if not app_name:

                    continue

                duplicate = False

                for existing in apps:

                    if (
                        existing["name"].lower()
                        ==
                        app_name.lower()
                    ):

                        duplicate = True
                        break

                if duplicate:

                    continue

                apps.append(
                    {
                        "name": app_name,
                        "path": app_path,
                        "app_id": ""
                    }
                )

        except (
            subprocess.TimeoutExpired,
            OSError,
            Exception
        ):

            return []

        return apps

    # =================================================
    # GET START APPS
    #
    # Additional scanner.
    #
    # This is NOT the only method anymore.
    # =================================================

    def get_start_apps(self):

        script = r'''
$ErrorActionPreference = "SilentlyContinue"

try {

    if (
        Get-Command Get-StartApps
        -ErrorAction SilentlyContinue
    ) {

        Get-StartApps |
        ForEach-Object {

            $name = $_.Name
            $appId = $_.AppID

            if (
                $name -and
                $appId
            ) {

                Write-Output (
                    $name + "`t" + $appId
                )
            }
        }
    }

}
catch {

    exit 1
}
'''

        apps = []

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

            if process.returncode != 0:

                return []

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

        except (
            subprocess.TimeoutExpired,
            OSError,
            Exception
        ):

            return []

        return apps

    # =================================================
    # FIND WINDOWS APP
    #
    # Uses AppsFolder FIRST.
    # Then Get-StartApps.
    #
    # Exact match has highest priority.
    # =================================================

    def search_windows_apps(self, target):

        target_name = self.normalize(
            target
        )

        if not target_name:

            return []

        results = []

        # -------------------------------------------------
        # 1. DIRECT AppsFolder SCAN
        # -------------------------------------------------

        apps_folder_apps = (
            self.scan_apps_folder()
        )

        # -------------------------------------------------
        # EXACT MATCH
        # -------------------------------------------------

        for app in apps_folder_apps:

            app_name = self.normalize(
                app["name"]
            )

            if app_name == target_name:

                result = {
                    "name": app["name"],
                    "app_id": app.get(
                        "app_id",
                        ""
                    ),
                    "path": app.get(
                        "path",
                        ""
                    ),
                    "source": "appsfolder"
                }

                return [result]

        # -------------------------------------------------
        # PARTIAL MATCH
        # -------------------------------------------------

        for app in apps_folder_apps:

            app_name = self.normalize(
                app["name"]
            )

            if target_name in app_name:

                result = {
                    "name": app["name"],
                    "app_id": app.get(
                        "app_id",
                        ""
                    ),
                    "path": app.get(
                        "path",
                        ""
                    ),
                    "source": "appsfolder"
                }

                duplicate = False

                for existing in results:

                    if (
                        existing["name"].lower()
                        ==
                        result["name"].lower()
                    ):

                        duplicate = True
                        break

                if not duplicate:

                    results.append(
                        result
                    )

        # -------------------------------------------------
        # 2. Get-StartApps
        # -------------------------------------------------

        start_apps = (
            self.get_start_apps()
        )

        # -------------------------------------------------
        # EXACT MATCH FROM Get-StartApps
        # -------------------------------------------------

        for app in start_apps:

            app_name = self.normalize(
                app["name"]
            )

            if app_name == target_name:

                result = {
                    "name": app["name"],
                    "app_id": app.get(
                        "app_id",
                        ""
                    ),
                    "path": app.get(
                        "path",
                        ""
                    ),
                    "source": "get-startapps"
                }

                return [result]

        # -------------------------------------------------
        # PARTIAL MATCH FROM Get-StartApps
        # -------------------------------------------------

        for app in start_apps:

            app_name = self.normalize(
                app["name"]
            )

            if target_name in app_name:

                result = {
                    "name": app["name"],
                    "app_id": app.get(
                        "app_id",
                        ""
                    ),
                    "path": app.get(
                        "path",
                        ""
                    ),
                    "source": "get-startapps"
                }

                duplicate = False

                for existing in results:

                    if (
                        existing["name"].lower()
                        ==
                        result["name"].lower()
                    ):

                        duplicate = True
                        break

                if not duplicate:

                    results.append(
                        result
                    )

        return results[:20]

    # =================================================
    # DIRECTLY OPEN WINDOWS APP
    #
    # This is the important Windows 8.1 fix.
    #
    # Instead of relying only on:
    #
    # explorer.exe shell:AppsFolder\AppID
    #
    # we directly ask Windows Shell:
    #
    #     item.InvokeVerb()
    #
    # to launch the actual App.
    # =================================================

    def open_windows_app_direct(
        self,
        target
    ):

        target_name = self.normalize(
            target
        )

        if not target_name:

            return None

        script = r'''
$ErrorActionPreference = "SilentlyContinue"

param(
    [string]$Target
)

try {

    $shell = New-Object -ComObject Shell.Application

    $folder = $shell.Namespace(
        "shell:AppsFolder"
    )

    if ($folder -eq $null) {
        exit 2
    }

    $targetLower = $Target.ToLower()

    $partial = @()

    foreach ($item in $folder.Items()) {

        try {

            $name = $item.Name

            if (-not $name) {
                continue
            }

            $nameLower = $name.ToLower()

            # -----------------------------------------
            # EXACT MATCH
            # -----------------------------------------

            if ($nameLower -eq $targetLower) {

                try {

                    $item.InvokeVerb()

                    Write-Output "SUCCESS"
                    Write-Output $name

                    exit 0

                }
                catch {

                    try {

                        $item.InvokeVerb("open")

                        Write-Output "SUCCESS"
                        Write-Output $name

                        exit 0

                    }
                    catch {

                        continue
                    }
                }
            }

            # -----------------------------------------
            # PARTIAL MATCH
            # -----------------------------------------

            if ($nameLower.Contains($targetLower)) {

                $partial += $item
            }

        }
        catch {

            continue
        }
    }

    # ---------------------------------------------
    # If exactly one partial app exists
    # ---------------------------------------------

    if ($partial.Count -eq 1) {

        $item = $partial[0]

        try {

            $item.InvokeVerb()

            Write-Output "SUCCESS"
            Write-Output $item.Name

            exit 0

        }
        catch {

            try {

                $item.InvokeVerb("open")

                Write-Output "SUCCESS"
                Write-Output $item.Name

                exit 0

            }
            catch {

                exit 3
            }
        }
    }

    # ---------------------------------------------
    # Multiple partial matches
    # ---------------------------------------------

    if ($partial.Count -gt 1) {

        Write-Output "MULTIPLE"

        foreach ($item in $partial) {

            Write-Output $item.Name
        }

        exit 4
    }

}
catch {

    exit 5
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
                timeout=20
            )

            lines = [
                line.strip()
                for line in stdout.splitlines()
                if line.strip()
            ]

            if (
                process.returncode == 0
                and
                len(lines) >= 2
                and
                lines[0] == "SUCCESS"
            ):

                app_name = lines[1]

                return (
                    True,
                    f"Opened Windows app: {app_name}"
                )

            # -----------------------------------------
            # Multiple partial Apps
            # -----------------------------------------

            if (
                process.returncode == 4
                and
                len(lines) >= 2
                and
                lines[0] == "MULTIPLE"
            ):

                multiple = []

                for name in lines[1:]:

                    if name not in multiple:

                        multiple.append(
                            {
                                "name": name,
                                "app_id": "",
                                "path": "",
                                "source": "appsfolder"
                            }
                        )

                return (
                    False,
                    f"Multiple Windows apps found "
                    f"for '{target}':\n"
                    +
                    "\n".join(
                        [
                            f"{i}. {app['name']}"
                            for i, app
                            in enumerate(
                                multiple,
                                start=1
                            )
                        ]
                    )
                    +
                    "\n\nPlease select a number.",
                    multiple
                )

        except (
            subprocess.TimeoutExpired,
            OSError,
            Exception
        ):

            pass

        return None

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

        try:

            subprocess.Popen(
                [
                    "explorer.exe",
                    app_path
                ]
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
    # First:
    #     Direct AppsFolder InvokeVerb
    #
    # Then:
    #     Scanner + AppID
    # =================================================

    def open_windows_app(self, target):

        # -------------------------------------------------
        # FIRST:
        # DIRECT SHELL AppsFolder INVOKE
        #
        # This fixes Windows 8 / 8.1 Store Apps.
        # -------------------------------------------------

        direct_result = (
            self.open_windows_app_direct(
                target
            )
        )

        if direct_result:

            return direct_result

        # -------------------------------------------------
        # SECOND:
        # SCAN APPS
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

            app_path = app.get(
                "path",
                ""
            )

            # ---------------------------------------------
            # Try AppsFolder path
            # ---------------------------------------------

            if app_path:

                success, message = (
                    self.open_windows_app_by_path(
                        app_path
                    )
                )

                if success:

                    return (
                        True,
                        f"Opened Windows app: "
                        f"{app['name']}"
                    )

            # ---------------------------------------------
            # If path failed, use PowerShell direct
            # ---------------------------------------------

            retry = (
                self.open_windows_app_direct(
                    app["name"]
                )
            )

            if retry:

                return retry

            return (
                False,
                f"Found Windows app "
                f"'{app['name']}', "
                f"but Windows could not open it."
            )

        # -------------------------------------------------
        # MULTIPLE APPS
        # -------------------------------------------------

        self.pending_results = results

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
    # SIMILAR FILE / FOLDER SEARCH
    #
    # Used when exact spelling is not found.
    #
    # Example:
    #
    #   user: open weater
    #
    #   result:
    #
    #   Similar items found:
    #   1. Weather
    #   2. Weather Report.txt
    #
    # =================================================

    def search_similar_files(
        self,
        target
    ):

        target_name = self.normalize(
            target
        )

        if not target_name:

            return []

        candidates = []

        # -------------------------------------------------
        # START MENU
        # -------------------------------------------------

        start_results = []

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

                        name = os.path.splitext(
                            file
                        )[0]

                        candidates.append(
                            {
                                "name": name,
                                "path": os.path.join(
                                    root,
                                    file
                                ),
                                "type": "path"
                            }
                        )

            except (
                PermissionError,
                OSError
            ):

                continue

        # -------------------------------------------------
        # COMMON LOCATIONS
        # -------------------------------------------------

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

                    for directory in dirs:

                        candidates.append(
                            {
                                "name": directory,
                                "path": os.path.join(
                                    root,
                                    directory
                                ),
                                "type": "path"
                            }
                        )

                    for file in files:

                        candidates.append(
                            {
                                "name": file,
                                "path": os.path.join(
                                    root,
                                    file
                                ),
                                "type": "path"
                            }
                        )

            except (
                PermissionError,
                OSError
            ):

                continue

        # -------------------------------------------------
        # WINDOWS APPS
        # -------------------------------------------------

        apps = self.scan_apps_folder()

        for app in apps:

            candidates.append(
                {
                    "name": app["name"],
                    "path": app.get(
                        "path",
                        ""
                    ),
                    "app_id": app.get(
                        "app_id",
                        ""
                    ),
                    "type": "windows_app"
                }
            )

        # -------------------------------------------------
        # CALCULATE SIMILARITY
        # -------------------------------------------------

        scored = []

        for candidate in candidates:

            candidate_name = (
                self.normalize(
                    candidate["name"]
                )
            )

            if not candidate_name:

                continue

            # ---------------------------------------------
            # Exact is not a "similar" result.
            # ---------------------------------------------

            if candidate_name == target_name:

                continue

            # ---------------------------------------------
            # Similarity
            # ---------------------------------------------

            ratio = difflib.SequenceMatcher(
                None,
                target_name,
                candidate_name
            ).ratio()

            # ---------------------------------------------
            # Extra score when one contains another
            # ---------------------------------------------

            if (
                target_name in candidate_name
                or
                candidate_name in target_name
            ):

                ratio += 0.15

            # ---------------------------------------------
            # First-letter / word similarity
            # ---------------------------------------------

            target_words = target_name.split()
            candidate_words = candidate_name.split()

            if target_words and candidate_words:

                if (
                    target_words[0][0]
                    ==
                    candidate_words[0][0]
                ):

                    ratio += 0.03

            if ratio >= 0.45:

                candidate_copy = dict(
                    candidate
                )

                candidate_copy["score"] = ratio

                scored.append(
                    candidate_copy
                )

        # -------------------------------------------------
        # SORT BY BEST MATCH
        # -------------------------------------------------

        scored.sort(
            key=lambda item: item["score"],
            reverse=True
        )

        # -------------------------------------------------
        # REMOVE DUPLICATES
        # -------------------------------------------------

        final_results = []

        seen = set()

        for item in scored:

            key = (
                item["name"].lower(),
                item.get(
                    "path",
                    ""
                ).lower()
                if isinstance(
                    item.get("path", ""),
                    str
                )
                else ""
            )

            if key in seen:

                continue

            seen.add(key)

            final_results.append(
                item
            )

            if len(final_results) >= 10:

                break

        return final_results

    # =================================================
    # DISPLAY SIMILAR RESULTS
    # =================================================

    def format_similar_results(
        self,
        target,
        results
    ):

        if not results:

            return (
                f"I could not find "
                f"'{target}'."
            )

        self.pending_results = results

        message = (
            f"I could not find an exact match "
            f"for '{target}'.\n\n"
            f"Similar items found:\n"
        )

        for index, item in enumerate(
            results,
            start=1
        ):

            message += (
                f"{index}. "
                f"{item['name']}\n"
            )

        message += (
            "\nPlease select a number to open."
        )

        return message

    # =================================================
    # FIND EVERYTHING
    #
    # Windows Apps are kept separate from normal
    # filesystem results.
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
        # CLEAR OLD PENDING RESULTS
        # -------------------------------------------------

        self.pending_results = []

        # -------------------------------------------------
        # FIRST:
        # EXACT NORMAL FILE / FOLDER / EXE / LNK
        #
        # This keeps the old behavior.
        # -------------------------------------------------

        exact_path = self.find_exact_path(
            target
        )

        if exact_path:

            success, message = self._open(
                exact_path
            )

            if success:

                return message

        # -------------------------------------------------
        # SECOND:
        # EXACT WINDOWS APP
        #
        # Direct AppsFolder scan.
        # -------------------------------------------------

        windows_app_result = (
            self.open_windows_app_direct(
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

                self.pending_results = (
                    app_results
                )

                return message

        # -------------------------------------------------
        # THIRD:
        # OLD NORMAL SEARCH
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

            self.pending_results = results

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
        # FOURTH:
        # WINDOWS APP SCANNER
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

                return message

            if len(
                windows_app_result
            ) == 3:

                success, message, app_results = (
                    windows_app_result
                )

                self.pending_results = (
                    app_results
                )

                return message

        # -------------------------------------------------
        # FIFTH:
        # SIMILAR SEARCH
        #
        # Typo / spelling mistake support.
        # -------------------------------------------------

        similar_results = (
            self.search_similar_files(
                target
            )
        )

        if similar_results:

            return self.format_similar_results(
                target,
                similar_results
            )

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
        # Use same resolver logic
        # -------------------------------------------------

        return self.open(
            target
        )

    # =================================================
    # OPEN SELECTED RESULT
    #
    # Supports:
    #
    #     Normal paths
    #     Windows Apps
    #     Similar results
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

            app_name = selected.get(
                "name",
                "Windows app"
            )

            # ---------------------------------------------
            # If this is a Windows App
            # ---------------------------------------------

            if (
                selected.get("type")
                == "windows_app"
                or
                selected.get("source")
                == "appsfolder"
                or
                selected.get("source")
                == "get-startapps"
            ):

                # -----------------------------------------
                # Try stored path first
                # -----------------------------------------

                app_path = selected.get(
                    "path",
                    ""
                )

                if app_path:

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

                # -----------------------------------------
                # Most reliable fallback:
                # find the app again and InvokeVerb
                # -----------------------------------------

                direct_result = (
                    self.open_windows_app_direct(
                        app_name
                    )
                )

                if direct_result:

                    if len(
                        direct_result
                    ) == 2:

                        success, message = (
                            direct_result
                        )

                        if success:

                            return message

                    elif len(
                        direct_result
                    ) == 3:

                        return direct_result[1]

                return (
                    f"Could not open Windows app "
                    f"'{app_name}'."
                )

            # ---------------------------------------------
            # Similar normal file/folder
            # ---------------------------------------------

            normal_path = selected.get(
                "path"
            )

            if normal_path:

                success, message = (
                    self._open(
                        normal_path
                    )
                )

                return message

            return (
                f"Could not open "
                f"'{app_name}'."
            )

        # -------------------------------------------------
        # Normal path
        # -------------------------------------------------

        success, message = self._open(
            selected
        )

        return message

    # =================================================
    # OPEN PENDING RESULT
    #
    # This helper allows the command engine to use:
    #
    #     open_selected(self.pending_results, number)
    #
    # =================================================

    def open_pending(
        self,
        number
    ):

        if not self.pending_results:

            return (
                "There are no pending results."
            )

        return self.open_selected(
            self.pending_results,
            number
    )
