"""
Project : Vyom AI
Version : 0.4
Module  : App Registry
"""

import os


APPS = {

    # Windows built-in apps
    "notepad": "notepad.exe",
    "calculator": "calc.exe",
    "calc": "calc.exe",
    "paint": "mspaint.exe",
    "cmd": "cmd.exe",
    "command prompt": "cmd.exe",
    "explorer": "explorer.exe",
    "file explorer": "explorer.exe",

    # Common Windows tools
    "control panel": "control.exe",
    "task manager": "taskmgr.exe",
    "registry editor": "regedit.exe",
    "device manager": "devmgmt.msc",
    "services": "services.msc",
    "system configuration": "msconfig.exe",

    # Microsoft Office
    "word": "WINWORD.EXE",
    "microsoft word": "WINWORD.EXE",
    "excel": "EXCEL.EXE",
    "microsoft excel": "EXCEL.EXE",
    "powerpoint": "POWERPNT.EXE",
    "microsoft powerpoint": "POWERPNT.EXE",

    # Browsers
    "chrome": "chrome.exe",
    "google chrome": "chrome.exe",
    "firefox": "firefox.exe",
    "mozilla firefox": "firefox.exe",
    "edge": "msedge.exe",
    "internet explorer": "iexplore.exe",
}


def get_app(app_name):

    app_name = app_name.lower().strip()

    # 1. Check registered applications
    app = APPS.get(app_name)

    if app:
        return app

    # 2. If user gives an actual file path
    if os.path.exists(app_name):
        return app_name

    # 3. Try executable directly
    if app_name.endswith(".exe"):
        return app_name

    # 4. Try adding .exe
    exe_name = app_name + ".exe"

    return exe_name
