"""
Project : Vyom AI
Version : 0.9
Module  : Universal Windows Launcher
"""

import os
import subprocess
import shutil


class WindowsLauncher:

    def __init__(self):
        self.app_directories = [
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
            ),

            os.path.join(
                os.environ.get("USERPROFILE", ""),
                "Desktop"
            ),

            os.path.join(
                os.environ.get("PUBLIC", ""),
                "Desktop"
            )
        ]

    def open_app(self, app_name):

        app_name = app_name.strip().lower()

        if not app_name:
            return "Application name is empty."

        # ---------------------------------------------
        # WINDOWS SPECIAL COMMANDS
        # ---------------------------------------------

        special_apps = {
            "notepad": "notepad.exe",
            "calculator": "calc.exe",
            "calc": "calc.exe",
            "paint": "mspaint.exe",
            "cmd": "cmd.exe",
            "command prompt": "cmd.exe",
            "explorer": "explorer.exe",
            "file explorer": "explorer.exe",
            "windows explorer": "explorer.exe"
        }

        if app_name in special_apps:

            try:
                subprocess.Popen(special_apps[app_name])

                return f"{app_name} opened successfully."

            except Exception as e:

                return f"Error opening {app_name}: {e}"

        # ---------------------------------------------
        # DIRECT WINDOWS PATH
        # ---------------------------------------------

        if os.path.exists(app_name):

            try:
                os.startfile(app_name)

                return f"{app_name} opened successfully."

            except Exception as e:

                return f"Error opening {app_name}: {e}"

        # ---------------------------------------------
        # SEARCH APPLICATION SHORTCUTS
        # ---------------------------------------------

        result = self._find_shortcut(app_name)

        if result:

            try:
                os.startfile(result)

                return f"{app_name} opened successfully."

            except Exception as e:

                return f"Error opening {app_name}: {e}"

        # ---------------------------------------------
        # SEARCH WINDOWS PATH
        # ---------------------------------------------

        executable = shutil.which(app_name)

        if executable:

            try:
                subprocess.Popen(executable)

                return f"{app_name} opened successfully."

            except Exception as e:

                return f"Error opening {app_name}: {e}"

        # ---------------------------------------------
        # TRY EXE NAME
        # ---------------------------------------------

        if not app_name.endswith(".exe"):

            executable = shutil.which(app_name + ".exe")

            if executable:

                try:
                    subprocess.Popen(executable)

                    return f"{app_name} opened successfully."

                except Exception as e:

                    return f"Error opening {app_name}: {e}"

        # ---------------------------------------------
        # NOT FOUND
        # ---------------------------------------------

        return (
            f"Application '{app_name}' was not found. "
            f"Vyom could not find a Windows shortcut or executable."
        )

    # =================================================
    # FIND APPLICATION SHORTCUT
    # =================================================

    def _find_shortcut(self, app_name):

        extensions = [
            ".lnk",
            ".url",
            ".exe"
        ]

        for directory in self.app_directories:

            if not os.path.exists(directory):
                continue

            for root, dirs, files in os.walk(directory):

                for file in files:

                    file_lower = file.lower()

                    for extension in extensions:

                        if not file_lower.endswith(extension):
                            continue

                        name = file_lower[:-len(extension)].strip()

                        if name == app_name:
                            return os.path.join(root, file)

                        if app_name in name:
                            return os.path.join(root, file)

        return None
