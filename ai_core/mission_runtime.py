"""
Project : Vyom AI
Version : 1.1
Module  : Mission Runtime

Purpose:
    Runtime state machine for autonomous missions.

Architecture:

    Goal
      |
      v
    MissionPlanner
      |
      v
    MissionRuntime
      |
      +----> next step
      |
      v
    ToolManager
      |
      v
    Observation / Verification
      |
      +----> completed
      |
      +----> retry
      |
      +----> replan
      |
      +----> blocked

Important:

    - MissionRuntime NEVER executes computer actions directly.
    - ToolManager remains the actual executor.
    - Runtime owns mission/step lifecycle.
    - Runtime tracks dependencies.
    - Runtime tracks retries.
    - Runtime supports verification results.
    - Runtime can request re-planning after failure.
    - Runtime supports capability-blocked missions.
    - Runtime is bounded by max_steps.
    - Runtime preserves mission history.
"""

from typing import Any, Dict, List, Optional


class MissionRuntime:

    # =========================================================
    # TERMINAL STATES
    # =========================================================

    TERMINAL_STATES = {
        "completed",
        "failed",
        "blocked"
    }

    # =========================================================
    # INITIALIZE
    # =========================================================

    def __init__(
        self,
        max_retries: int = 2,
        max_steps: int = 10
    ):

        self.max_retries = max(
            0,
            int(max_retries)
        )

        self.max_steps = max(
            1,
            int(max_steps)
        )

        # -----------------------------------------------------
        # MISSION
        # -----------------------------------------------------

        self.goal = ""

        self.plan: List[
            Dict[str, Any]
        ] = []

        self.mission_state = "idle"

        # -----------------------------------------------------
        # CURRENT STEP
        # -----------------------------------------------------

        self.current_step: Optional[
            Dict[str, Any]
        ] = None

        # -----------------------------------------------------
        # EXECUTION
        # -----------------------------------------------------

        self.step_count = 0

        self.completed_steps = 0

        self.failed_steps = 0

        # -----------------------------------------------------
        # HISTORY
        # -----------------------------------------------------

        self.history: List[
            Dict[str, Any]
        ] = []

        # -----------------------------------------------------
        # LAST RESULT
        # -----------------------------------------------------

        self.last_result: Any = None

        self.last_verification: Dict[
            str,
            Any
        ] = {}

        self.last_error = ""

        # -----------------------------------------------------
        # REPLANNING
        # -----------------------------------------------------

        self.replan_requested = False

        self.replan_reason = ""

        # -----------------------------------------------------
        # CAPABILITY
        # -----------------------------------------------------

        self.blocked_capability = None

    # =========================================================
    # START MISSION
    # =========================================================

    def start(
        self,
        goal: str,
        plan: List[Dict[str, Any]]
    ) -> Dict[str, Any]:

        self.goal = str(
            goal or ""
        ).strip()

        self.plan = []

        if isinstance(
            plan,
            list
        ):

            for step in plan:

                if not isinstance(
                    step,
                    dict
                ):
                    continue

                self.plan.append(
                    dict(step)
                )

        self.current_step = None

        self.step_count = 0

        self.completed_steps = 0

        self.failed_steps = 0

        self.history = []

        self.last_result = None

        self.last_verification = {}

        self.last_error = ""

        self.replan_requested = False

        self.replan_reason = ""

        self.blocked_capability = None

        if not self.goal:

            self.mission_state = "blocked"

        elif not self.plan:

            self.mission_state = "blocked"

        else:

            self.mission_state = "ready"

        return self.snapshot()

    # =========================================================
    # IS ACTIVE
    # =========================================================

    def is_active(
        self
    ) -> bool:

        return (
            self.mission_state
            not in self.TERMINAL_STATES
            and
            self.mission_state != "idle"
        )

    # =========================================================
    # IS TERMINAL
    # =========================================================

    def is_terminal(
        self
    ) -> bool:

        return (
            self.mission_state
            in self.TERMINAL_STATES
        )

    # =========================================================
    # GET NEXT STEP
    # =========================================================

    def get_next_step(
        self
    ) -> Optional[
        Dict[str, Any]
    ]:

        # -----------------------------------------------------
        # STOP CONDITIONS
        # -----------------------------------------------------

        if self.mission_state in (
            "idle",
            "completed",
            "failed",
            "blocked"
        ):
            return None

        # -----------------------------------------------------
        # SAFETY LIMIT
        # -----------------------------------------------------

        if self.step_count >= self.max_steps:

            self.mission_state = "failed"

            self.last_error = (
                "Mission step limit reached."
            )

            self.history.append({
                "event": "safety_limit",
                "step_count": self.step_count,
                "max_steps": self.max_steps
            })

            return None

        # -----------------------------------------------------
        # CHECK REPLAN
        # -----------------------------------------------------

        if self.replan_requested:

            return None

        # -----------------------------------------------------
        # COMPLETED STEP IDS
        # -----------------------------------------------------

        completed_ids = {
            str(
                item.get("id")
            )
            for item in self.plan
            if item.get(
                "status"
            ) == "completed"
        }

        # -----------------------------------------------------
        # FIND READY STEP
        # -----------------------------------------------------

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

            dependencies_ready = all(
                str(dep)
                in completed_ids
                for dep in dependencies
            )

            if not dependencies_ready:

                continue

            # -------------------------------------------------
            # PREPARE STEP
            # -------------------------------------------------

            step["status"] = "executing"

            self.current_step = step

            self.mission_state = "executing"

            self.step_count += 1

            self.history.append({
                "event": "step_started",
                "step": step.get(
                    "step"
                ),
                "id": step.get(
                    "id"
                ),
                "step_count": self.step_count
            })

            return step

        # -----------------------------------------------------
        # CHECK MISSION COMPLETION
        # -----------------------------------------------------

        if self.plan and all(
            step.get(
                "status"
            ) == "completed"
            for step in self.plan
        ):

            self.mission_state = "completed"

            self.current_step = None

            self.history.append({
                "event": "mission_completed"
            })

            return None

        # -----------------------------------------------------
        # NO EXECUTABLE STEP
        #
        # This usually means:
        #
        # - dependency problem
        # - blocked plan
        # - invalid mission
        # -----------------------------------------------------

        pending_steps = [
            step
            for step in self.plan
            if step.get(
                "status",
                "pending"
            ) == "pending"
        ]

        if pending_steps:

            self.mission_state = "blocked"

            self.last_error = (
                "No executable mission step "
                "is currently available."
            )

            self.history.append({
                "event": "mission_blocked",
                "reason": self.last_error
            })

        return None

    # =========================================================
    # MARK STEP COMPLETED
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

        # -----------------------------------------------------
        # UPDATE STEP
        # -----------------------------------------------------

        step["status"] = "completed"

        step["result"] = result

        step["verification"] = (
            verification or {}
        )

        # -----------------------------------------------------
        # UPDATE RUNTIME
        # -----------------------------------------------------

        self.completed_steps += 1

        self.last_result = result

        self.last_verification = (
            verification or {}
        )

        self.last_error = ""

        # -----------------------------------------------------
        # HISTORY
        # -----------------------------------------------------

        self.history.append({
            "event": "step_completed",
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

        # -----------------------------------------------------
        # CHECK MISSION COMPLETE
        # -----------------------------------------------------

        if self.plan and all(
            item.get(
                "status"
            ) == "completed"
            for item in self.plan
        ):

            self.mission_state = "completed"

            self.history.append({
                "event": "mission_completed"
            })

        else:

            self.mission_state = "ready"

        return True

    # =========================================================
    # MARK STEP FAILED
    # =========================================================

    def mark_failed(
        self,
        step_id: str,
        result: Any = None,
        reason: str = "",
        verification: Optional[
            Dict[str, Any]
        ] = None
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

        self.last_result = result

        self.last_verification = (
            verification or {}
        )

        self.last_error = str(
            reason or "Step failed."
        )

        # -----------------------------------------------------
        # RETRY AVAILABLE
        # -----------------------------------------------------

        if retries < self.max_retries:

            retries += 1

            step["retries"] = retries

            step["status"] = "pending"

            step["last_error"] = (
                self.last_error
            )

            step["last_result"] = result

            step["verification"] = (
                verification or {}
            )

            self.history.append({
                "event": "step_retry",
                "step": step.get(
                    "step"
                ),
                "id": step_id,
                "status": "retry",
                "attempt": retries,
                "result": result,
                "verification": (
                    verification or {}
                ),
                "reason": self.last_error
            })

            self.current_step = None

            self.mission_state = "ready"

            return True

        # -----------------------------------------------------
        # RETRIES EXHAUSTED
        # -----------------------------------------------------

        step["status"] = "failed"

        step["result"] = result

        step["last_error"] = (
            self.last_error
        )

        step["verification"] = (
            verification or {}
        )

        self.failed_steps += 1

        self.history.append({
            "event": "step_failed",
            "step": step.get(
                "step"
            ),
            "id": step_id,
            "status": "failed",
            "result": result,
            "verification": (
                verification or {}
            ),
            "reason": self.last_error
        })

        self.current_step = None

        # -----------------------------------------------------
        # REQUEST REPLAN
        # -----------------------------------------------------

        self.request_replan(
            reason=self.last_error
        )

        return False

    # =========================================================
    # REQUEST REPLAN
    # =========================================================

    def request_replan(
        self,
        reason: str = ""
    ):

        self.replan_requested = True

        self.replan_reason = str(
            reason or ""
        ).strip()

        self.mission_state = "replanning"

        self.history.append({
            "event": "replan_requested",
            "reason": self.replan_reason
        })

    # =========================================================
    # CHECK REPLAN
    # =========================================================

    def needs_replan(
        self
    ) -> bool:

        if self.replan_requested:

            return True

        if self.mission_state == "replanning":

            return True

        for step in self.plan:

            if step.get(
                "status"
            ) == "failed":

                return True

        return False

    # =========================================================
    # APPLY NEW PLAN
    # =========================================================

    def apply_replan(
        self,
        plan: List[
            Dict[str, Any]
        ]
    ) -> bool:

        if not isinstance(
            plan,
            list
        ):

            return False

        new_plan = []

        for step in plan:

            if not isinstance(
                step,
                dict
            ):
                continue

            new_step = dict(
                step
            )

            # -------------------------------------------------
            # New plan starts pending unless explicitly marked
            # completed.
            # -------------------------------------------------

            if new_step.get(
                "status"
            ) not in (
                "completed",
                "failed"
            ):

                new_step["status"] = "pending"

            new_plan.append(
                new_step
            )

        if not new_plan:

            self.mission_state = "blocked"

            self.last_error = (
                "Re-planning produced an empty plan."
            )

            return False

        self.plan = new_plan

        self.current_step = None

        self.replan_requested = False

        self.replan_reason = ""

        self.mission_state = "ready"

        self.history.append({
            "event": "plan_updated",
            "plan_size": len(
                self.plan
            )
        })

        return True

    # =========================================================
    # BLOCK MISSION
    # =========================================================

    def block(
        self,
        reason: str = "",
        capability: Any = None
    ):

        self.mission_state = "blocked"

        self.last_error = str(
            reason or "Mission blocked."
        )

        self.blocked_capability = (
            capability
        )

        self.current_step = None

        self.history.append({
            "event": "mission_blocked",
            "reason": self.last_error,
            "capability": capability
        })

    # =========================================================
    # UNBLOCK
    # =========================================================

    def unblock(
        self
    ) -> bool:

        if not self.plan:

            return False

        self.blocked_capability = None

        self.last_error = ""

        self.mission_state = "ready"

        self.history.append({
            "event": "mission_unblocked"
        })

        return True

    # =========================================================
    # FIND STEP
    # =========================================================

    def _find_step(
        self,
        step_id: str
    ) -> Optional[
        Dict[str, Any]
    ]:

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
    # GET CURRENT STEP
    # =========================================================

    def get_current_step(
        self
    ) -> Optional[
        Dict[str, Any]
    ]:

        if not isinstance(
            self.current_step,
            dict
        ):

            return None

        return dict(
            self.current_step
        )

    # =========================================================
    # GET STEP
    # =========================================================

    def get_step(
        self,
        step_id: str
    ) -> Optional[
        Dict[str, Any]
    ]:

        step = self._find_step(
            step_id
        )

        if step is None:

            return None

        return dict(
            step
        )

    # =========================================================
    # MISSION PROGRESS
    # =========================================================

    def progress(
        self
    ) -> Dict[str, Any]:

        total = len(
            self.plan
        )

        completed = sum(
            1
            for step in self.plan
            if step.get(
                "status"
            ) == "completed"
        )

        failed = sum(
            1
            for step in self.plan
            if step.get(
                "status"
            ) == "failed"
        )

        pending = sum(
            1
            for step in self.plan
            if step.get(
                "status"
            ) == "pending"
        )

        executing = sum(
            1
            for step in self.plan
            if step.get(
                "status"
            ) == "executing"
        )

        percentage = (
            (completed / total) * 100
            if total
            else 0
        )

        return {
            "total": total,
            "completed": completed,
            "failed": failed,
            "pending": pending,
            "executing": executing,
            "percentage": percentage
        }

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
                dict(
                    self.current_step
                )
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
            ],

            "step_count": (
                self.step_count
            ),

            "max_steps": (
                self.max_steps
            ),

            "completed_steps": (
                self.completed_steps
            ),

            "failed_steps": (
                self.failed_steps
            ),

            "last_result": (
                self.last_result
            ),

            "last_verification": (
                dict(
                    self.last_verification
                )
            ),

            "last_error": (
                self.last_error
            ),

            "replan_requested": (
                self.replan_requested
            ),

            "replan_reason": (
                self.replan_reason
            ),

            "blocked_capability": (
                self.blocked_capability
            ),

            "progress": (
                self.progress()
            )
        }

    # =========================================================
    # RESET
    # =========================================================

    def reset(
        self
    ):

        self.goal = ""

        self.plan = []

        self.mission_state = "idle"

        self.current_step = None

        self.step_count = 0

        self.completed_steps = 0

        self.failed_steps = 0

        self.history = []

        self.last_result = None

        self.last_verification = {}

        self.last_error = ""

        self.replan_requested = False

        self.replan_reason = ""

        self.blocked_capability = None
