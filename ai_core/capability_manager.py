"""
Project : Vyom AI
Version : 0.1
Module  : Capability Manager

Purpose:
    Maintain and discover Vyom's available capabilities.

IMPORTANT:
    This module does not execute arbitrary code.

    It only describes and selects capabilities.

Future:
    New skills created by Vyom can register themselves here
    after validation and permission.
"""


class CapabilityManager:

    # =========================================================
    # INITIALIZATION
    # =========================================================

    def __init__(self):

        self.capabilities = {}

        self._register_builtin_capabilities()

    # =========================================================
    # BUILT-IN CAPABILITIES
    # =========================================================

    def _register_builtin_capabilities(self):

        self.register(
            name="application_control",
            description=(
                "Open and close Windows applications."
            ),
            keywords=[
                "open app",
                "open application",
                "launch",
                "start",
                "close app",
                "close application"
            ],
            enabled=True
        )

        self.register(
            name="file_search",
            description=(
                "Search for files and folders."
            ),
            keywords=[
                "search file",
                "find file",
                "find folder",
                "search folder",
                "look for file"
            ],
            enabled=True
        )

        self.register(
            name="file_open",
            description=(
                "Open files, folders and supported documents."
            ),
            keywords=[
                "open file",
                "open folder",
                "open document",
                "open photo",
                "open video",
                "open audio"
            ],
            enabled=True
        )

        self.register(
            name="process_control",
            description=(
                "Close running Windows applications/processes."
            ),
            keywords=[
                "close",
                "stop application",
                "stop app"
            ],
            enabled=True
        )

        self.register(
            name="browser_automation",
            description=(
                "Browser automation capability."
            ),
            keywords=[
                "browser",
                "website",
                "web",
                "internet",
                "search online"
            ],
            enabled=False
        )

        self.register(
            name="image_understanding",
            description=(
                "Understand information contained in images."
            ),
            keywords=[
                "image",
                "photo",
                "picture",
                "read image",
                "understand photo"
            ],
            enabled=False
        )

        self.register(
            name="ocr",
            description=(
                "Extract text and structured information from images."
            ),
            keywords=[
                "ocr",
                "extract text",
                "read text from image",
                "photo text"
            ],
            enabled=False
        )

        self.register(
            name="excel_automation",
            description=(
                "Create and modify Excel spreadsheets."
            ),
            keywords=[
                "excel",
                "spreadsheet",
                "xlsx",
                "table in excel"
            ],
            enabled=False
        )

        self.register(
            name="coding",
            description=(
                "Create, modify and test software code."
            ),
            keywords=[
                "code",
                "coding",
                "program",
                "software",
                "python",
                "flutter",
                "dart"
            ],
            enabled=False
        )

    # =========================================================
    # REGISTER
    # =========================================================

    def register(
        self,
        name,
        description="",
        keywords=None,
        enabled=True
    ):

        if not name:

            return False

        name = str(
            name
        ).strip().lower()

        if not name:

            return False

        if keywords is None:

            keywords = []

        self.capabilities[name] = {
            "name": name,
            "description": str(
                description
            ),
            "keywords": [
                str(keyword).strip().lower()
                for keyword in keywords
                if str(keyword).strip()
            ],
            "enabled": bool(
                enabled
            )
        }

        return True

    # =========================================================
    # UNREGISTER
    # =========================================================

    def unregister(
        self,
        name
    ):

        if not name:

            return False

        name = str(
            name
        ).strip().lower()

        if name not in self.capabilities:

            return False

        del self.capabilities[name]

        return True

    # =========================================================
    # GET
    # =========================================================

    def get(
        self,
        name
    ):

        if not name:

            return None

        name = str(
            name
        ).strip().lower()

        return self.capabilities.get(
            name
        )

    # =========================================================
    # LIST
    # =========================================================

    def list_capabilities(
        self,
        enabled_only=False
    ):

        result = []

        for capability in self.capabilities.values():

            if (
                enabled_only
                and
                not capability.get(
                    "enabled",
                    False
                )
            ):

                continue

            result.append(
                dict(
                    capability
                )
            )

        return result

    # =========================================================
    # MATCH
    # =========================================================

    def match(
        self,
        goal
    ):
        """
        Find capabilities whose keywords appear in the goal.

        This is intentionally simple in v0.1.

        Later this matching will be performed by the reasoning
        model using semantic understanding.
        """

        if not goal:

            return []

        goal = str(
            goal
        ).strip().lower()

        matches = []

        for capability in self.capabilities.values():

            if not capability.get(
                "enabled",
                False
            ):

                continue

            score = 0

            for keyword in capability.get(
                "keywords",
                []
            ):

                if keyword in goal:

                    score += 1

            if score > 0:

                matches.append(
                    {
                        "name": capability[
                            "name"
                        ],
                        "description": capability[
                            "description"
                        ],
                        "score": score
                    }
                )

        matches.sort(
            key=lambda item: item[
                "score"
            ],
            reverse=True
        )

        return matches

    # =========================================================
    # FIND REQUIRED CAPABILITY
    # =========================================================

    def find_required(
        self,
        goal
    ):

        matches = self.match(
            goal
        )

        if not matches:

            return None

        return matches[0]

    # =========================================================
    # ENABLE
    # =========================================================

    def enable(
        self,
        name
    ):

        capability = self.get(
            name
        )

        if capability is None:

            return False

        capability[
            "enabled"
        ] = True

        return True

    # =========================================================
    # DISABLE
    # =========================================================

    def disable(
        self,
        name
    ):

        capability = self.get(
            name
        )

        if capability is None:

            return False

        capability[
            "enabled"
        ] = False

        return True
