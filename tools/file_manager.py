"""
Project : Vyom AI
Version : 0.7
Module  : File Manager
"""

import os


class FileManager:

    def search(self, filename, start_path="C:\\"):

        results = []

        try:
            for root, dirs, files in os.walk(start_path):

                for file in files:

                    if filename.lower() in file.lower():

                        results.append(os.path.join(root, file))

                        if len(results) >= 10:
                            return results

        except Exception:
            pass

        return results
