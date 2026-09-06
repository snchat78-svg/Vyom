import os
import sys
import shutil
import subprocess
import difflib
import ctypes
import time

# Guard Windows-only imports
if sys.platform == "win32":
    try:
        import winreg
    except ImportError:
        winreg = None
else:
    winreg = None


class UniversalResolver:

    def __init__(self):

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

        self.application_extensions = [
            ".exe",
            ".com",
            ".bat",
            ".cmd",
            ".lnk"
        ]

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

        self.max_results = 20

        self._windows_apps_cache = None
        self._windows_apps_cache_time = 0

        self.app_cache_seconds = 30

    def normalize(self, name):

        if name is None:
            return ""

        name = str(name)

        name = name.strip()

        name = name.strip('"')

        name = name.strip("'")

        name = name.lower()

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

        name = " ".join(
            name.split()
        )

        return name.strip()

    def clean_target(self, target):

        if target is None:
            return ""

        target = str(target)

        target = target.strip()

        target = target.strip('"')

        target = target.strip("'")

        return target.strip()

    def search_registry_app_paths(
        self,
        target
    ):

        if winreg is None:
            return []

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

                                        results.append(
                                            value
                                        )

                            finally:

                                subkey.Close()

                        except Exception:
                            continue

            except Exception:
                continue

        return results[:self.max_results]
