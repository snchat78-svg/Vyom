"""
Project : Vyom AI
Version : 0.9
Module : Universal Windows Resolver

Purpose:
    Find and open Windows applications, files,
    folders and Windows shortcuts without
    manually registering every application.
"""

import os
import shutil


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
            os.path.join(
                os.environ.get("USERPROFILE", ""),
                "Desktop"
            ),

            os.path.join(
                os.environ.get("USERPROFILE", ""),
                "Documents"
            ),

            os.path.join(
                os.environ.get("USERPROFILE", ""),
                "Downloads"
            ),

            os.path.join(
                os.environ.get("USERPROFILE", ""),
                "Pictures"
            ),

            os.path.join(
                os.environ.get("USERPROFILE", ""),
                "Videos"
            ),

            os.path.join(
                os.environ.get("USERPROFILE", ""),
                "Music"
            )
        ]

    # =================================================
    # NORMALIZE
    # =================================================

    def normalize(self, name):

        name = name.strip().strip('"').strip("'").lower()

        if name.endswith(".exe"):

            name = name[:-4]

        return name.strip()

    # =================================================
    # OPEN WINDOWS TARGET
    # =================================================

    def _open(self, path):

        try:

            os.startfile(path)

            return True, f"Opened successfully: {path}"

        except Exception as e:

            return False, f"Error opening '{path}': {e}"

    # =================================================
    # EXACT PATH
    # =================================================

    def find_exact_path(self, target):

        target = target.strip().strip('"').strip("'")

        if os.path.exists(target):

            return target

        return None

    # =================================================
    # WINDOWS PATH / EXE
    # =================================================

    def find_in_path(self, target):

        name = self.normalize(target)

        result = shutil.which(name)

        if result:

            return result

        result = shutil.which(name + ".exe")

        if result:

            return result

        return None

    # =================================================
    # START MENU APPLICATION SEARCH
    # =================================================

    def search_start_menu(self, target):

        target_name = self.normalize(target)

        results = []

        for start_path in self.start_menu_paths:

            if not os.path.exists(start_path):

                continue

            try:

                for root, dirs, files in os.walk(start_path):

                    for file in files:

                        lower_file = file.lower()

                        if not (
                            lower_file.endswith(".lnk")
                            or lower_file.endswith(".exe")
                        ):

                            continue

                        filename = os.path.splitext(
                            file
                        )[0].lower().strip()

                        if (
                            filename == target_name
                            or target_name in filename
                        ):

                            full_path = os.path.join(
                                root,
                                file
                            )

                            if full_path not in results:

                                results.append(full_path)

            except (PermissionError, OSError):

                continue

        return results

    # =================================================
    # COMMON FILE / FOLDER SEARCH
    # =================================================

    def search_common_locations(self, target):

        target_name = target.strip().strip('"').strip("'").lower()

        results = []

        for base_path in self.common_paths:

            if not os.path.exists(base_path):

                continue

            try:

                for root, dirs, files in os.walk(
                    base_path,
                    onerror=lambda error: None
                ):

                    # -------------------------------
                    # FOLDERS
                    # -------------------------------

                    for directory in dirs:

                        if directory.lower() == target_name:

                            full_path = os.path.join(
                                root,
                                directory
                            )

                            if full_path not in results:

                                results.append(full_path)

                    # -------------------------------
                    # FILES
                    # -------------------------------

                    for file in files:

                        if file.lower() == target_name:

                            full_path = os.path.join(
                                root,
                                file
                            )

                            if full_path not in results:

                                results.append(full_path)

                    if len(results) >= 20:

                        return results

            except (PermissionError, OSError):

                continue

        return results

    # =================================================
    # FIND EVERYTHING
    # =================================================

    def find(self, target):

        target = target.strip()

        if not target:

            return []

        results = []

        # ---------------------------------------------
        # 1. EXACT PATH
        # ---------------------------------------------

        exact = self.find_exact_path(target)

        if exact:

            return [exact]

        # ---------------------------------------------
        # 2. WINDOWS PATH
        # ---------------------------------------------

        path_result = self.find_in_path(target)

        if path_result:

            results.append(path_result)

        # ---------------------------------------------
        # 3. START MENU
        # ---------------------------------------------

        start_results = self.search_start_menu(target)

        for item in start_results:

            if item not in results:

                results.append(item)

        # ---------------------------------------------
        # 4. USER FOLDERS
        # ---------------------------------------------

        common_results = self.search_common_locations(
            target
        )

        for item in common_results:

            if item not in results:

                results.append(item)

        return results[:20]

    # =================================================
    # OPEN
    # =================================================

    def open(self, target):

        results = self.find(target)

        if not results:

            return (
                f"I could not find "
                f"'{target}'."
            )

        # ---------------------------------------------
        # ONLY ONE RESULT
        # ---------------------------------------------

        if len(results) == 1:

            success, message = self._open(
                results[0]
            )

            return message

        # ---------------------------------------------
        # MULTIPLE RESULTS
        # ---------------------------------------------

        message = (
            f"Multiple items found for "
            f"'{target}':\n"
        )

        for index, path in enumerate(
            results,
            start=1
        ):

            message += (
                f"{index}. {path}\n"
            )

        message += (
            "\nPlease select a number."
        )

        return message

    # =================================================
    # SEARCH AND OPEN
    # =================================================

    def search_and_open(self, target):

        results = self.find(target)

        if not results:

            return (
                f"I could not find "
                f"'{target}'."
            )

        # ---------------------------------------------
        # ONE RESULT
        # ---------------------------------------------

        if len(results) == 1:

            success, message = self._open(
                results[0]
            )

            return message

        # ---------------------------------------------
        # MULTIPLE RESULTS
        # ---------------------------------------------

        message = (
            f"I found multiple items "
            f"for '{target}':\n"
        )

        for index, path in enumerate(
            results,
            start=1
        ):

            message += (
                f"{index}. {path}\n"
            )

        message += (
            "\nPlease select a number."
        )

        return message

    # =================================================
    # OPEN SELECTED RESULT
    # =================================================

    def open_selected(self, results, number):

        try:

            index = int(number) - 1

        except ValueError:

            return "Please enter a valid number."

        if index < 0 or index >= len(results):

            return "Invalid selection."

        path = results[index]

        success, message = self._open(path)

        return message
