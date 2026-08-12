"""
Project : Vyom AI
Version : 1.0
Module  : Universal Windows Resolver

Purpose:
    Universal Windows application/file/folder resolver.

Designed for:
    Windows 8 / 8.1 / 10 / 11

Supports:
    - Normal EXE applications
    - BAT / CMD / COM
    - Start Menu shortcuts
    - User Start Menu
    - All Users Start Menu
    - Desktop shortcuts
    - Public Desktop
    - Program Files
    - Program Files (x86)
    - PATH applications
    - Registry App Paths
    - Windows AppsFolder
    - Windows Store / Modern Apps
    - AUMID / AppID
    - Shell.Application COM
    - AppsFolder InvokeVerb("open")
    - Exact matching
    - Partial matching
    - Duplicate removal
    - Similar-name suggestions
    - Spelling error recovery
    - Number selection
"""

import os
import shutil
import subprocess
import difflib
import ctypes
import winreg
import time


class UniversalResolver:

    def __init__(self):

        # =================================================
        # START MENU LOCATIONS
        # =================================================

        appdata = os.environ.get(
            "APPDATA",
            ""
        )

        programdata = os.environ.get(
            "PROGRAMDATA",
            ""
        )

        user_profile = os.environ.get(
            "USERPROFILE",
            ""
        )

        self.start_menu_paths = [
            os.path.join(
                appdata,
                "Microsoft",
                "Windows",
                "Start Menu",
                "Programs"
            ),

            os.path.join(
                programdata,
                "Microsoft",
                "Windows",
                "Start Menu",
                "Programs"
            )
        ]

        # =================================================
        # DESKTOP LOCATIONS
        # =================================================

        self.desktop_paths = [
            os.path.join(
                user_profile,
                "Desktop"
            ),

            os.path.join(
                programdata,
                "Desktop"
            ),

            os.path.join(
                user_profile,
                "OneDrive",
                "Desktop"
            )
        ]

        # =================================================
        # COMMON LOCATIONS
        # =================================================

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
            ),

            os.path.join(
                user_profile,
                "OneDrive",
                "Desktop"
            ),

            os.path.join(
                user_profile,
                "OneDrive",
                "Documents"
            ),

            os.path.join(
                user_profile,
                "OneDrive",
                "Pictures"
            )
        ]

        # =================================================
        # PROGRAM FILE LOCATIONS
        # =================================================

        self.program_paths = []

        program_files = os.environ.get(
            "ProgramFiles",
            ""
        )

        program_files_x86 = os.environ.get(
            "ProgramFiles(x86)",
            ""
        )

        program_w6432 = os.environ.get(
            "ProgramW6432",
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

        if program_w6432:
            self.program_paths.append(
                program_w6432
            )

        # =================================================
        # ADDITIONAL WINDOWS LOCATIONS
        # =================================================

        windows_dir = os.environ.get(
            "WINDIR",
            r"C:\Windows"
        )

        self.windows_paths = [
            windows_dir,
            os.path.join(
                windows_dir,
                "System32"
            ),
            os.path.join(
                windows_dir,
                "SysWOW64"
            )
        ]

        # =================================================
        # WINDOWS APPS LOCATIONS
        #
        # We DO NOT depend on this location for launching
        # Store apps. It is only used as an additional
        # discovery source.
        # =================================================

        self.windows_apps_paths = [
            os.path.join(
                os.environ.get(
                    "ProgramFiles",
                    r"C:\Program Files"
                ),
                "WindowsApps"
            ),

            os.path.join(
                os.environ.get(
                    "LOCALAPPDATA",
                    ""
                ),
                "Packages"
            )
        ]

        # =================================================
        # APPLICATION EXTENSIONS
        # =================================================

        self.application_extensions = [
            ".exe",
            ".com",
            ".bat",
            ".cmd",
            ".lnk"
        ]

        # =================================================
        # FILE EXTENSIONS
        # =================================================

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
        # MAX RESULTS
        # =================================================

        self.max_results = 20

        # =================================================
        # CACHE
        #
        # AppsFolder enumeration is relatively expensive.
        # =================================================

        self._windows_apps_cache = None
        self._windows_apps_cache_time = 0

        self.app_cache_seconds = 30

    # =====================================================
    # NORMALIZE
    # =====================================================

    def normalize(self, name):

        if name is None:
            return ""

        name = str(name)

        name = name.strip()

        name = name.strip('"')

        name = name.strip("'")

        name = name.lower()

        # Remove common application extensions

        for ext in (
            ".exe",
            ".lnk",
            ".bat",
            ".cmd",
            ".com"
        ):

            if name.endswith(ext):
                name = name[:-len(ext)]
                break

        # Normalize spaces

        name = " ".join(
            name.split()
        )

        return name.strip()

    # =====================================================
    # CLEAN TARGET
    # =====================================================

    def clean_target(self, target):

        if target is None:
            return ""

        target = str(target)

        target = target.strip()

        target = target.strip('"')

        target = target.strip("'")

        return target.strip()

    # =====================================================
    # SAFE UNIQUE ADD
    # =====================================================

    def _add_unique(
        self,
        results,
        item
    ):

        if item is None:
            return

        if isinstance(
            item,
            str
        ):

            key = item.lower()

        elif isinstance(
            item,
            dict
        ):

            key = (
                str(
                    item.get(
                        "name",
                        ""
                    )
                ).lower()
                + "|"
                +
                str(
                    item.get(
                        "path",
                        ""
                    )
                ).lower()
            )

        else:

            key = str(
                item
            ).lower()

        for existing in results:

            if isinstance(
                existing,
                str
            ):

                existing_key = (
                    existing.lower()
                )

            elif isinstance(
                existing,
                dict
            ):

                existing_key = (
                    str(
                        existing.get(
                            "name",
                            ""
                        )
                    ).lower()
                    + "|"
                    +
                    str(
                        existing.get(
                            "path",
                            ""
                        )
                    ).lower()
                )

            else:

                existing_key = str(
                    existing
                ).lower()

            if existing_key == key:
                return

        results.append(
            item
        )

    # =====================================================
    # STRONG NORMAL FILE LAUNCHER
    # =====================================================

    def _open(self, path):

        try:

            if not path:

                return (
                    False,
                    "Invalid path."
                )

            # ---------------------------------------------
            # shell:AppsFolder
            # ---------------------------------------------

            if isinstance(
                path,
                str
            ):

                if path.lower().startswith(
                    "shell:appsfolder"
                ):

                    if self._launch_appsfolder_path(
                        path
                    ):

                        return (
                            True,
                            "Opened successfully: "
                            + path
                        )

            # ---------------------------------------------
            # Existing path
            # ---------------------------------------------

            if not os.path.exists(path):

                return (
                    False,
                    "Path does not exist: "
                    + path
                )

            # ---------------------------------------------
            # METHOD 1
            # os.startfile
            # ---------------------------------------------

            try:

                os.startfile(path)

                return (
                    True,
                    "Opened successfully: "
                    + path
                )

            except Exception:
                pass

            # ---------------------------------------------
            # METHOD 2
            # ShellExecute
            # ---------------------------------------------

            try:

                result = (
                    ctypes.windll.shell32.ShellExecuteW(
                        None,
                        "open",
                        path,
                        None,
                        None,
                        1
                    )
                )

                if result > 32:

                    return (
                        True,
                        "Opened successfully: "
                        + path
                    )

            except Exception:
                pass

            # ---------------------------------------------
            # METHOD 3
            # CMD START
            # ---------------------------------------------

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
                    "Opened successfully: "
                    + path
                )

            except Exception:
                pass

        except Exception as e:

            return (
                False,
                "Error opening '{}': {}".format(
                    path,
                    e
                )
            )

        return (
            False,
            "Could not open: {}".format(
                path
            )
        )

    # =====================================================
    # APPSFOLDER PATH LAUNCHER
    #
    # Multiple methods.
    # =====================================================

    def _launch_appsfolder_path(
        self,
        app_path
    ):

        if not app_path:
            return False

        # ---------------------------------------------
        # METHOD 1
        # ShellExecute directly
        # ---------------------------------------------

        try:

            result = (
                ctypes.windll.shell32.ShellExecuteW(
                    None,
                    "open",
                    app_path,
                    None,
                    None,
                    1
                )
            )

            if result > 32:

                return True

        except Exception:
            pass

        # ---------------------------------------------
        # METHOD 2
        # explorer.exe
        # ---------------------------------------------

        try:

            subprocess.Popen(
                [
                    "explorer.exe",
                    app_path
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

            return True

        except Exception:
            pass

        # ---------------------------------------------
        # METHOD 3
        # CMD START
        # ---------------------------------------------

        try:

            subprocess.Popen(
                [
                    "cmd.exe",
                    "/c",
                    "start",
                    "",
                    app_path
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

            return True

        except Exception:
            pass

        return False

    # =====================================================
    # APPSFOLDER COM DIRECT OPEN
    #
    # THIS IS THE IMPORTANT FIX
    #
    # Uses Shell.Application and InvokeVerb("open").
    # =====================================================

    def _open_appsfolder_item(
        self,
        target
    ):

        target_name = self.normalize(
            target
        )

        if not target_name:
            return None

        # -------------------------------------------------
        # PowerShell script
        #
        # Search shell:AppsFolder and invoke actual
        # Open verb.
        # -------------------------------------------------

        script = r'''
$ErrorActionPreference = "SilentlyContinue"

$target = $env:VYOM_TARGET

try {

    $shell = New-Object -ComObject Shell.Application

    $folder = $shell.Namespace("shell:AppsFolder")

    if ($folder -ne $null) {

        $best = $null
        $bestScore = -1

        foreach ($item in $folder.Items()) {

            if ($item -eq $null) {
                continue
            }

            $name = [string]$item.Name

            if ([string]::IsNullOrWhiteSpace($name)) {
                continue
            }

            $nameClean = $name.ToLower().Trim()

            $targetClean = $target.ToLower().Trim()

            $score = 0

            if ($nameClean -eq $targetClean) {

                $score = 1000

            }
            elseif ($nameClean.StartsWith($targetClean)) {

                $score = 800

            }
            elseif ($nameClean.Contains($targetClean)) {

                $score = 600

            }

            if ($score -gt $bestScore) {

                $best = $item
                $bestScore = $score

            }
        }

        if ($best -ne $null -and $bestScore -gt 0) {

            $best.InvokeVerb("open")

            Write-Output "OPENED`t$($best.Name)`t$($best.Path)"

            exit 0
        }
    }

}
catch {

}

exit 1
'''

        try:

            env = os.environ.copy()

            env[
                "VYOM_TARGET"
            ] = target_name

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
                universal_newlines=True,
                env=env
            )

            stdout, stderr = (
                process.communicate(
                    timeout=20
                )
            )

            for line in stdout.splitlines():

                line = line.strip()

                if line.startswith(
                    "OPENED\t"
                ):

                    parts = line.split(
                        "\t"
                    )

                    app_name = (
                        parts[1]
                        if len(parts) > 1
                        else target
                    )

                    app_path = (
                        parts[2]
                        if len(parts) > 2
                        else ""
                    )

                    return {
                        "name": app_name,
                        "path": app_path
                    }

        except Exception:
            pass

        return None

    # =====================================================
    # GET START APPS
    # =====================================================

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

            stdout, stderr = (
                process.communicate(
                    timeout=20
                )
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
                        "path":
                            "shell:AppsFolder\\"
                            + app_id
                    }
                )

            return apps

        except Exception:

            return []

    # =====================================================
    # GET APPSFOLDER APPS
    #
    # COM enumeration.
    # =====================================================

    def get_appsfolder_apps(
        self,
        force=False
    ):

        now = time.time()

        if (
            not force
            and
            self._windows_apps_cache is not None
            and
            (
                now
                -
                self._windows_apps_cache_time
            )
            < self.app_cache_seconds
        ):

            return list(
                self._windows_apps_cache
            )

        script = r'''
$ErrorActionPreference = "SilentlyContinue"

try {

    $shell = New-Object -ComObject Shell.Application

    $folder = $shell.Namespace("shell:AppsFolder")

    if ($folder -ne $null) {

        foreach ($item in $folder.Items()) {

            try {

                $name = [string]$item.Name
                $path = [string]$item.Path

                if ($name) {

                    Write-Output (
                        $name + "`t" + $path
                    )
                }

            }
            catch {

            }
        }
    }

}
catch {

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

            stdout, stderr = (
                process.communicate(
                    timeout=25
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

                name = parts[0].strip()

                path = parts[1].strip()

                if not name:
                    continue

                self._add_unique(
                    apps,
                    {
                        "name": name,
                        "app_id": "",
                        "path": path
                    }
                )

        except Exception:
            pass

        self._windows_apps_cache = list(
            apps
        )

        self._windows_apps_cache_time = (
            time.time()
        )

        return apps

    # =====================================================
    # SEARCH WINDOWS APPS
    # =====================================================

    def search_windows_apps(
        self,
        target
    ):

        target_name = self.normalize(
            target
        )

        if not target_name:
            return []

        all_apps = []

        # -------------------------------------------------
        # 1. Get-StartApps
        # -------------------------------------------------

        for app in self.get_start_apps():

            self._add_unique(
                all_apps,
                app
            )

        # -------------------------------------------------
        # 2. AppsFolder COM
        # -------------------------------------------------

        for app in self.get_appsfolder_apps():

            self._add_unique(
                all_apps,
                app
            )

        # -------------------------------------------------
        # EXACT
        # -------------------------------------------------

        exact = []

        partial = []

        for app in all_apps:

            app_name = self.normalize(
                app.get(
                    "name",
                    ""
                )
            )

            if not app_name:
                continue

            if app_name == target_name:

                exact.append(
                    app
                )

            elif target_name in app_name:

                partial.append(
                    app
                )

        results = []

        for app in (
            exact
            +
            partial
        ):

            self._add_unique(
                results,
                app
            )

        return results[
            :self.max_results
        ]

    # =====================================================
    # OPEN WINDOWS APP
    #
    # DIRECT AppsFolder InvokeVerb FIRST.
    # =====================================================

    def open_windows_app(
        self,
        target
    ):

        # -------------------------------------------------
        # IMPORTANT:
        # Direct COM launch first.
        #
        # This avoids the old false "success" problem.
        # -------------------------------------------------

        direct = (
            self._open_appsfolder_item(
                target
            )
        )

        if direct:

            return (
                True,
                "Opened Windows app: "
                + direct.get(
                    "name",
                    target
                )
            )

        # -------------------------------------------------
        # Search apps
        # -------------------------------------------------

        results = (
            self.search_windows_apps(
                target
            )
        )

        if not results:
            return None

        # -------------------------------------------------
        # Exact result
        # -------------------------------------------------

        target_name = self.normalize(
            target
        )

        exact = []

        for app in results:

            if (
                self.normalize(
                    app.get(
                        "name",
                        ""
                    )
                )
                ==
                target_name
            ):

                exact.append(
                    app
                )

        # -------------------------------------------------
        # Try exact AppID paths
        # -------------------------------------------------

        if exact:

            for app in exact:

                app_path = app.get(
                    "path",
                    ""
                )

                if (
                    app_path
                    and
                    app_path.lower().startswith(
                        "shell:appsfolder"
                    )
                ):

                    if self._launch_appsfolder_path(
                        app_path
                    ):

                        return (
                            True,
                            "Opened Windows app: "
                            + app.get(
                                "name",
                                target
                            )
                        )

        # -------------------------------------------------
        # One result
        # -------------------------------------------------

        if len(results) == 1:

            app = results[0]

            app_path = app.get(
                "path",
                ""
            )

            if app_path:

                if app_path.lower().startswith(
                    "shell:appsfolder"
                ):

                    if self._launch_appsfolder_path(
                        app_path
                    ):

                        return (
                            True,
                            "Opened Windows app: "
                            + app.get(
                                "name",
                                target
                            )
                        )

                success, message = (
                    self._open(
                        app_path
                    )
                )

                if success:

                    return (
                        True,
                        "Opened Windows app: "
                        + app.get(
                            "name",
                            target
                        )
                    )

        # -------------------------------------------------
        # Multiple results
        # -------------------------------------------------

        message = (
            "Multiple Windows apps found "
            "for '{}':\n"
            .format(target)
        )

        for index, app in enumerate(
            results,
            start=1
        ):

            message += (
                "{}. {}\n".format(
                    index,
                    app.get(
                        "name",
                        "Unknown"
                    )
                )
            )

        message += (
            "\nPlease select a number."
        )

        return (
            False,
            message,
            results
        )

    # =====================================================
    # START MENU SEARCH
    # =====================================================

    def search_start_menu(
        self,
        target
    ):

        target_name = self.normalize(
            target
        )

        if not target_name:
            return []

        exact = []

        partial = []

        for start_path in (
            self.start_menu_paths
        ):

            if not os.path.exists(
                start_path
            ):
                continue

            try:

                for root, dirs, files in os.walk(
                    start_path
                ):

                    for file in files:

                        lower = file.lower()

                        if not lower.endswith(
                            (
                                ".lnk",
                                ".exe",
                                ".bat",
                                ".cmd",
                                ".com"
                            )
                        ):
                            continue

                        filename = os.path.splitext(
                            file
                        )[0].strip()

                        normalized = self.normalize(
                            filename
                        )

                        full_path = os.path.join(
                            root,
                            file
                        )

                        if normalized == target_name:

                            self._add_unique(
                                exact,
                                full_path
                            )

                        elif (
                            target_name
                            in normalized
                        ):

                            self._add_unique(
                                partial,
                                full_path
                            )

            except Exception:
                continue

        return (
            exact
            +
            partial
        )[
            :self.max_results
        ]

    # =====================================================
    # DESKTOP SEARCH
    # =====================================================

    def search_desktop(
        self,
        target
    ):

        target_name = self.normalize(
            target
        )

        if not target_name:
            return []

        results = []

        for desktop in self.desktop_paths:

            if not os.path.exists(
                desktop
            ):
                continue

            try:

                for file in os.listdir(
                    desktop
                ):

                    full_path = os.path.join(
                        desktop,
                        file
                    )

                    name = os.path.splitext(
                        file
                    )[0]

                    normalized = self.normalize(
                        name
                    )

                    if normalized == target_name:

                        self._add_unique(
                            results,
                            full_path
                        )

                    elif target_name in normalized:

                        self._add_unique(
                            results,
                            full_path
                        )

            except Exception:
                continue

        return results[
            :self.max_results
        ]

    # =====================================================
    # PATH SEARCH
    # =====================================================

    def find_in_path(
        self,
        target
    ):

        name = self.normalize(
            target
        )

        if not name:
            return None

        result = shutil.which(
            name
        )

        if result:
            return result

        result = shutil.which(
            name + ".exe"
        )

        if result:
            return result

        return None

    # =====================================================
    # EXACT PATH
    # =====================================================

    def find_exact_path(
        self,
        target
    ):

        target = self.clean_target(
            target
        )

        if not target:
            return None

        if os.path.exists(
            target
        ):

            return target

        return None

    # =====================================================
    # REGISTRY APP PATHS
    #
    # Very important for installed desktop apps.
    # =====================================================

    def search_registry_app_paths(
        self,
        target
    ):

        target_name = self.normalize(
            target
        )

        if not target_name:
            return []

        results = []

        registry_roots = [
            (
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\App Paths"
            ),
            (
                winreg.HKEY_LOCAL_MACHINE,
                r"Software\Microsoft\Windows\CurrentVersion\App Paths"
            ),
            (
                winreg.HKEY_LOCAL_MACHINE,
                r"Software\Wow6432Node\Microsoft\Windows\CurrentVersion\App Paths"
            )
        ]

        for hive, base_key in registry_roots:

            try:

                with winreg.OpenKey(
                    hive,
                    base_key
                ) as key:

                    count = winreg.QueryInfoKey(
                        key
                    )[0]

                    for index in range(
                        count
                    ):

                        try:

                            subkey_name = (
                                winreg.EnumKey(
                                    key,
                                    index
                                )
                            )

                            subkey = winreg.OpenKey(
                                key,
                                subkey_name
                            )

                            try:

                                value, value_type = (
                                    winreg.QueryValueEx(
                                        subkey,
                                        ""
                                    )
                                )

                                if not value:
                                    continue

                                exe_name = (
                                    os.path.splitext(
                                        subkey_name
                                    )[0]
                                )

                                normalized = (
                                    self.normalize(
                                        exe_name
                                    )
                                )

                                if (
                                    normalized
                                    ==
                                    target_name
                                    or
                                    target_name
                                    in normalized
                                ):

                                    if os.path.exists(
                                        value
                                    ):

                                        self._add_unique(
                                            results,
                                            value
                                        )

                            finally:

                                subkey.Close()

                        except Exception:
                            continue

            except Exception:
                continue

        return results[
            :self.max_results
        ]

    # =====================================================
    # PROGRAM FILES SEARCH
    # =====================================================

    def search_program_files(
        self,
        target
    ):

        target_name = self.normalize(
            target
        )

        if not target_name:
            return []

        exact = []

        partial = []

        for base_path in self.program_paths:

            if not os.path.exists(
                base_path
            ):
                continue

            try:

                for root, dirs, files in os.walk(
                    base_path
                ):

                    dirs[:] = [
                        d
                        for d in dirs
                        if d.lower()
                        not in (
                            "cache",
                            "temp",
                            "__pycache__",
                            "logs"
                        )
                    ]

                    for file in files:

                        if not file.lower().endswith(
                            ".exe"
                        ):
                            continue

                        filename = os.path.splitext(
                            file
                        )[0]

                        normalized = self.normalize(
                            filename
                        )

                        full_path = os.path.join(
                            root,
                            file
                        )

                        if normalized == target_name:

                            self._add_unique(
                                exact,
                                full_path
                            )

                        elif target_name in normalized:

                            self._add_unique(
                                partial,
                                full_path
                            )

                    if len(
                        exact
                        +
                        partial
                    ) >= self.max_results:

                        break

            except Exception:
                continue

        return (
            exact
            +
            partial
        )[
            :self.max_results
        ]

    # =====================================================
    # COMMON FILE/FOLDER SEARCH
    # =====================================================

    def search_common_locations(
        self,
        target
    ):

        original = self.clean_target(
            target
        ).lower()

        target_name = self.normalize(
            target
        )

        if not original:
            return []

        exact = []

        partial = []

        for base_path in self.common_paths:

            if not os.path.exists(
                base_path
            ):
                continue

            try:

                for root, dirs, files in os.walk(
                    base_path
                ):

                    # ---------------------------------
                    # FOLDERS
                    # ---------------------------------

                    for directory in dirs:

                        directory_lower = (
                            directory.lower()
                        )

                        full_path = os.path.join(
                            root,
                            directory
                        )

                        if (
                            directory_lower
                            ==
                            original
                        ):

                            self._add_unique(
                                exact,
                                full_path
                            )

                        elif (
                            target_name
                            and
                            target_name
                            in directory_lower
                        ):

                            self._add_unique(
                                partial,
                                full_path
                            )

                    # ---------------------------------
                    # FILES
                    # ---------------------------------

                    for file in files:

                        file_lower = (
                            file.lower()
                        )

                        filename = (
                            os.path.splitext(
                                file_lower
                            )[0]
                        )

                        full_path = os.path.join(
                            root,
                            file
                        )

                        if (
                            file_lower
                            ==
                            original
                        ):

                            self._add_unique(
                                exact,
                                full_path
                            )

                        elif (
                            filename
                            ==
                            target_name
                        ):

                            self._add_unique(
                                exact,
                                full_path
                            )

                        elif (
                            target_name
                            and
                            target_name
                            in filename
                        ):

                            self._add_unique(
                                partial,
                                full_path
                            )

                    if len(
                        exact
                        +
                        partial
                    ) >= self.max_results:

                        break

            except Exception:
                continue

        return (
            exact
            +
            partial
        )[
            :self.max_results
        ]

    # =====================================================
    # FIND EVERYTHING
    # =====================================================

    def find(
        self,
        target
    ):

        target = self.clean_target(
            target
        )

        if not target:
            return []

        results = []

        # -------------------------------------------------
        # 1. Exact path
        # -------------------------------------------------

        exact = self.find_exact_path(
            target
        )

        if exact:
            return [exact]

        # -------------------------------------------------
        # 2. PATH
        # -------------------------------------------------

        path_result = self.find_in_path(
            target
        )

        if path_result:

            self._add_unique(
                results,
                path_result
            )

        # -------------------------------------------------
        # 3. Registry App Paths
        # -------------------------------------------------

        for item in (
            self.search_registry_app_paths(
                target
            )
        ):

            self._add_unique(
                results,
                item
            )

        # -------------------------------------------------
        # 4. Start Menu
        # -------------------------------------------------

        for item in (
            self.search_start_menu(
                target
            )
        ):

            self._add_unique(
                results,
                item
            )

        # -------------------------------------------------
        # 5. Desktop
        # -------------------------------------------------

        for item in (
            self.search_desktop(
                target
            )
        ):

            self._add_unique(
                results,
                item
            )

        # -------------------------------------------------
        # 6. Program Files
        # -------------------------------------------------

        for item in (
            self.search_program_files(
                target
            )
        ):

            self._add_unique(
                results,
                item
            )

        # -------------------------------------------------
        # 7. Common files/folders
        # -------------------------------------------------

        for item in (
            self.search_common_locations(
                target
            )
        ):

            self._add_unique(
                results,
                item
            )

        return results[
            :self.max_results
        ]

    # =====================================================
    # ALL SEARCH NAMES
    #
    # Used for spelling suggestions.
    # =====================================================

    def get_all_search_names(self):

        names = []

        # -------------------------------------------------
        # Start Menu names
        # -------------------------------------------------

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

                        if file.lower().endswith(
                            (
                                ".lnk",
                                ".exe",
                                ".bat",
                                ".cmd",
                                ".com"
                            )
                        ):

                            name = os.path.splitext(
                                file
                            )[0].strip()

                            if name:
                                names.append(
                                    name
                                )

            except Exception:
                continue

        # -------------------------------------------------
        # Desktop
        # -------------------------------------------------

        for desktop in self.desktop_paths:

            if not os.path.exists(
                desktop
            ):
                continue

            try:

                for file in os.listdir(
                    desktop
                ):

                    name = os.path.splitext(
                        file
                    )[0]

                    if name:
                        names.append(
                            name
                        )

            except Exception:
                continue

        # -------------------------------------------------
        # Windows Start Apps
        # -------------------------------------------------

        for app in self.get_start_apps():

            if app.get("name"):

                names.append(
                    app["name"]
                )

        # -------------------------------------------------
        # AppsFolder
        # -------------------------------------------------

        for app in self.get_appsfolder_apps():

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

            key = self.normalize(
                name
            )

            if not key:
                continue

            if key not in seen:

                seen.add(key)

                unique.append(
                    name
                )

        return unique

    # =====================================================
    # SIMILAR NAME SEARCH
    # =====================================================

    def find_similar(
        self,
        target,
        limit=8
    ):

        target_name = self.normalize(
            target
        )

        if not target_name:
            return []

        names = (
            self.get_all_search_names()
        )

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
        # Direct substring suggestions first
        # -------------------------------------------------

        direct = []

        for candidate in candidates:

            if (
                target_name
                in candidate
                or
                candidate
                in target_name
            ):

                direct.append(
                    candidate
                )

        # -------------------------------------------------
        # Fuzzy suggestions
        # -------------------------------------------------

        fuzzy = difflib.get_close_matches(
            target_name,
            candidates,
            n=limit,
            cutoff=0.30
        )

        combined = []

        for item in (
            direct
            +
            fuzzy
        ):

            if item not in combined:

                combined.append(
                    item
                )

        results = []

        for item in combined:

            display = (
                normalized_map.get(
                    item,
                    item
                )
            )

            if display not in results:

                results.append(
                    display
                )

            if len(results) >= limit:

                break

        return results

    # =====================================================
    # SUGGESTION MESSAGE
    # =====================================================

    def suggestion_message(
        self,
        target,
        suggestions
    ):

        if not suggestions:

            return (
                "I could not find "
                "'{}'.".format(
                    target
                )
            )

        message = (
            "I could not find "
            "'{}'.\n\n"
            "Did you mean:\n"
            .format(
                target
            )
        )

        for index, name in enumerate(
            suggestions,
            start=1
        ):

            message += (
                "{}. {}\n".format(
                    index,
                    name
                )
            )

        message += (
            "\nPlease select a number."
        )

        return message

    # =====================================================
    # OPEN
    # =====================================================

    def open(
        self,
        target
    ):

        target = self.clean_target(
            target
        )

        if not target:

            return (
                "Please tell me what "
                "you want to open."
            )

        # -------------------------------------------------
        # 1. EXACT REAL PATH
        # -------------------------------------------------

        exact = self.find_exact_path(
            target
        )

        if exact:

            success, message = (
                self._open(
                    exact
                )
            )

            if success:
                return message

        # -------------------------------------------------
        # 2. WINDOWS APPSFOLDER DIRECT
        #
        # THIS MUST COME EARLY.
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

                return windows_app_result[1]

        # -------------------------------------------------
        # 3. NORMAL FILE / FOLDER / EXE / LNK
        # -------------------------------------------------

        results = self.find(
            target
        )

        # -------------------------------------------------
        # Exact/one
        # -------------------------------------------------

        if len(results) == 1:

            success, message = (
                self._open(
                    results[0]
                )
            )

            if success:

                return message

        # -------------------------------------------------
        # Multiple
        # -------------------------------------------------

        if len(results) > 1:

            message = (
                "Multiple items found "
                "for '{}':\n".format(
                    target
                )
            )

            for index, path in enumerate(
                results,
                start=1
            ):

                message += (
                    "{}. {}\n".format(
                        index,
                        path
                    )
                )

            message += (
                "\nPlease select a number."
            )

            return message

        # -------------------------------------------------
        # 4. SIMILAR SPELLING
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

    # =====================================================
    # SEARCH AND OPEN
    # =====================================================

    def search_and_open(
        self,
        target
    ):

        return self.open(
            target
        )

    # =====================================================
    # OPEN SELECTED RESULT
    # =====================================================

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

            app_name = selected.get(
                "name",
                "Windows app"
            )

            app_path = selected.get(
                "path",
                ""
            )

            # ---------------------------------------------
            # Try direct AppsFolder COM by name
            # ---------------------------------------------

            direct = (
                self._open_appsfolder_item(
                    app_name
                )
            )

            if direct:

                return (
                    "Opened Windows app: "
                    + direct.get(
                        "name",
                        app_name
                    )
                )

            # ---------------------------------------------
            # Try path
            # ---------------------------------------------

            if app_path:

                if app_path.lower().startswith(
                    "shell:appsfolder"
                ):

                    if self._launch_appsfolder_path(
                        app_path
                    ):

                        return (
                            "Opened Windows app: "
                            + app_name
                        )

                success, message = (
                    self._open(
                        app_path
                    )
                )

                if success:
                    return message

            return (
                "Could not open Windows app: "
                + app_name
            )

        # -------------------------------------------------
        # Normal path
        # -------------------------------------------------

        success, message = (
            self._open(
                selected
            )
        )

        return message

    # =====================================================
    # OPEN SUGGESTION
    # =====================================================

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
