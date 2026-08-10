"""
Project : Vyom AI
Version : 0.8
Module : Windows Launcher
"""

import os
import subprocess

from tools.app_registry import get_app


class WindowsLauncher:

    def open_app(self, target):

        target = target.strip()

        if not target:

            return "Please specify an application or file."

        # -----------------------------------------
        # 1. Direct existing path
        # -----------------------------------------

        if os.path.exists(target):

            try:

                os.startfile(target)

                return f"{target} opened successfully."

            except Exception as e:

                return f"Error opening {target}: {e}"

        # -----------------------------------------
        # 2. Search installed application
        # -----------------------------------------

        app = get_app(target)

        if app:

            try:

                os.startfile(app)

                return f"{target} opened successfully."

            except Exception as e:

                return f"Error opening {target}: {e}"

        # -----------------------------------------
        # 3. Windows Shell
        # -----------------------------------------

        try:

            subprocess.Popen(
                ["cmd", "/c", "start", "", target],
                shell=False
            )

            return f"{target} opening requested."

        except Exception as e:

            return f"Application or file '{target}' could not be opened. Error: {e}"
