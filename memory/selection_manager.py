"""
Project : Vyom AI
Version : 0.1
Module  : Selection Manager

Purpose:
    Remember the latest multiple search results so the
    user can select an item by number.
"""


class SelectionManager:

    def __init__(self):

        self.results = []

    # =================================================
    # SAVE RESULTS
    # =================================================

    def save(self, results):

        if not results:

            self.results = []

            return

        self.results = list(results)

    # =================================================
    # CHECK RESULTS
    # =================================================

    def has_results(self):

        return len(self.results) > 0

    # =================================================
    # GET SELECTED RESULT
    # =================================================

    def get(self, number):

        try:

            index = int(number) - 1

        except (ValueError, TypeError):

            return None

        if index < 0:

            return None

        if index >= len(self.results):

            return None

        return self.results[index]

    # =================================================
    # CLEAR RESULTS
    # =================================================

    def clear(self):

        self.results = []

    # =================================================
    # COUNT
    # =================================================

    def count(self):

        return len(self.results)
