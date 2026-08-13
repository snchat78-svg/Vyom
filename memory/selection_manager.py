"""
Project : Vyom AI
Version : 0.2
Module  : Selection Manager

Purpose:
    Remember the latest multiple search results so the
    user can select an item by number.

    This module is designed to work with:

    - ToolManager
    - UniversalResolver
    - UniversalAppLauncher
    - FileManager
    - Context Memory
    - Natural Language Selection

IMPORTANT:

    The original selection functionality is preserved.

    Existing code can continue using:

        save(results)
        has_results()
        get(number)
        clear()
        count()

    Additional optional context information can now be stored:

        target
        source
        selected item
        selected number

    These additions are backward compatible.
"""


class SelectionManager:

    # =========================================================
    # INITIALIZATION
    # =========================================================

    def __init__(self):

        # -----------------------------------------------------
        # Existing selection results
        # -----------------------------------------------------

        self.results = []

        # -----------------------------------------------------
        # Context information
        #
        # These are optional and do not affect old behaviour.
        #
        # Example:
        #
        # target = "pic sanu"
        # source = "resolver"
        #
        # or:
        #
        # target = "Facebook"
        # source = "app"
        # -----------------------------------------------------

        self.target = None

        self.source = None

        # -----------------------------------------------------
        # Last selected item
        #
        # These are useful for future contextual commands such
        # as:
        #
        #     open that again
        #     open the previous one
        #
        # They are kept separately from current results.
        # -----------------------------------------------------

        self.last_selected = None

        self.last_selected_number = None

    # =========================================================
    # SAVE RESULTS
    # =========================================================

    def save(
        self,
        results,
        target=None,
        source=None
    ):

        # -----------------------------------------------------
        # Empty results
        # -----------------------------------------------------

        if not results:

            self.results = []

            self.target = target

            self.source = source

            return

        # -----------------------------------------------------
        # Preserve existing behaviour
        #
        # Convert incoming results into a list so that the
        # SelectionManager always works with its own copy.
        # -----------------------------------------------------

        self.results = list(
            results
        )

        # -----------------------------------------------------
        # Optional context information
        #
        # Old code may simply call:
        #
        #     save(results)
        #
        # and this will continue to work.
        # -----------------------------------------------------

        if target is not None:

            self.target = str(
                target
            ).strip()

        else:

            self.target = None

        if source is not None:

            self.source = str(
                source
            ).strip()

        else:

            self.source = None

        # -----------------------------------------------------
        # A new result list means there is no current selection.
        # -----------------------------------------------------

        self.last_selected = None

        self.last_selected_number = None

    # =========================================================
    # CHECK RESULTS
    # =========================================================

    def has_results(self):

        return len(
            self.results
        ) > 0

    # =========================================================
    # GET SELECTED RESULT
    # =========================================================

    def get(
        self,
        number
    ):

        try:

            index = (
                int(number) - 1
            )

        except (
            ValueError,
            TypeError
        ):

            return None

        if index < 0:

            return None

        if index >= len(
            self.results
        ):

            return None

        # -----------------------------------------------------
        # Save selection information.
        #
        # This does NOT remove the result.
        #
        # ToolManager remains responsible for clearing the
        # selection after opening the selected item.
        # -----------------------------------------------------

        self.last_selected = (
            self.results[index]
        )

        self.last_selected_number = (
            index + 1
        )

        return self.results[index]

    # =========================================================
    # GET RESULT BY ZERO-BASED INDEX
    #
    # Internal/helper method for future modules.
    #
    # Normal user selection remains one-based through get().
    # =========================================================

    def get_by_index(
        self,
        index
    ):

        try:

            index = int(
                index
            )

        except (
            ValueError,
            TypeError
        ):

            return None

        if index < 0:

            return None

        if index >= len(
            self.results
        ):

            return None

        return self.results[index]

    # =========================================================
    # GET CURRENT RESULTS
    # =========================================================

    def get_all(self):

        return list(
            self.results
        )

    # =========================================================
    # GET CURRENT TARGET
    # =========================================================

    def get_target(self):

        return self.target

    # =========================================================
    # GET CURRENT SOURCE
    # =========================================================

    def get_source(self):

        return self.source

    # =========================================================
    # GET LAST SELECTED ITEM
    # =========================================================

    def get_last_selected(self):

        return self.last_selected

    # =========================================================
    # GET LAST SELECTED NUMBER
    # =========================================================

    def get_last_selected_number(self):

        return self.last_selected_number

    # =========================================================
    # CHECK LAST SELECTION
    # =========================================================

    def has_last_selected(self):

        return (
            self.last_selected is not None
        )

    # =========================================================
    # UPDATE CONTEXT
    #
    # This allows ToolManager or future Context Memory to
    # update target/source without replacing the results.
    # =========================================================

    def set_context(
        self,
        target=None,
        source=None
    ):

        if target is not None:

            self.target = str(
                target
            ).strip()

        if source is not None:

            self.source = str(
                source
            ).strip()

    # =========================================================
    # CLEAR RESULTS
    #
    # IMPORTANT:
    #
    # This preserves the original clear() behaviour while
    # also clearing the current selection context.
    #
    # The last selected item is also cleared because it belongs
    # to the previous selection session.
    # =========================================================

    def clear(self):

        self.results = []

        self.target = None

        self.source = None

        self.last_selected = None

        self.last_selected_number = None

    # =========================================================
    # COUNT
    # =========================================================

    def count(self):

        return len(
            self.results
        )
