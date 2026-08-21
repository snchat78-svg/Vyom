"""
Project : Vyom AI
Version : 0.1
Module  : Skill Builder

Purpose:
    Convert an unknown user goal into a structured
    capability/skill proposal.

IMPORTANT:

    This module does NOT execute generated code.

    It creates a safe skill specification that can later
    be passed through:

        validation
            ↓
        code generation
            ↓
        sandbox testing
            ↓
        user permission
            ↓
        activation

This is the foundation for Vyom's future self-capability
system.
"""


from typing import Any, Dict, List, Optional

from ai_core.skill_registry import SkillRegistry


class SkillBuilder:

    # =========================================================
    # INITIALIZATION
    # =========================================================

    def __init__(
        self,
        registry: Optional[SkillRegistry] = None
    ):

        self.registry = (
            registry
            if registry is not None
            else SkillRegistry()
        )

    # =========================================================
    # NORMALIZE
    # =========================================================

    def _normalize(
        self,
        goal
    ):

        if goal is None:

            return ""

        return str(
            goal
        ).strip()

    # =========================================================
    # CREATE NAME
    # =========================================================

    def _create_skill_name(
        self,
        goal
    ):

        goal = self._normalize(
            goal
        )

        words = goal.lower().split()

        important = []

        ignored = {
            "the",
            "a",
            "an",
            "please",
            "me",
            "my",
            "do",
            "make",
            "create",
            "give",
            "get",
            "and",
            "to",
            "for",
            "from",
            "with"
        }

        for word in words:

            cleaned = "".join(
                character
                for character in word
                if character.isalnum()
            )

            if (
                cleaned
                and
                cleaned not in ignored
            ):

                important.append(
                    cleaned
                )

        if not important:

            return "generated_skill"

        return "_".join(
            important[:6]
        )

    # =========================================================
    # DETECT REQUIREMENTS
    # =========================================================

    def _detect_requirements(
        self,
        goal
    ) -> List[str]:

        text = self._normalize(
            goal
        ).lower()

        requirements = []

        # -----------------------------------------------------
        # Image / OCR
        # -----------------------------------------------------

        image_words = [
            "photo",
            "image",
            "picture",
            "screenshot",
            "ocr",
            "image se",
            "photo se"
        ]

        if any(
            word in text
            for word in image_words
        ):

            requirements.append(
                "image_input"
            )

            requirements.append(
                "ocr"
            )

        # -----------------------------------------------------
        # Excel
        # -----------------------------------------------------

        excel_words = [
            "excel",
            "xlsx",
            "spreadsheet",
            "sheet",
            "table"
        ]

        if any(
            word in text
            for word in excel_words
        ):

            requirements.append(
                "excel_automation"
            )

        # -----------------------------------------------------
        # Browser
        # -----------------------------------------------------

        browser_words = [
            "browser",
            "website",
            "web",
            "internet",
            "online",
            "chrome",
            "search online"
        ]

        if any(
            word in text
            for word in browser_words
        ):

            requirements.append(
                "browser_automation"
            )

        # -----------------------------------------------------
        # Coding
        # -----------------------------------------------------

        coding_words = [
            "code",
            "coding",
            "program",
            "software",
            "app",
            "application",
            "flutter",
            "dart",
            "python"
        ]

        if any(
            word in text
            for word in coding_words
        ):

            requirements.append(
                "coding"
            )

        # -----------------------------------------------------
        # File
        # -----------------------------------------------------

        file_words = [
            "file",
            "folder",
            "document",
            "pdf",
            "photo",
            "image"
        ]

        if any(
            word in text
            for word in file_words
        ):

            requirements.append(
                "file_access"
            )

        # -----------------------------------------------------
        # Remove duplicates
        # -----------------------------------------------------

        unique = []

        for item in requirements:

            if item not in unique:

                unique.append(
                    item
                )

        return unique

    # =========================================================
    # CREATE PLAN
    # =========================================================

    def _create_plan(
        self,
        goal,
        requirements
    ):

        plan = []

        # -----------------------------------------------------
        # Input
        # -----------------------------------------------------

        if "image_input" in requirements:

            plan.append(
                {
                    "step": len(plan) + 1,
                    "action": "locate_image_input",
                    "purpose": (
                        "Find the image supplied by "
                        "the user."
                    )
                }
            )

        # -----------------------------------------------------
        # OCR
        # -----------------------------------------------------

        if "ocr" in requirements:

            plan.append(
                {
                    "step": len(plan) + 1,
                    "action": "extract_text",
                    "purpose": (
                        "Extract readable information "
                        "from the image."
                    )
                }
            )

        # -----------------------------------------------------
        # Browser
        # -----------------------------------------------------

        if "browser_automation" in requirements:

            plan.append(
                {
                    "step": len(plan) + 1,
                    "action": "browser_automation",
                    "purpose": (
                        "Use an approved browser automation "
                        "interface."
                    )
                }
            )

        # -----------------------------------------------------
        # Excel
        # -----------------------------------------------------

        if "excel_automation" in requirements:

            plan.append(
                {
                    "step": len(plan) + 1,
                    "action": "create_excel",
                    "purpose": (
                        "Create or update an Excel workbook "
                        "with the extracted data."
                    )
                }

            )

        # -----------------------------------------------------
        # Coding
        # -----------------------------------------------------

        if "coding" in requirements:

            plan.append(
                {
                    "step": len(plan) + 1,
                    "action": "software_development",
                    "purpose": (
                        "Create or modify software according "
                        "to the user's goal."
                    )
                }
            )

        # -----------------------------------------------------
        # File access
        # -----------------------------------------------------

        if "file_access" in requirements:

            plan.append(
                {
                    "step": len(plan) + 1,
                    "action": "file_access",
                    "purpose": (
                        "Locate and access the files required "
                        "for the task."
                    )
                }
            )

        # -----------------------------------------------------
        # If no specialized requirement detected
        # -----------------------------------------------------

        if not plan:

            plan.append(
                {
                    "step": 1,
                    "action": "analyze_goal",
                    "purpose": (
                        "Analyze the goal and determine "
                        "the required tools."
                    )
                }
            )

        return plan

    # =========================================================
    # BUILD
    # =========================================================

    def build(
        self,
        goal
    ) -> Dict[str, Any]:

        goal = self._normalize(
            goal
        )

        if not goal:

            return {
                "success": False,
                "stage": "invalid_goal",
                "message": (
                    "Cannot build a skill from an empty goal."
                )
            }

        skill_name = self._create_skill_name(
            goal
        )

        requirements = self._detect_requirements(
            goal
        )

        plan = self._create_plan(
            goal,
            requirements
        )

        description = (
            "Generated capability plan for: "
            + goal
        )

        registered = self.registry.register(
            name=skill_name,
            description=description,
            goal=goal,
            requirements=requirements,
            plan=plan,
            status="planned"
        )

        if not registered.get(
            "success",
            False
        ):

            return registered

        return {
            "success": True,
            "stage": "skill_planned",
            "message": (
                "I analyzed the goal and created "
                "a new capability plan."
            ),
            "skill": registered.get(
                "skill"
            ),
            "next_stage": (
                "validation_and_code_generation"
            )
        }

    # =========================================================
    # GET SKILL
    # =========================================================

    def get_skill(
        self,
        name
    ):

        return self.registry.get(
            name
            )
