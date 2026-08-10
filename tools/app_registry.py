"""
Project : Vyom AI
Version : 0.8
Module  : App Registry

Purpose:
    Windows में installed applications को manually register किए बिना
    खोजने में मदद करना।
"""

import os
import winreg


def _read_app_paths():

    results = []

    registry_locations = [
        (winreg.HKEY_CURRENT_USER,
         r"Software\Microsoft\Windows\CurrentVersion\App Paths"),

        (winreg.HKEY_LOCAL_MACHINE,
         r"Software\Microsoft\Windows\CurrentVersion\App Paths")
    ]

    for hive, path in registry_locations:

        try:

            key = winreg.OpenKey(hive, path)

            count = winreg.QueryInfoKey(key)[0]

            for i in range(count):

                try:

                    name = winreg.EnumKey(key, i)

                    subkey = winreg.OpenKey(key, name)

                    try:
                        exe_path, _ = winreg.QueryValueEx(subkey, None)

                        if exe_path:
                            results.append(
                                (name.lower(), exe_path)
                            )

                    except Exception:
                        pass

                    winreg.CloseKey(subkey)

                except Exception:
                    pass

            winreg.CloseKey(key)

        except Exception:
            pass

    return results


def find_application(app_name):

    app_name = app_name.strip().lower()

    if not app_name:
        return None

    # -----------------------------------------
    # 1. Direct executable name
    # -----------------------------------------

    if os.path.isfile(app_name):

        return app_name

    # -----------------------------------------
    # 2. PATH / Windows command
    # -----------------------------------------

    if not app_name.endswith(".exe"):

        exe_name = app_name + ".exe"

    else:

        exe_name = app_name

    path_result = os.popen(
        'where "{}" 2>nul'.format(exe_name)
    ).read().strip()

    if path_result:

        first_result = path_result.splitlines()[0]

        if os.path.isfile(first_result):

            return first_result

    # -----------------------------------------
    # 3. Windows App Paths Registry
    # -----------------------------------------

    for name, exe_path in _read_app_paths():

        clean_name = name.replace(".exe", "").lower()

        requested_name = app_name.replace(".exe", "").lower()

        if clean_name == requested_name:

            return exe_path.strip('"')

        if requested_name in clean_name:

            return exe_path.strip('"')

    return None


def get_app(app_name):

    return find_application(app_name)
