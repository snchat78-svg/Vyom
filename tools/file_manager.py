"""
Project : Vyom AI
Version : 0.8
Module : File Manager
"""

import os


class FileManager:

    def search(self, filename, start_path="C:\\"):

        results = []

        filename = filename.strip()

        if not filename:
            return results

        try:

            for root, dirs, files in os.walk(start_path):

                # Ignore folders that commonly cause unnecessary
                # access problems or very large searches.
                dirs[:] = [
                    d for d in dirs
                    if d.lower() not in [
                        "$recycle.bin",
                        "system volume information"
                    ]
                ]

                for file in files:

                    if filename.lower() in file.lower():

                        full_path = os.path.join(root, file)

                        results.append(full_path)

                        # Maximum 10 results
                        if len(results) >= 10:

                            return results

        except (PermissionError, OSError):

            pass

        return results

    # -----------------------------------------------------
    # Open file or folder using Windows default application
    # -----------------------------------------------------

    def open_file(self, file_path):

        file_path = file_path.strip()

        if not file_path:

            return "Please specify a file or folder."

        if not os.path.exists(file_path):

            return f"File or folder not found: {file_path}"

        try:

            # Windows opens the file with its registered
            # default application.
            os.startfile(file_path)

            return f"Opened successfully: {file_path}"

        except Exception as e:

            return f"Error opening {file_path}: {e}"

    # -----------------------------------------------------
    # Search and open the first matching file
    # -----------------------------------------------------

    def search_and_open(self, filename, start_path="C:\\"):

        results = self.search(
            filename,
            start_path
        )

        if not results:

            return f"File not found: {filename}"

        return self.open_file(results[0])
