"""
Project : Vyom AI
Version : 0.4
Module  : Windows Launcher
"""

import subprocess
from tools.app_registry import get_app

class WindowsLauncher:

    def open_app(self, app_name):

        app = get_app(app_name)

        if app is None:
            return f"Application '{app_name}' is not registered."

        try:
            subprocess.Popen(app)
            return f"{app_name} opened successfully."

        except Exception as e:
            return f"Error : {e}"
