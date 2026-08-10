"""
Project : Vyom AI
Version : 0.9
Module  : File Manager
"""

import os


class FileManager:

    def __init__(self):

        self.search_locations = [

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

        self.blocked_directories = [
            "$recycle.bin",
            "system volume information",
            "windows\\winsxs",
            "windows\\servicing",
            "windows\\system32",
            "windows\\softwaredistribution"
        ]

    # =================================================
    # SEARCH FILE
    # =================================================

    def search(self, filename, start_path=None):

        filename = filename.strip().lower()

        if not filename:
            return []

        results = []

        locations = []

        # User specifically requested location
        if start_path:

            locations.append(start_path)

        # Normal user folders
        locations.extend(self.search_locations)

        # Remove duplicate paths
        checked = set()

        for location in locations:

            if not location:
                continue

            location = os.path.abspath(location)

            if location.lower() in checked:
                continue

            checked.add(location.lower())

            if not os.path.exists(location):
                continue

            self._search_directory(
                location,
                filename,
                results
            )

            if len(results) >= 10:
                break

        return results[:10]

    # =================================================
    # DIRECTORY SEARCH
    # =================================================

    def _search_directory(
        self,
        directory,
        filename,
        results
    ):

        if len(results) >= 10:
            return

        try:

            for root, dirs, files in os.walk(
                directory,
                onerror=lambda error: None
            ):

                # Remove blocked directories
                dirs[:] = [
                    d for d in dirs
                    if not self._is_blocked(
                        os.path.join(root, d)
                    )
                ]

                for file in files:

                    if filename in file.lower():

                        full_path = os.path.join(
                            root,
                            file
                        )

                        results.append(full_path)

                        if len(results) >= 10:
                            return

        except Exception:
            pass

    # =================================================
    # BLOCK SYSTEM DIRECTORIES
    # =================================================

    def _is_blocked(self, path):

        path_lower = path.lower()

        for blocked in self.blocked_directories:

            if blocked in path_lower:
                return True

        return False

    # =================================================
    # OPEN FILE
    # =================================================

    def open_file(self, filepath):

        if not filepath:
            return "File path is empty."

        if not os.path.exists(filepath):
            return f"File not found: {filepath}"

        try:

            os.startfile(filepath)

            return f"File opened successfully: {filepath}"

        except Exception as e:

            return f"Error opening file: {e}"

    # =================================================
    # SEARCH AND OPEN
    # =================================================

    def search_and_open(self, filename):

        results = self.search(filename)

        if not results:
            return f"File '{filename}' was not found."

        filepath = results[0]

        return self.open_file(filepath)
