# ============================================================
# Project : Vyom AI
# Module  : universal_app_launcher.py
# Version : 1.0
#
# Purpose:
#     Universal Windows Application Launcher
#
# Designed for:
#     Windows 8 / 8.1 / 10 / 11
#
# Handles:
#     - Start Menu applications
#     - User Start Menu
#     - All Users Start Menu
#     - .LNK shortcuts
#     - .EXE applications
#     - .BAT / .CMD applications
#     - AppsFolder
#     - Windows Modern / Store Apps
#     - AppID / AUMID
#     - PATH applications
#     - Program Files
#     - Program Files (x86)
#     - PowerShell Get-StartApps
#     - PowerShell Get-AppxPackage
#     - Windows Shell launching
#     - Multiple fallback launch methods
#     - Duplicate removal
#     - Fuzzy spelling suggestions
#     - Numbered selection
#
# IMPORTANT:
#     This module is independent from UniversalResolver.
# ============================================================

import os
import sys
import subprocess
import ctypes
import shutil
import difflib
import re
import time

try:
    from tools.app_registry import find_application
except Exception:
    find_application = None


class UniversalAppLauncher:

    # ========================================================
    # INITIALIZATION
    # ========================================================

    def __init__(self):

        self.max_results = 30
        self.max_suggestions = 8

        self.user_profile = os.environ.get(
            "USERPROFILE",
            ""
        )

        self.appdata = os.environ.get(
            "APPDATA",
            ""
        )

        self.program_data = os.environ.get(
            "PROGRAMDATA",
            ""
        )

        self.program_files = os.environ.get(
            "ProgramFiles",
            ""
        )

        self.program_files_x86 = os.environ.get(
            "ProgramFiles(x86)",
            ""
        )

        # ----------------------------------------------------
        # START MENU LOCATIONS
        # ----------------------------------------------------

        self.start_menu_paths = []

        if self.appdata:

            self.start_menu_paths.append(
                os.path.join(
                    self.appdata,
                    "Microsoft",
                    "Windows",
                    "Start Menu",
                    "Programs"
                )
            )

        if self.program_data:

            self.start_menu_paths.append(
                os.path.join(
                    self.program_data,
                    "Microsoft",
                    "Windows",
                    "Start Menu",
                    "Programs"
                )
            )

        # ----------------------------------------------------
        # DESKTOP LOCATIONS
        # ----------------------------------------------------

        self.desktop_paths = []

        if self.user_profile:

            self.desktop_paths.append(
                os.path.join(
                    self.user_profile,
                    "Desktop"
                )
            )

        if self.program_data:

            self.desktop_paths.append(
                os.path.join(
                    self.program_data,
                    "Desktop"
                )
            )

        # ----------------------------------------------------
        # APPLICATION EXTENSIONS
        # ----------------------------------------------------

        self.app_extensions = (
            ".exe",
            ".com",
            ".bat",
            ".cmd",
            ".lnk"
        )

        # ----------------------------------------------------
        # INTERNAL CACHE
        # ----------------------------------------------------

        self._cache = []
        self._cache_time = 0

        # Cache for 60 seconds
        self.cache_seconds = 60

    # ========================================================
    # NORMALIZE
    # ========================================================

    def normalize(self, value):

        if value is None:

            return ""

        value = str(value)

        value = value.strip()

        value = value.strip('"')

        value = value.strip("'")

        value = value.lower()

        # Remove common executable extensions
        for ext in (
            ".exe",
            ".lnk",
            ".bat",
            ".cmd",
            ".com"
        ):

            if value.endswith(ext):

                value = value[:-len(ext)]

        # Replace separators
        value = value.replace("_", " ")
        value = value.replace("-", " ")

        # Remove repeated spaces
        value = re.sub(
            r"\s+",
            " ",
            value
        )

        return value.strip()

    # ========================================================
    # CLEAN INPUT
    # ========================================================

    def clean_target(self, target):

        if target is None:

            return ""

        target = str(target)

        target = target.strip()

        target = target.strip('"')

        target = target.strip("'")

        return target.strip()

    # ========================================================
    # IS WINDOWS
    # ========================================================

    def is_windows(self):

        return os.name == "nt"

    # ========================================================
    # ADD RESULT WITHOUT DUPLICATE
    # ========================================================

    def _add_result(
        self,
        results,
        item
    ):

        if not item:
            return

        if not isinstance(item, dict):
            item = {
                "name": os.path.basename(str(item)),
                "path": str(item),
                "app_id": "",
                "aumid": "",
                "type": "unknown"
            }

        name = str(
            item.get("name", "")
        ).strip()

        path = str(
            item.get("path", "")
        ).strip()

        app_id = str(
            item.get("app_id", "")
        ).strip()

        aumid = str(
            item.get("aumid", "")
        ).strip()

        # ----------------------------------------------------
        # NORMALIZED VALUES
        # ----------------------------------------------------

        name_key = self.normalize(name)

        path_key = path.lower()

        app_id_key = app_id.lower()

        aumid_key = aumid.lower()

        # ----------------------------------------------------
        # DUPLICATE CHECK
        #
        # Same physical file/path = duplicate
        # Same AUMID/AppID = duplicate application
        #
        # IMPORTANT:
        # Same filename in different folders is NOT duplicate.
        # User must be able to select between them.
        # ----------------------------------------------------

        for existing in results:

            if not isinstance(existing, dict):
                continue

            existing_path = str(
                existing.get("path", "")
            ).strip().lower()

            existing_app_id = str(
                existing.get("app_id", "")
            ).strip().lower()

            existing_aumid = str(
                existing.get("aumid", "")
            ).strip().lower()

            # Same real path
            if (
                path_key
                and existing_path
                and path_key == existing_path
            ):
                return

            # Same application ID
            if (
                app_id_key
                and existing_app_id
                and app_id_key == existing_app_id
            ):
                return

            if (
                aumid_key
                and existing_aumid
                and aumid_key == existing_aumid
            ):
                return

        # ----------------------------------------------------
        # DO NOT REMOVE SAME-NAME FILES
        #
        # Example:
        #
        # Desktop\10th.jpg
        # Documents\10th.jpg
        #
        # Both must remain selectable.
        # ----------------------------------------------------

        results.append(item)

    # ========================================================
    # START MENU SCAN
    # ========================================================

    def scan_start_menu(self):

        results = []

        for base in self.start_menu_paths:

            if not os.path.exists(base):

                continue

            try:

                for root, dirs, files in os.walk(
                    base,
                    onerror=lambda e: None
                ):

                    for file_name in files:

                        lower = file_name.lower()

                        if not lower.endswith(
                            self.app_extensions
                        ):

                            continue

                        full_path = os.path.join(
                            root,
                            file_name
                        )

                        name = os.path.splitext(
                            file_name
                        )[0].strip()

                        if not name:

                            continue

                        result = {
                            "name": name,
                            "path": full_path,
                            "app_id": "",
                            "aumid": "",
                            "type": "start_menu"
                        }

                        self._add_result(
                            results,
                            result
                        )

            except (
                PermissionError,
                OSError
            ):

                continue

        return results

    # ========================================================
    # DESKTOP APPLICATION SCAN
    # ========================================================

    def scan_desktop(self):

        results = []

        for base in self.desktop_paths:

            if not os.path.exists(base):

                continue

            try:

                for root, dirs, files in os.walk(
                    base,
                    onerror=lambda e: None
                ):

                    for file_name in files:

                        lower = file_name.lower()

                        if not lower.endswith(
                            self.app_extensions
                        ):

                            continue

                        full_path = os.path.join(
                            root,
                            file_name
                        )

                        name = os.path.splitext(
                            file_name
                        )[0].strip()

                        if not name:

                            continue

                        result = {
                            "name": name,
                            "path": full_path,
                            "app_id": "",
                            "aumid": "",
                            "type": "desktop"
                        }

                        self._add_result(
                            results,
                            result
                        )

            except (
                PermissionError,
                OSError
            ):

                continue

        return results

        # ========================================================
    # GET START APPS
    #
    # Windows 8 / 8.1 SAFE VERSION
    #
    # Get-StartApps is not required here.
    # AppsFolder is used as the primary Windows Shell source.
    # ========================================================

    def get_start_apps(self):

        if not self.is_windows():

            return []

        script = r'''
$ErrorActionPreference = "SilentlyContinue"

try {

    $shell = New-Object -ComObject Shell.Application

    $folder = $shell.Namespace(
        "shell:::{4234d49b-0245-4df3-b780-3893943456e1}"
    )

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

        try:

            process = subprocess.Popen(
                [
                    "powershell.exe",
                    "-NoProfile",
                    "-NonInteractive",
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
                timeout=30
            )

            results = []

            for line in stdout.splitlines():

                line = line.rstrip()

                if not line:

                    continue

                parts = line.split(
                    "\t",
                    1
                )

                if len(parts) == 1:

                    name = parts[0].strip()
                    path = ""

                else:

                    name = parts[0].strip()
                    path = parts[1].strip()

                if not name:

                    continue

                results.append(
                    {
                        "name": name,
                        "path": path,
                        "app_id": "",
                        "aumid": path,
                        "type": "start_app"
                    }
                )

            return results

        except (
            subprocess.TimeoutExpired,
            OSError,
            Exception
        ):

            return []

    # ========================================================
    # APPSFOLDER DISCOVERY
    #
    # This is extremely important for Windows 8/8.1.
    #
    # Uses Shell.Application COM through PowerShell.
    # ========================================================

    def get_appsfolder_apps(self):

        if not self.is_windows():

            return []

        script = r'''
$ErrorActionPreference = "SilentlyContinue"

try {

    $shell = New-Object -ComObject Shell.Application

    $folder = $shell.Namespace(
        "shell:AppsFolder"
    )

    if ($folder -ne $null) {

        foreach ($item in $folder.Items()) {

            try {

                $name = $item.Name
                $path = $item.Path

                if ($name) {

                    if ($path) {

                        Write-Output (
                            $name + "`t" + $path
                        )

                    }
                    else {

                        Write-Output (
                            $name + "`t"
                        )
                    }
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

        try:

            process = subprocess.Popen(
                [
                    "powershell.exe",
                    "-NoProfile",
                    "-NonInteractive",
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
                timeout=30
            )

            results = []

            for line in stdout.splitlines():

                line = line.rstrip()

                if not line:

                    continue

                parts = line.split(
                    "\t",
                    1
                )

                if len(parts) == 1:

                    name = parts[0].strip()

                    path = ""

                else:

                    name = parts[0].strip()

                    path = parts[1].strip()

                if not name:

                    continue

                results.append(
                    {
                        "name": name,
                        "path": path,
                        "app_id": "",
                        "aumid": "",
                        "type": "appsfolder"
                    }
                )

            return results

        except (
            subprocess.TimeoutExpired,
            OSError,
            Exception
        ):

            return []

    # ========================================================
    # APPX PACKAGE DISCOVERY
    #
    # Finds installed Windows Store / Modern applications.
    # ========================================================

    def get_appx_apps(self):

        if not self.is_windows():

            return []

        script = r'''
$ErrorActionPreference = "SilentlyContinue"

try {

    if (Get-Command Get-AppxPackage -ErrorAction SilentlyContinue) {

        Get-AppxPackage | ForEach-Object {

            $package = $_

            $manifestPath = Join-Path `
                $package.InstallLocation `
                "AppxManifest.xml"

            if (Test-Path $manifestPath) {

                try {

                    [xml]$xml = Get-Content `
                        -LiteralPath $manifestPath

                    $applications = `
                        $xml.Package.Applications.Application

                    foreach ($application in $applications) {

                        $appId = `
                            [string]$application.Id

                        $displayName = `
                            [string]$application.VisualElements.DisplayName

                        if (-not $displayName) {

                            $displayName = `
                                [string]$application.Id
                        }

                        if ($appId) {

                            $aumid = `
                                $package.PackageFamilyName `
                                + "!" `
                                + $appId

                            Write-Output (
                                $displayName `
                                + "`t" `
                                + $aumid
                            )
                        }
                    }

                }
                catch {

                }
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
                    "-NonInteractive",
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
                timeout=45
            )

            results = []

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

                aumid = parts[1].strip()

                if not name or not aumid:

                    continue

                results.append(
                    {
                        "name": name,
                        "path": (
                            "shell:AppsFolder\\"
                            + aumid
                        ),
                        "app_id": aumid,
                        "aumid": aumid,
                        "type": "appx"
                    }
                )

            return results

        except (
            subprocess.TimeoutExpired,
            OSError,
            Exception
        ):

            return []

    # ========================================================
    # PATH APPLICATION
    # ========================================================

    def find_path_application(
        self,
        target
    ):

        name = self.clean_target(
            target
        )

        if not name:

            return None

        # Direct PATH
        result = shutil.which(name)

        if result:

            return result

        # EXE
        result = shutil.which(
            name + ".exe"
        )

        if result:

            return result

        # COM
        result = shutil.which(
            name + ".com"
        )

        if result:

            return result

        return None

    # ========================================================
    # PROGRAM FILES APPLICATION SCAN
    #
    # Used as fallback.
    # ========================================================

    def scan_program_files(
        self,
        target=None
    ):

        results = []

        target_name = ""

        if target:

            target_name = self.normalize(
                target
            )

        bases = []

        if self.program_files:

            bases.append(
                self.program_files
            )

        if self.program_files_x86:

            bases.append(
                self.program_files_x86
            )

        for base in bases:

            if not os.path.exists(base):

                continue

            try:

                for root, dirs, files in os.walk(
                    base,
                    onerror=lambda e: None
                ):

                    # Avoid huge cache folders
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

                    for file_name in files:

                        lower = file_name.lower()

                        if not lower.endswith(
                            ".exe"
                        ):

                            continue

                        name = os.path.splitext(
                            file_name
                        )[0]

                        if (
                            target_name
                            and
                            self.normalize(name)
                            != target_name
                            and
                            target_name
                            not in self.normalize(name)
                        ):

                            continue

                        full_path = os.path.join(
                            root,
                            file_name
                        )

                        result = {
                            "name": name,
                            "path": full_path,
                            "app_id": "",
                            "aumid": "",
                            "type": "program_files"
                        }

                        self._add_result(
                            results,
                            result
                        )

                        if len(results) >= self.max_results:

                            return results

            except (
                PermissionError,
                OSError
            ):

                continue

        return results

    # ========================================================
    # BUILD APPLICATION DATABASE
    # ========================================================

    def build_database(
        self,
        force=False
    ):

        now = time.time()

        if (
            not force
            and
            self._cache
            and
            now - self._cache_time
            < self.cache_seconds
        ):

            return self._cache

        results = []

        # ----------------------------------------------------
        # 1. Start Menu LNK / EXE
        # ----------------------------------------------------

        for item in self.scan_start_menu():

            self._add_result(
                results,
                item
            )

        # ----------------------------------------------------
        # 2. Desktop applications
        # ----------------------------------------------------

        for item in self.scan_desktop():

            self._add_result(
                results,
                item
            )

        # ----------------------------------------------------
        # 3. Get-StartApps / AUMID
        # ----------------------------------------------------

        for item in self.get_start_apps():

            self._add_result(
                results,
                item
            )

        # ----------------------------------------------------
        # 4. AppsFolder
        # ----------------------------------------------------

        for item in self.get_appsfolder_apps():

            self._add_result(
                results,
                item
            )

        # ----------------------------------------------------
        # 5. AppX
        # ----------------------------------------------------

        for item in self.get_appx_apps():

            self._add_result(
                results,
                item
            )

        self._cache = results

        self._cache_time = now

        return results

    # ========================================================
    # SEARCH
    # ========================================================

    def search(
        self,
        target,
        force_refresh=False
    ):

        target = self.clean_target(target)

        if not target:
            return []

        target_normalized = self.normalize(target)

        # ----------------------------------------------------
        # FAST PATH
        #
        # Normal commands such as Chrome/Notepad should never
        # wait for several PowerShell/AppsFolder scans.
        # First check sources that are fast and deterministic.
        # ----------------------------------------------------
        exact = []
        partial = []

        # 1. Windows App Paths registry (very fast when available)
        if find_application is not None:
            try:
                registry_path = find_application(target)
            except Exception:
                registry_path = None

            if registry_path:
                name = os.path.splitext(os.path.basename(registry_path))[0]
                self._add_result(
                    exact,
                    {
                        "name": name,
                        "path": registry_path,
                        "app_id": "",
                        "aumid": "",
                        "type": "registry"
                    }
                )

        # 2. PATH executable
        try:
            path_result = self.find_path_application(target)
        except Exception:
            path_result = None

        if path_result:
            path_name = os.path.splitext(os.path.basename(path_result))[0]
            item = {
                "name": path_name,
                "path": path_result,
                "app_id": "",
                "aumid": "",
                "type": "path"
            }
            if self.normalize(path_name) == target_normalized:
                self._add_result(exact, item)
            else:
                self._add_result(partial, item)

        # 3. Start Menu and Desktop are cheap compared with the
        # PowerShell/AppsFolder discovery path.
        try:
            quick_sources = [
                self.scan_start_menu(),
                self.scan_desktop(),
            ]
        except Exception:
            quick_sources = []

        for source_items in quick_sources:
            for app in source_items:
                if not isinstance(app, dict):
                    continue

                app_name = self.normalize(app.get("name", ""))
                if not app_name:
                    continue

                if app_name == target_normalized:
                    self._add_result(exact, app)
                elif target_normalized in app_name:
                    self._add_result(partial, app)

        # Exact match is enough to continue immediately. This is the
        # critical fix for the apparent voice-mode freeze.
        if exact:
            return exact[:self.max_results]

        # If quick sources produced meaningful partial matches, return
        # them before invoking slow system discovery.
        if partial:
            return partial[:self.max_results]

        # ----------------------------------------------------
        # SLOW FALLBACK
        #
        # Used only when the fast sources did not find anything.
        # Existing discovery behaviour is preserved here.
        # ----------------------------------------------------
        database = self.build_database(
            force=force_refresh
        )

        exact = []
        partial = []

        for app in database:
            if not isinstance(app, dict):
                continue

            app_name = self.normalize(app.get("name", ""))
            if not app_name:
                continue

            if app_name == target_normalized:
                self._add_result(exact, app)
            elif target_normalized in app_name:
                self._add_result(partial, app)

        # Program Files is intentionally last because recursive disk
        # scanning can be expensive on the user's older HDD.
        if not exact:
            try:
                program_results = self.scan_program_files(target)
            except Exception:
                program_results = []

            for item in program_results:
                item_name = self.normalize(item.get("name", ""))
                if item_name == target_normalized:
                    self._add_result(exact, item)
                elif target_normalized in item_name:
                    self._add_result(partial, item)

        results = []
        for item in exact:
            self._add_result(results, item)
        for item in partial:
            self._add_result(results, item)

        return results[:self.max_results]

    # ========================================================
    # FIND SIMILAR APPLICATIONS
    # ========================================================

    def find_similar(
        self,
        target,
        limit=None
    ):

        if limit is None:

            limit = self.max_suggestions

        target = self.clean_target(
            target
        )

        normalized_target = self.normalize(
            target
        )

        if not normalized_target:

            return []

        database = self.build_database()

        mapping = {}

        for app in database:

            name = app.get(
                "name",
                ""
            )

            normalized = self.normalize(
                name
            )

            if not normalized:

                continue

            if normalized not in mapping:

                mapping[
                    normalized
                ] = name

        candidates = list(
            mapping.keys()
        )

        # ----------------------------------------------------
        # difflib matching
        # ----------------------------------------------------

        matches = difflib.get_close_matches(
            normalized_target,
            candidates,
            n=limit,
            cutoff=0.30
        )

        results = []

        for match in matches:

            name = mapping.get(
                match,
                match
            )

            if name not in results:

                results.append(name)

        # ----------------------------------------------------
        # Additional substring/word similarity
        # ----------------------------------------------------

        if len(results) < limit:

            words = normalized_target.split()

            for normalized_name in candidates:

                if normalized_name in results:

                    continue

                score = 0

                for word in words:

                    if word in normalized_name:

                        score += 1

                if score > 0:

                    results.append(
                        mapping[
                            normalized_name
                        ]
                    )

                if len(results) >= limit:

                    break

        return results[:limit]

    # ========================================================
    # SHELLEXECUTE
    # ========================================================

    def shell_execute(
        self,
        target,
        arguments=None
    ):

        if not self.is_windows():

            return False

        try:

            result = (
                ctypes.windll.shell32.ShellExecuteW(
                    None,
                    "open",
                    str(target),
                    arguments,
                    None,
                    1
                )
            )

            return result > 32

        except Exception:

            return False

    # ========================================================
    # OPEN NORMAL PATH
    # ========================================================

    def open_normal_path(
        self,
        path
    ):

        if not path:
            return False

        path = str(path).strip()

        if not path:
            return False

        # ----------------------------------------------------
        # 1. EXISTING FILE / FOLDER
        #
        # Windows default application handles:
        # JPG
        # JPEG
        # PNG
        # GIF
        # BMP
        # PDF
        # MP3
        # MP4
        # DOC/DOCX
        # XLS/XLSX
        # ZIP
        # FOLDERS
        # etc.
        # ----------------------------------------------------

        try:

            if os.path.exists(path):

                os.startfile(path)

                return True

        except Exception:
            pass

        # ----------------------------------------------------
        # 2. SHELL EXECUTE
        # ----------------------------------------------------

        try:

            if self.shell_execute(path):

                return True

        except Exception:
            pass

        # ----------------------------------------------------
        # 3. CMD START
        #
        # Important for folders and file associations.
        # ----------------------------------------------------

        try:

            if os.path.exists(path):

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

                return True

        except Exception:
            pass

        return False

        # ========================================================
    # OPEN APPSFOLDER ITEM BY NAME
    #
    # Windows 8 / 8.1 compatible
    #
    # Process:
    #
    #   1. Search Shell AppsFolder
    #   2. Find application by name
    #   3. Read application Path / AUMID
    #   4. Launch through explorer.exe
    # ========================================================

    def open_appsfolder_by_name(
        self,
        target
    ):

        if not self.is_windows():

            return False

        target = self.clean_target(
            target
        )

        if not target:

            return False

        safe_target = target.replace(
            "'",
            "''"
        )

        script = r"""
$ErrorActionPreference = "SilentlyContinue"

$target = '__TARGET__'

try {

    $shell = New-Object -ComObject Shell.Application

    $folder = $shell.Namespace(
        "shell:::{4234d49b-0245-4df3-b780-3893943456e1}"
    )

    if ($folder -eq $null) {

        exit 2
    }

    foreach ($item in $folder.Items()) {

        try {

            $name = [string]$item.Name
            $path = [string]$item.Path

            if (
                $name -and
                $name.Equals(
                    $target,
                    [System.StringComparison]::OrdinalIgnoreCase
                )
            ) {

                if ($path) {

                    Write-Output $path

                    exit 0
                }
            }

        }
        catch {

        }
    }

}
catch {

}

exit 3
"""

        script = script.replace(
            "__TARGET__",
            safe_target
        )

        try:

            process = subprocess.Popen(
                [
                    "powershell.exe",
                    "-NoProfile",
                    "-NonInteractive",
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
                timeout=30
            )

            if process.returncode != 0:

                return False

            app_path = ""

            for line in stdout.splitlines():

                line = line.strip()

                if line:

                    app_path = line

                    break

            if not app_path:

                return False

            prefix = "shell:AppsFolder\\"

            if app_path.lower().startswith(
                prefix.lower()
            ):

                app_id = app_path[
                    len(prefix):
                ]

                return self.open_by_aumid(
                    app_id
                )

            if "!" in app_path:

                return self.open_by_aumid(
                    app_path
                )

            return self.open_normal_path(
                app_path
            )

        except Exception:

            return False


           # ========================================================
    # OPEN BY AUMID / APPID
    #
    # Windows 8 / 8.1 / 10 / 11
    #
    # Primary:
    #     explorer.exe shell:AppsFolder\<AUMID>
    #
    # Fallback:
    #     ShellExecute
    # ========================================================

    def open_by_aumid(
        self,
        app_id
    ):

        if not self.is_windows():

            return False

        app_id = str(
            app_id or ""
        ).strip()

        if not app_id:

            return False

        # ----------------------------------------------------
        # Remove shell:AppsFolder prefix
        # ----------------------------------------------------

        prefix = "shell:AppsFolder\\"

        if app_id.lower().startswith(
            prefix.lower()
        ):

            app_id = app_id[
                len(prefix):
            ]

        if not app_id:

            return False

        shell_target = (
            "shell:AppsFolder\\"
            + app_id
        )

        # ----------------------------------------------------
        # METHOD 1
        #
        # Windows Explorer
        #
        # This is the primary AUMID launch method.
        # ----------------------------------------------------

        try:

            windows_dir = os.environ.get(
                "WINDIR",
                r"C:\Windows"
            )

            explorer_path = os.path.join(
                windows_dir,
                "explorer.exe"
            )

            if os.path.exists(
                explorer_path
            ):

                process = subprocess.Popen(
                    [
                        explorer_path,
                        shell_target
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )

                if process is not None:

                    return True

        except Exception:

            pass

        # ----------------------------------------------------
        # METHOD 2
        #
        # Windows ShellExecute
        # ----------------------------------------------------

        try:

            if self.shell_execute(
                shell_target
            ):

                return True

        except Exception:

            pass

        return False


    # ========================================================
    # OPEN APPLICATION RECORD
    # ========================================================

    def open_record(
        self,
        app
    ):

        if not isinstance(
            app,
            dict
        ):

            return False

        name = str(
            app.get(
                "name",
                ""
            )
        ).strip()

        path = str(
            app.get(
                "path",
                ""
            )
        ).strip()

        app_id = str(
            app.get(
                "app_id",
                ""
            )
        ).strip()

        aumid = str(
            app.get(
                "aumid",
                ""
            )
        ).strip()

        app_type = str(
            app.get(
                "type",
                ""
            )
        ).strip().lower()

        # ----------------------------------------------------
        # 1. REAL FILE / FOLDER
        #
        # JPG / PDF / MP3 / DOC / ZIP / FOLDER etc.
        # ----------------------------------------------------

        if path:

            if (
                not path.lower().startswith(
                    "shell:appsfolder\\"
                )
            ):

                if os.path.exists(path):

                    if self.open_normal_path(
                        path
                    ):

                        return True

        # ----------------------------------------------------
        # 2. AUMID / APPID
        #
        # Modern / Store applications.
        # ----------------------------------------------------

        launch_ids = []

        if aumid:

            launch_ids.append(
                aumid
            )

        if app_id:

            if app_id not in launch_ids:

                launch_ids.append(
                    app_id
                )

        for launch_id in launch_ids:

            if self.open_by_aumid(
                launch_id
            ):

                return True

        # ----------------------------------------------------
        # 3. shell:AppsFolder DIRECT PATH
        # ----------------------------------------------------

        if path:

            prefix = "shell:AppsFolder\\"

            if path.lower().startswith(
                prefix.lower()
            ):

                app_id_from_path = path[
                    len(prefix):
                ]

                if self.open_by_aumid(
                    app_id_from_path
                ):

                    return True

        # ----------------------------------------------------
        # 4. AppsFolder NAME
        #
        # Useful for Windows 8/8.1 applications whose
        # AUMID/path information is incomplete.
        # ----------------------------------------------------

        if (
            app_type
            in (
                "appsfolder",
                "appx",
                "start_app"
            )
        ):

            if name:

                if self.open_appsfolder_by_name(
                    name
                ):

                    return True

        # ----------------------------------------------------
        # 5. FINAL NORMAL PATH FALLBACK
        # ----------------------------------------------------

        if path:

            if self.open_normal_path(
                path
            ):

                return True

        # ----------------------------------------------------
        # 6. FINAL APPLICATION NAME FALLBACK
        # ----------------------------------------------------

        if name:

            if self.open_appsfolder_by_name(
                name
            ):

                return True

        return False
    # ========================================================
    # OPEN
    # ========================================================

    def open(
        self,
        target,
        force_refresh=False
    ):

        target = self.clean_target(
            target
        )

        if not target:

            return {
                "success": False,
                "message": (
                    "Please tell me which "
                    "application to open."
                ),
                "results": [],
                "suggestions": []
            }

        # ----------------------------------------------------
        # Exact filesystem path
        # ----------------------------------------------------

        if os.path.exists(target):

            if self.open_normal_path(
                target
            ):

                return {
                    "success": True,
                    "message": (
                        "Opened successfully: "
                        + target
                    ),
                    "results": [],
                    "suggestions": []
                }

        # ----------------------------------------------------
        # Search applications
        # ----------------------------------------------------

        results = self.search(
            target,
            force_refresh=force_refresh
        )

        # ----------------------------------------------------
        # EXACT / ONE
        # ----------------------------------------------------

        if len(results) == 1:

            selected = results[0]

            if self.open_record(
                selected
            ):

                return {
                    "success": True,
                    "message": (
                        "Opened successfully: "
                        + selected.get(
                            "name",
                            target
                        )
                    ),
                    "results": [
                        selected
                    ],
                    "suggestions": []
                }

            # If first launch mechanism failed,
            # force refresh and try again.
            refreshed = self.search(
                target,
                force_refresh=True
            )

            for item in refreshed:

                if self.open_record(
                    item
                ):

                    return {
                        "success": True,
                        "message": (
                            "Opened successfully: "
                            + item.get(
                                "name",
                                target
                            )
                        ),
                        "results": [
                            item
                        ],
                        "suggestions": []
                    }

        # ----------------------------------------------------
        # MULTIPLE RESULTS
        # ----------------------------------------------------

        if len(results) > 1:

            lines = []

            lines.append(
                "Multiple applications found:"
            )

            lines.append("")

            for index, item in enumerate(
                results,
                start=1
            ):

                name = item.get(
                    "name",
                    "Unknown"
                )

                app_type = item.get(
                    "type",
                    ""
                )

                if app_type:

                    lines.append(
                        str(index)
                        + ". "
                        + name
                        + " ["
                        + app_type
                        + "]"
                    )

                else:

                    lines.append(
                        str(index)
                        + ". "
                        + name
                    )

            lines.append("")

            lines.append(
                "Please select a number."
            )

            return {
                "success": False,
                "message": "\n".join(lines),
                "results": results,
                "suggestions": []
            }

        # ----------------------------------------------------
        # DIRECT APPSFOLDER NAME FALLBACK
        #
        # This can catch apps that were not returned by
        # Get-StartApps but are visible to AppsFolder.
        # ----------------------------------------------------

        if self.open_appsfolder_by_name(
            target
        ):

            return {
                "success": True,
                "message": (
                    "Opened Windows application: "
                    + target
                ),
                "results": [],
                "suggestions": []
            }

        # ----------------------------------------------------
        # SPELLING SUGGESTIONS
        # ----------------------------------------------------

        suggestions = self.find_similar(
            target
        )

        if suggestions:

            lines = []

            lines.append(
                "I could not find '"
                + target
                + "'."
            )

            lines.append("")

            lines.append(
                "Did you mean:"
            )

            for index, name in enumerate(
                suggestions,
                start=1
            ):

                lines.append(
                    str(index)
                    + ". "
                    + name
                )

            lines.append("")

            lines.append(
                "Please select a number."
            )

            return {
                "success": False,
                "message": "\n".join(lines),
                "results": [],
                "suggestions": suggestions
            }

        return {
            "success": False,
            "message": (
                "I could not find '"
                + target
                + "'."
            ),
            "results": [],
            "suggestions": []
        }

    # ========================================================
    # OPEN SELECTED RESULT
    # ========================================================

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

            return {
                "success": False,
                "message": (
                    "Please enter a valid number."
                )
            }

        if (
            index < 0
            or
            index >= len(results)
        ):

            return {
                "success": False,
                "message": (
                    "Invalid selection."
                )
            }

        selected = results[
            index
        ]

        if self.open_record(
            selected
        ):

            return {
                "success": True,
                "message": (
                    "Opened successfully: "
                    + selected.get(
                        "name",
                        "application"
                    )
                )
            }

        return {
            "success": False,
            "message": (
                "Windows could not launch: "
                + selected.get(
                    "name",
                    "application"
                )
            )
        }

    # ========================================================
    # OPEN SUGGESTION
    # ========================================================

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

            return {
                "success": False,
                "message": (
                    "Please enter a valid number."
                )
            }

        if (
            index < 0
            or
            index >= len(suggestions)
        ):

            return {
                "success": False,
                "message": (
                    "Invalid selection."
                )
            }

        selected_name = suggestions[
            index
        ]

        return self.open(
            selected_name
        )

    # ========================================================
    # REFRESH DATABASE
    # ========================================================

    def refresh(self):

        self._cache = []

        self._cache_time = 0

        return self.build_database(
            force=True
        )

    # ========================================================
    # LIST ALL APPLICATIONS
    # ========================================================

    def list_applications(self):

        database = self.build_database()

        result = []

        seen = set()

        for app in database:

            name = app.get(
                "name",
                ""
            ).strip()

            if not name:

                continue

            key = name.lower()

            if key in seen:

                continue

            seen.add(key)

            result.append(
                app
            )

        return result


# ============================================================
# SIMPLE TEST / STANDALONE MODE
#
# You can run:
#
#     python universal_app_launcher.py
#
# Then type:
#
#     open camera
#     open weather
#     open money
#     open chrome
#     open firefix
#
# ============================================================

def main():

    launcher = UniversalAppLauncher()

    print("=" * 60)
    print("Vyom AI - Universal Application Launcher")
    print("=" * 60)
    print("Type 'exit' to quit.")
    print("")
    print("Examples:")
    print("  open camera")
    print("  open weather")
    print("  open money")
    print("  open chrome")
    print("  open firefox")
    print("  open firefix")
    print("")

    pending_results = None
    pending_suggestions = None

    while True:

        try:

            user_input = input(
                "You : "
            ).strip()

        except (
            KeyboardInterrupt,
            EOFError
        ):

            print("")
            break

        if not user_input:

            continue

        if user_input.lower() in (
            "exit",
            "quit",
            "close"
        ):

            break

        # ----------------------------------------------------
        # NUMBER SELECTION
        # ----------------------------------------------------

        if user_input.isdigit():

            number = int(
                user_input
            )

            if pending_results:

                response = launcher.open_selected(
                    pending_results,
                    number
                )

                print(
                    "Vyom : "
                    + response["message"]
                )

                if response["success"]:

                    pending_results = None

                continue

            if pending_suggestions:

                response = launcher.open_suggestion(
                    pending_suggestions,
                    number
                )

                print(
                    "Vyom : "
                    + response["message"]
                )

                if response["success"]:

                    pending_suggestions = None

                continue

            print(
                "Vyom : No selection is pending."
            )

            continue

        # ----------------------------------------------------
        # OPEN COMMAND
        # ----------------------------------------------------

        command = user_input

        if command.lower().startswith(
            "open "
        ):

            target = command[
                5:
            ].strip()

        else:

            target = command

        pending_results = None
        pending_suggestions = None

        response = launcher.open(
            target
        )

        print(
            "Vyom : "
            + response["message"]
        )

        if response.get(
            "results"
        ):

            pending_results = response[
                "results"
            ]

        if response.get(
            "suggestions"
        ):

            pending_suggestions = response[
                "suggestions"
            ]


if __name__ == "__main__":

    main()

