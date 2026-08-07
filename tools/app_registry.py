"""
Project : Vyom AI
Version : 0.3
Module  : App Registry
"""

APPS = {

    "notepad": "notepad.exe",

    "calculator": "calc.exe",

    "paint": "mspaint.exe",

    "cmd": "cmd.exe",

    "explorer": "explorer.exe",

    "chrome": None,

    "excel": None,

    "word": None

}


def get_app(app_name):

    return APPS.get(app_name.lower())
