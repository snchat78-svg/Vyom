"""
Project : Vyom AI
Version : 0.10
Module  : File Manager
"""

import os
import ctypes


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
            ),

            # OneDrive common folders
            os.path.join(
                os.environ.get("USERPROFILE", ""),
                "OneDrive",
                "Desktop"
            ),

            os.path.join(
                os.environ.get("USERPROFILE", ""),
                "OneDrive",
                "Documents"
            ),

            os.path.join(
                os.environ.get("USERPROFILE", ""),
                "OneDrive",
                "Downloads"
            ),

            os.path.join(
                os.environ.get("USERPROFILE", ""),
                "OneDrive",
                "Pictures"
            ),

            os.path.join(
                os.environ.get("USERPROFILE", ""),
                "OneDrive",
                "Videos"
            ),

            os.path.join(
                os.environ.get("USERPROFILE", ""),
                "OneDrive",
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

        self.max_results = 10

    # =================================================
    # SEARCH FILE
    # =================================================

    def search(
        self,
        filename,
        start_path=None
    ):

        if filename is None:

            return []

        filename = str(
            filename
        ).strip().lower()

        if not filename:

            return []

        results = []

        locations = []

        # -------------------------------------------------
        # User specifically requested location
        # -------------------------------------------------

        if start_path:

            locations.append(
                start_path
            )

        # -------------------------------------------------
        # Normal user folders
        # -------------------------------------------------

        locations.extend(
            self.search_locations
        )

        # -------------------------------------------------
        # Remove duplicate paths
        # -------------------------------------------------

        checked = set()

        for location in locations:

            if not location:

                continue

            try:

                location = os.path.abspath(
                    location
                )

            except Exception:

                continue

            key = location.lower()

            if key in checked:

                continue

            checked.add(key)

            if not os.path.exists(
                location
            ):

                continue

            self._search_directory(
                location,
                filename,
                results
            )

            if len(results) >= self.max_results:

                break

        return results[
            :self.max_results
        ]

    # =================================================
    # DIRECTORY SEARCH
    # =================================================

    def _search_directory(
        self,
        directory,
        filename,
        results
    ):

        if len(results) >= self.max_results:

            return

        try:

            for root, dirs, files in os.walk(
                directory,
                onerror=lambda error: None
            ):

                # -------------------------------------------------
                # Remove blocked directories
                # -------------------------------------------------

                dirs[:] = [
                    d
                    for d in dirs
                    if not self._is_blocked(
                        os.path.join(
                            root,
                            d
                        )
                    )
                ]

                for file in files:

                    if filename in file.lower():

                        full_path = os.path.join(
                            root,
                            file
                        )

                        # -----------------------------------------
                        # Avoid duplicate result
                        # -----------------------------------------

                        if full_path.lower() not in [
                            item.lower()
                            for item in results
                        ]:

                            results.append(
                                full_path
                            )

                        if len(results) >= self.max_results:

                            return

        except Exception:

            pass

    # =================================================
    # BLOCK SYSTEM DIRECTORIES
    # =================================================

    def _is_blocked(
        self,
        path
    ):

        path_lower = str(
            path
        ).lower()

        for blocked in self.blocked_directories:

            if blocked in path_lower:

                return True

        return False

    # =================================================
    # OPEN FILE
    #
    # Windows default application is used.
    #
    # JPG  -> Default Image Viewer
    # PNG  -> Default Image Viewer
    # MP3  -> Default Music Player
    # MP4  -> Default Video Player
    # PDF  -> Default PDF Reader
    # DOCX -> Default Word application
    # =================================================

    def open_file(
        self,
        filepath
    ):

        if not filepath:

            return (
                "File path is empty."
            )

        filepath = str(
            filepath
        ).strip().strip('"').strip("'")

        if not os.path.exists(
            filepath
        ):

            return (
                f"File not found: "
                f"{filepath}"
            )

        # =================================================
        # METHOD 1
        # os.startfile
        # =================================================

        try:

            os.startfile(
                filepath
            )

            return (
                f"File opened successfully: "
                f"{filepath}"
            )

        except Exception as first_error:

            # =================================================
            # METHOD 2
            # Windows ShellExecute
            # =================================================

            try:

                result = (
                    ctypes.windll.shell32.ShellExecuteW(
                        None,
                        "open",
                        filepath,
                        None,
                        None,
                        1
                    )
                )

                if result > 32:

                    return (
                        f"File opened successfully: "
                        f"{filepath}"
                    )

            except Exception:
                pass

            return (
                f"Error opening file: "
                f"{first_error}"
            )

    # =================================================
    # SEARCH AND OPEN
    # =================================================

    def search_and_open(
        self,
        filename
    ):

        results = self.search(
            filename
        )

        if not results:

            return (
                f"File '{filename}' "
                f"was not found."
            )

        # -------------------------------------------------
        # One result
        # -------------------------------------------------

        if len(results) == 1:

            return self.open_file(
                results[0]
            )

        # -------------------------------------------------
        # Multiple results
        # -------------------------------------------------

        message = (
            f"Multiple files found "
            f"for '{filename}':\n"
        )

        for index, filepath in enumerate(
            results,
            start=1
        ):

            message += (
                f"{index}. "
                f"{filepath}\n"
            )

        message += (
            "\nPlease select a number."
        )

        return message
