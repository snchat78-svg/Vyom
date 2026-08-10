"""
Project : Vyom AI
Version : 0.5
Module : Windows Launcher
"""

import os
import subprocess
import shutil

from tools.app_registry import get_app


class WindowsLauncher:

    def open_app(self, app_name):

        app_name = app_name.strip()

        if not app_name:
            return "Please specify an application."

        # -------------------------------------------------
        # 1. Direct file / folder / shortcut
        # -------------------------------------------------

        if os.path.exists(app_name):

            try:
                os.startfile(app_name)

                return f"{app_name} opened successfully."

            except Exception as e:
                return f"Error opening {app_name}: {e}"

        # -------------------------------------------------
        # 2. Get registered application
        # -------------------------------------------------

        app = get_app(app_name)

        # -------------------------------------------------
        # 3. Try Windows Shell
        # -------------------------------------------------

        try:

            os.startfile(app_name)

            return f"{app_name} opened successfully."

        except Exception:
            pass

        # -------------------------------------------------
        # 4. Try registered application path
        # -------------------------------------------------

        if app:

            try:

                if os.path.exists(app):

                    os.startfile(app)

                    return f"{app_name} opened successfully."

            except Exception:
                pass

        # -------------------------------------------------
        # 5. Try executable from PATH
        # -------------------------------------------------

        if app:

            executable = shutil.which(app)

            if executable:

                try:

                    subprocess.Popen([executable])

                    return f"{app_name} opened successfully."

                except Exception as e:

                    return f"Error opening {app_name}: {e}"

        # -------------------------------------------------
        # 6. Try Windows START command
        # -------------------------------------------------

        try:

            subprocess.Popen(
                ["cmd", "/c", "start", "", app_name],
                shell=False
            )

            return f"{app_name} opened successfully."

        except Exception:
            pass

        # -------------------------------------------------
        # 7. Search Start Menu shortcuts
        # -------------------------------------------------

        shortcut = self._find_start_menu_app(app_name)

        if shortcut:

            try:

                os.startfile(shortcut)

                return f"{app_name} opened successfully."

            except Exception as e:

                return f"Error opening {app_name}: {e}"

        # -------------------------------------------------
        # Application not found
        # -------------------------------------------------

        return (
            f"Application '{app_name}' could not be found. "
            f"Please check the application name."
        )

    # -----------------------------------------------------
    # Search Windows Start Menu shortcuts
    # -----------------------------------------------------

    def _find_start_menu_app(self, app_name):

        locations = []

        # Current user Start Menu
        user_start = os.path.join(
            os.environ.get("APPDATA", ""),
            "Microsoft",
            "Windows",
            "Start Menu",
            "Programs"
        )

        # All users Start Menu
        common_start = os.path.join(
            os.environ.get("PROGRAMDATA", ""),
            "Microsoft",
            "Windows",
            "Start Menu",
            "Programs"
        )

        locations.append(user_start)
        locations.append(common_start)

        target = app_name.lower().strip()

        for location in locations:

            if not os.path.exists(location):
                continue

            for root, dirs, files in os.walk(location):

                for file in files:

                    lower_file = file.lower()

                    if not lower_file.endswith(".lnk"):
                        continue

                    shortcut_name = os.path.splitext(
                        lower_file
                    )[0]

                    if target == shortcut_name:

                        return os.path.join(root, file)

                    if target in shortcut_name:

                        return os.path.join(root, file)

        return None
