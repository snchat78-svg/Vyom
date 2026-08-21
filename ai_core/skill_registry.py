"""
Project : Vyom AI
Version : 0.1
Module  : Skill Registry

Purpose:
    Maintain Vyom's locally created skill/capability
    definitions.

IMPORTANT:

    This registry stores skill METADATA and plans.

    It does NOT execute arbitrary generated Python code.

    A skill must pass the future validation and permission
    pipeline before it can become executable.

Architecture:

    SkillBuilder
         |
         v
    SkillRegistry
         |
         v
    Local Skill Storage
         |
         v
    Future Validator / Sandbox
"""


import json
import os
import re
from typing import Any, Dict, List, Optional


class SkillRegistry:

    # =========================================================
    # INITIALIZATION
    # =========================================================

    def __init__(
        self,
        storage_path: Optional[str] = None
    ):

        if storage_path:

            self.storage_path = os.path.abspath(
                storage_path
            )

        else:

            project_root = os.path.dirname(
                os.path.dirname(
                    os.path.abspath(
                        __file__
                    )
                )
            )

            skills_directory = os.path.join(
                project_root,
                "skills"
            )

            self.storage_path = os.path.join(
                skills_directory,
                "registry.json"
            )

        self._ensure_storage()

        self.skills = self._load()

    # =========================================================
    # STORAGE
    # =========================================================

    def _ensure_storage(self):

        directory = os.path.dirname(
            self.storage_path
        )

        if directory:

            os.makedirs(
                directory,
                exist_ok=True
            )

        if not os.path.exists(
            self.storage_path
        ):

            self._write(
                {}
            )

    # =========================================================
    # LOAD
    # =========================================================

    def _load(
        self
    ) -> Dict[str, Any]:

        try:

            with open(
                self.storage_path,
                "r",
                encoding="utf-8"
            ) as file:

                data = json.load(
                    file
                )

            if isinstance(
                data,
                dict
            ):

                return data

        except Exception:

            pass

        return {}

    # =========================================================
    # WRITE
    # =========================================================

    def _write(
        self,
        data
    ):

        directory = os.path.dirname(
            self.storage_path
        )

        if directory:

            os.makedirs(
                directory,
                exist_ok=True
            )

        temporary_path = (
            self.storage_path
            + ".tmp"
        )

        with open(
            temporary_path,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                data,
                file,
                indent=4,
                ensure_ascii=False
            )

        os.replace(
            temporary_path,
            self.storage_path
        )

    # =========================================================
    # NORMALIZE NAME
    # =========================================================

    def _normalize_name(
        self,
        name
    ):

        if not name:

            return ""

        name = str(
            name
        ).strip().lower()

        name = re.sub(
            r"[^a-z0-9_]+",
            "_",
            name
        )

        name = re.sub(
            r"_+",
            "_",
            name
        )

        return name.strip(
            "_"
        )

    # =========================================================
    # REGISTER
    # =========================================================

    def register(
        self,
        name,
        description="",
        goal="",
        requirements=None,
        plan=None,
        status="planned"
    ):

        normalized_name = self._normalize_name(
            name
        )

        if not normalized_name:

            return {
                "success": False,
                "message": (
                    "Skill name is required."
                )
            }

        if requirements is None:

            requirements = []

        if plan is None:

            plan = []

        skill = {
            "name": normalized_name,
            "description": str(
                description
            ),
            "goal": str(
                goal
            ),
            "requirements": list(
                requirements
            ),
            "plan": list(
                plan
            ),
            "status": str(
                status
            ),
            "enabled": False,
            "validated": False,
            "approved": False,
            "executable": False
        }

        self.skills[
            normalized_name
        ] = skill

        self._write(
            self.skills
        )

        return {
            "success": True,
            "skill": dict(
                skill
            )
        }

    # =========================================================
    # GET
    # =========================================================

    def get(
        self,
        name
    ):

        normalized_name = self._normalize_name(
            name
        )

        if not normalized_name:

            return None

        skill = self.skills.get(
            normalized_name
        )

        if skill is None:

            return None

        return dict(
            skill
        )

    # =========================================================
    # EXISTS
    # =========================================================

    def exists(
        self,
        name
    ):

        return (
            self.get(
                name
            )
            is not None
        )

    # =========================================================
    # LIST
    # =========================================================

    def list_skills(
        self,
        enabled_only=False
    ):

        result = []

        for skill in self.skills.values():

            if (
                enabled_only
                and
                not skill.get(
                    "enabled",
                    False
                )
            ):

                continue

            result.append(
                dict(
                    skill
                )
            )

        return result

    # =========================================================
    # APPROVE
    # =========================================================

    def approve(
        self,
        name
    ):

        normalized_name = self._normalize_name(
            name
        )

        skill = self.skills.get(
            normalized_name
        )

        if skill is None:

            return False

        skill[
            "approved"
        ] = True

        skill[
            "status"
        ] = "approved"

        self._write(
            self.skills
        )

        return True

    # =========================================================
    # VALIDATE
    # =========================================================

    def validate(
        self,
        name
    ):

        normalized_name = self._normalize_name(
            name
        )

        skill = self.skills.get(
            normalized_name
        )

        if skill is None:

            return False

        skill[
            "validated"
        ] = True

        skill[
            "status"
        ] = "validated"

        self._write(
            self.skills
        )

        return True

    # =========================================================
    # ENABLE
    # =========================================================

    def enable(
        self,
        name
    ):

        normalized_name = self._normalize_name(
            name
        )

        skill = self.skills.get(
            normalized_name
        )

        if skill is None:

            return False

        # -----------------------------------------------------
        # Safety condition
        #
        # A skill cannot become executable merely because it
        # exists in the registry.
        # -----------------------------------------------------

        if not skill.get(
            "validated",
            False
        ):

            return False

        if not skill.get(
            "approved",
            False
        ):

            return False

        skill[
            "enabled"
        ] = True

        skill[
            "status"
        ] = "enabled"

        self._write(
            self.skills
        )

        return True

    # =========================================================
    # DISABLE
    # =========================================================

    def disable(
        self,
        name
    ):

        normalized_name = self._normalize_name(
            name
        )

        skill = self.skills.get(
            normalized_name
        )

        if skill is None:

            return False

        skill[
            "enabled"
        ] = False

        skill[
            "executable"
        ] = False

        skill[
            "status"
        ] = "disabled"

        self._write(
            self.skills
        )

        return True

    # =========================================================
    # REMOVE
    # =========================================================

    def remove(
        self,
        name
    ):

        normalized_name = self._normalize_name(
            name
        )

        if normalized_name not in self.skills:

            return False

        del self.skills[
            normalized_name
        ]

        self._write(
            self.skills
        )

        return True
