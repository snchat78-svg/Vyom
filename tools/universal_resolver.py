"""
Project : Vyom AI
Version : 0.8
Module  : Universal Windows Resolver

Purpose:
    Find and open Windows applications, files and folders
    without manually registering every application.
"""

import os
import shutil
import subprocess


class UniversalResolver:

    def __init__(self):

        self.start_menu_paths = [
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
            )
        ]

        self.common_paths = [
            os.path.expanduser("~/Desktop"),
            os.path.expanduser("~/Documents"),
            os.path.expanduser("~/Downloads"),
            os.path.expanduser("~/Pictures"),
            os.path.expanduser("~/Videos"),
            os.path.expanduser("~/Music")
        ]

    # -------------------------------------------------
    # NORMALIZE NAME
    # -------------------------------------------------

    def normalize(self, name):

        name = name.strip().lower()

        if name.endswith(".exe"):
            name = name[:-4]

        return name.strip()

    # -------------------------------------------------
    # EXACT PATH
    # -------------------------------------------------

    def find_exact_path(self, target):

        target = target.strip().strip('"')

        if os.path.exists(target):
            return target

        return None

    # -------------------------------------------------
    # WINDOWS PATH
    # -------------------------------------------------

    def find_in_path(self, target):

        name = self.normalize(target)

        result = shutil.which(name)

        if result:
            return result

        result = shutil.which(name + ".exe")

        if result:
            return result

        return None

    # -------------------------------------------------
    # START MENU SEARCH
    # -------------------------------------------------

    def search_start_menu(self, target):

        target_name = self.normalize(target)

        results = []

        for start_path in self.start_menu_paths:

            if not os.path.exists(start_path):
                continue

            for root, dirs, files in os.walk(start_path):

                for file in files:

                    lower_file = file.lower()

                    if not (
                        lower_file.endswith(".lnk")
                        or lower_file.endswith(".exe")
                    ):
                        continue

                    name_without_ext = os.path.splitext(
                        file
                    )[0].lower()

                    if (
                        name_without_ext == target_name
                        or target_name in name_without_ext
                    ):

                        results.append(
                            os.path.join(root, file)
                        )

        return results

    # -------------------------------------------------
    # COMMON USER FOLDERS / FILES
    # -------------------------------------------------

    def search_common_locations(self, target):

        target_name = target.strip().lower()

        results = []

        for base_path in self.common_paths:

            if not os.path.exists(base_path):
                continue

            try:

                for root, dirs, files in os.walk(base_path):

                    # FOLDERS
                    for directory in dirs:

                        if directory.lower() == target_name:

                            results.append(
                                os.path.join(root, directory)
                            )

                    # FILES
                    for file in files:

                        if file.lower() == target_name:

                            results.append(
                                os.path.join(root, file)
                            )

                    if len(results) >= 20:
                        return results

            except (PermissionError, OSError):

                continue

        return results

    # -------------------------------------------------
    # FULL SEARCH
    # -------------------------------------------------

    def find(self, target):

        target = target.strip()

        if not target:
            return []

        results = []

        # 1. Exact path
        exact = self.find_exact_path(target)

        if exact:
            return [exact]

        # 2. Windows PATH
        path_result = self.find_in_path(target)

        if path_result:
            results.append(path_result)

        # 3. Start Menu applications
        start_results = self.search_start_menu(target)

        for item in start_results:

            if item not in results:
                results.append(item)

        # 4. Common user locations
        common_results = self.search_common_locations(target)

        for item in common_results:

            if item not in results:
                results.append(item)

        return results[:20]

    # -------------------------------------------------
    # OPEN TARGET
    # -------------------------------------------------

    def open_target(self, target):

        results = self.find(target)

        if not results:

            return {
                "success": False,
                "message": (
                    "I could not find "
                    f"'{target}'."
                ),
                "results": []
            }

        # ---------------------------------------------
        # ONE MATCH
        # ---------------------------------------------

        if len(results) == 1:

            path = results[0]

            try:

                os.startfile(path)

                return {
                    "success": True,
                    "message": (
                        f"'{target}' opened successfully."
                    ),
                    "path": path,
                    "results": results
                }

            except Exception as e:

                return {
                    "success": False,
                    "message": f"Error opening '{target}': {e}",
                    "results": results
                }

        # ---------------------------------------------
        # MULTIPLE MATCHES
        # ---------------------------------------------

        return {
            "success": False,
            "multiple": True,
            "message": (
                f"Multiple items found for '{target}'."
            ),
            "results": results
        }

    # -------------------------------------------------
    # OPEN SELECTED RESULT
    # -------------------------------------------------

    def open_selected(self, results, number):

        try:

            index = int(number) - 1

            if index < 0 or index >= len(results):

                return "Invalid selection."

            path = results[index]

            os.startfile(path)

            return (
                f"Opened successfully: {path}"
            )

        except ValueError:

            return "Please enter a valid number."

        except Exception as e:

            return f"Error opening item: {e}"
