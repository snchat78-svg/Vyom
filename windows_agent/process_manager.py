"""
Project : Vyom AI
Version : 0.6
Module : Process Manager
"""

import os
import subprocess

from tools.app_registry import get_app


class ProcessManager:

    def close_app(self, process_name):

        process_name = process_name.strip().lower()

        if not process_name:
            return "Please specify an application."

        # -------------------------------------------------
        # 1. Get registered application
        # -------------------------------------------------

        app = get_app(process_name)

        # -------------------------------------------------
        # 2. Determine actual process name
        # -------------------------------------------------

        if app:

            # Example:
            # EXCEL.EXE
            # chrome.exe
            # notepad.exe

            actual_name = os.path.basename(app)

        else:

            actual_name = process_name

        # -------------------------------------------------
        # 3. Make sure process name ends with .exe
        # -------------------------------------------------

        if not actual_name.lower().endswith(".exe"):

            actual_name = actual_name + ".exe"

        # -------------------------------------------------
        # 4. Close application
        # -------------------------------------------------

        try:

            result = subprocess.run(
                [
                    "taskkill",
                    "/F",
                    "/IM",
                    actual_name
                ],
                capture_output=True,
                text=True
            )

            # -------------------------------------------------
            # Application successfully closed
            # -------------------------------------------------

            if result.returncode == 0:

                return (
                    f"{process_name} closed successfully."
                )

            # -------------------------------------------------
            # Application was not running
            # -------------------------------------------------

            error = result.stderr.strip()

            if "not found" in error.lower():

                return (
                    f"{process_name} is not currently running."
                )

            # -------------------------------------------------
            # Other Windows error
            # -------------------------------------------------

            return (
                f"Could not close {process_name}. "
                f"{error}"
            )

        except Exception as e:

            return f"Error closing {process_name}: {e}"
