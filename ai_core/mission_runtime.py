"""
Project : Vyom AI
Version : 1.0
Module  : Mission Runtime

Purpose:
    Runtime state machine for autonomous missions.

The runtime does NOT directly execute Windows operations.
Execution remains delegated to ToolManager.

States:

    pending
      |
      v
    ready
      |
      v
    executing
      |
      +----> verified
      |
      +----> failed
                |
                v
             retry/replan
"""

from typing import Any, Dict, List, Optional


class MissionRuntime:

    TERMINAL_STATES = {
        "completed",
        "failed",
        "blocked"
    }

    def __init__(
        self,
        max_retries: int = 2
    ):
        self.max_retries = max(
            0,
            int(max_retries)
        )

        self.goal = ""
        self.plan: List[
            Dict[str, Any]
        ] = []

        self.mission_state = "idle"
        self.current_step: Optional[
            Dict[str, Any]
        ] = None

        self.history: List[
            Dict[str, Any]
        ] = []

    # =========================================================
    # START
    # =========================================================

    def start(
        self,
        goal: str,
        plan: List[Dict[str, Any]]
    ):

        self.goal = str(
            goal or ""
        ).strip()

        self.plan = [
            dict(step)
            for step in plan
            if isinstance(
                step,
                dict
            )
        ]

        self.history = []
        self.current_step = None

        self.mission_state = (
            "running"
            if self.plan
            else "blocked"
        )

    # =========================================================
    # GET STEP
    # =========================================================

    def get_next_step(
        self
    ) -> Optional[Dict[str, Any]]:

        if self.mission_state in (
            "idle",
            "completed",
            "failed",
            "blocked"
        ):
            return None

        completed_ids = {
            str(item.get("id"))
            for item in self.plan
            if item.get("status")
            == "completed"
        }

        for step in self.plan:

            status = step.get(
                "status",
                "pending"
            )

            if status != "pending":
                continue

            dependencies = step.get(
                "depends_on",
                []
            )

            if not isinstance(
                dependencies,
                list
            ):
                dependencies = []

            if any(
                str(dep) not in completed_ids
                for dep in dependencies
            ):
                continue

            step["status"] = "executing"

            self.current_step = step

            return step

        # -----------------------------------------------------
        # NO MORE PENDING STEPS
        # -----------------------------------------------------

        if all(
            step.get("status")
            == "completed"
            for step in self.plan
        ):
            self.mission_state = "completed"

        return None

    # =========================================================
    # COMPLETE STEP
    # =========================================================

    def mark_completed(
        self,
        step_id: str,
        result: Any = None,
        verification: Optional[
            Dict[str, Any]
        ] = None
    ) -> bool:

        step = self._find_step(
            step_id
        )

        if step is None:
            return False

        step["status"] = "completed"
        step["result"] = result
        step["verification"] = (
            verification or {}
        )

        self.history.append({
            "step": step.get(
                "step"
            ),
            "id": step_id,
            "status": "completed",
            "result": result,
            "verification": (
                verification or {}
            )
        })

        self.current_step = None

        if all(
            item.get("status")
            == "completed"
            for item in self.plan
        ):
            self.mission_state = "completed"

        return True

    # =========================================================
    # FAIL STEP
    # =========================================================

    def mark_failed(
        self,
        step_id: str,
        result: Any = None,
        reason: str = ""
    ) -> bool:

        step = self._find_step(
            step_id
        )

        if step is None:
            return False

        retries = int(
            step.get(
                "retries",
                0
            )
        )

        if retries < self.max_retries:

            step["retries"] = retries + 1
            step["status"] = "pending"
            step["last_error"] = reason

            self.history.append({
                "step": step.get(
                    "step"
                ),
                "id": step_id,
                "status": "retry",
                "attempt": retries + 1,
                "result": result,
                "reason": reason
            })

            self.current_step = None

            return True

        step["status"] = "failed"
        step["result"] = result
        step["last_error"] = reason

        self.history.append({
            "step": step.get(
                "step"
            ),
            "id": step_id,
            "status": "failed",
            "result": result,
            "reason": reason
        })

        self.current_step = None
        self.mission_state = "failed"

        return False

    # =========================================================
    # FIND STEP
    # =========================================================

    def _find_step(
        self,
        step_id: str
    ) -> Optional[Dict[str, Any]]:

        wanted = str(
            step_id
        )

        for step in self.plan:

            if str(
                step.get("id")
            ) == wanted:
                return step

        return None

    # =========================================================
    # REPLAN REQUIRED?
    # =========================================================

    def needs_replan(
        self
    ) -> bool:

        if self.mission_state == "failed":
            return True

        for step in self.plan:

            if step.get(
                "status"
            ) == "failed":
                return True

        return False

    # =========================================================
    # SNAPSHOT
    # =========================================================

    def snapshot(
        self
    ) -> Dict[str, Any]:

        return {
            "goal": self.goal,
            "mission_state": (
                self.mission_state
            ),
            "current_step": (
                dict(self.current_step)
                if isinstance(
                    self.current_step,
                    dict
                )
                else None
            ),
            "plan": [
                dict(step)
                for step in self.plan
            ],
            "history": [
                dict(item)
                for item in self.history
            ]
        }

    # =========================================================
    # RESET
    # =========================================================

    def reset(self):

        self.goal = ""
        self.plan = []
        self.current_step = None
        self.history = []
        self.mission_state = "idle"
