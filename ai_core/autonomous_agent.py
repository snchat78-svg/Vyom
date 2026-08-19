"""
Project : Vyom AI
Version : 0.1
Module  : Autonomous Agent Core

Purpose:
    First autonomous reasoning layer for Vyom.

    This module sits ABOVE the existing command engine and
    ToolManager.

    Current architecture:

        User Goal
            |
            v
        AutonomousAgent
            |
            +---- Understand
            |
            +---- Plan
            |
            +---- Decide
            |
            +---- Existing ToolManager
            |
            +---- Observe Result
            |
            +---- Continue / Complete

IMPORTANT:
    This version does NOT execute arbitrary generated code.

    It uses only the already registered/safe capabilities
    exposed through ToolManager.

    Future versions will add:

        - LLM reasoning
        - dynamic planning
        - capability discovery
        - self-created skills
        - sandbox testing
        - skill registry
        - browser automation
        - vision
        - coding agent
        - continuous voice context
"""

from typing import Any, Dict, List, Optional

from ai_core.logger import log
from tools.tool_manager import ToolManager


class AutonomousAgent:

    # =========================================================
    # INITIALIZATION
    # =========================================================

    def __init__(
        self,
        tool_manager: Optional[ToolManager] = None,
        max_steps: int = 10
    ):
        """
        Initialize Autonomous Agent.

        Args:
            tool_manager:
                Existing Vyom ToolManager.

            max_steps:
                Maximum number of actions allowed in one
                autonomous execution cycle.

        IMPORTANT:
            A step limit prevents an accidental infinite loop.
        """

        self.tool_manager = (
            tool_manager
            if tool_manager is not None
            else ToolManager()
        )

        self.max_steps = max(
            1,
            int(max_steps)
        )

        # -----------------------------------------------------
        # Current task
        # -----------------------------------------------------

        self.current_goal = ""

        self.task_history: List[Dict[str, Any]] = []

        self.step_count = 0

        self.active = False

    # =========================================================
    # NORMALIZE GOAL
    # =========================================================

    def _normalize_goal(
        self,
        goal: Any
    ) -> str:
        """
        Convert user input into a clean goal string.
        """

        if goal is None:
            return ""

        return str(
            goal
        ).strip()

    # =========================================================
    # UNDERSTAND
    # =========================================================

    def understand(
        self,
        goal: str
    ) -> Dict[str, Any]:
        """
        First-stage goal understanding.

        This is intentionally lightweight in v0.1.

        A future LLM/reasoning model will replace/extend this
        stage without changing the rest of the architecture.
        """

        clean_goal = self._normalize_goal(
            goal
        )

        if not clean_goal:

            return {
                "understood": False,
                "goal": "",
                "reason": "Empty goal."
            }

        return {
            "understood": True,
            "goal": clean_goal
        }

    # =========================================================
    # PLAN
    # =========================================================

    def create_plan(
        self,
        understood_goal: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Create an initial execution plan.

        v0.1 intentionally creates a simple plan.

        The important architectural point is that the plan is
        separate from execution.

        Later the reasoning model can create multi-step plans
        dynamically.
        """

        if not understood_goal.get(
            "understood",
            False
        ):

            return []

        goal = understood_goal.get(
            "goal",
            ""
        )

        return [
            {
                "step": 1,
                "action": "execute_goal",
                "goal": goal
            }
        ]

    # =========================================================
    # DECIDE
    # =========================================================

    def decide(
        self,
        step: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Decide how the current step should be executed.

        v0.1 delegates the actual command interpretation to
        the existing IntentEngine through the normal executor
        path later.

        For now this method creates a normalized decision
        object.

        This separation is important because future versions
        can replace this decision logic with a real reasoning
        model.
        """

        goal = step.get(
            "goal",
            ""
        )

        return {
            "action": "execute",
            "input": goal
        }

    # =========================================================
    # EXECUTE
    # =========================================================

    def execute_decision(
        self,
        decision: Dict[str, Any]
    ) -> Any:
        """
        Execute a decision through existing ToolManager.

        IMPORTANT:
            We do not bypass ToolManager.

            Existing safety and application/file handling
            remains active.
        """

        command = decision.get(
            "input",
            ""
        )

        if not command:

            return (
                "No executable goal was provided."
            )

        # -----------------------------------------------------
        # Current ToolManager expects an intent dictionary.
        #
        # The existing IntentEngine will be connected by the
        # Executor integration.
        #
        # Therefore this method is intentionally designed to
        # receive a prepared intent in future iterations.
        #
        # For direct compatibility, a simple fallback is used.
        # -----------------------------------------------------

        return {
            "status": "pending_intent",
            "command": command
        }

    # =========================================================
    # OBSERVE
    # =========================================================

    def observe(
        self,
        result: Any
    ) -> Dict[str, Any]:
        """
        Convert execution output into an observation.
        """

        if isinstance(
            result,
            dict
        ):

            status = result.get(
                "status",
                "unknown"
            )

            return {
                "status": status,
                "result": result
            }

        return {
            "status": "completed",
            "result": result
        }

    # =========================================================
    # SHOULD CONTINUE
    # =========================================================

    def should_continue(
        self,
        observation: Dict[str, Any]
    ) -> bool:
        """
        Decide whether another autonomous step is required.

        v0.1 stops after the current step.

        Future versions will use observation + goal +
        remaining plan to decide the next action.
        """

        status = observation.get(
            "status",
            ""
        )

        if status in (
            "failed",
            "error",
            "blocked"
        ):

            return False

        return False

    # =========================================================
    # RECORD
    # =========================================================

    def _record(
        self,
        step: int,
        action: str,
        result: Any
    ):

        self.task_history.append(
            {
                "step": step,
                "action": action,
                "result": result
            }
        )

    # =========================================================
    # RUN
    # =========================================================

    def run(
        self,
        goal: str
    ) -> Dict[str, Any]:
        """
        Main autonomous entry point.

        Current v0.1 pipeline:

            Goal
             ↓
            Understand
             ↓
            Plan
             ↓
            Decide
             ↓
            Prepare execution
             ↓
            Observe
             ↓
            Result

        The architecture is deliberately separated so that
        later versions can add real reasoning and autonomous
        multi-step execution without rewriting ToolManager.
        """

        self.current_goal = self._normalize_goal(
            goal
        )

        self.task_history = []

        self.step_count = 0

        self.active = True

        log(
            f"Autonomous goal received: "
            f"{self.current_goal}"
        )

        # =====================================================
        # UNDERSTAND
        # =====================================================

        understood = self.understand(
            self.current_goal
        )

        if not understood.get(
            "understood",
            False
        ):

            self.active = False

            return {
                "success": False,
                "stage": "understand",
                "message": understood.get(
                    "reason",
                    "Could not understand goal."
                ),
                "history": self.task_history
            }

        # =====================================================
        # PLAN
        # =====================================================

        plan = self.create_plan(
            understood
        )

        if not plan:

            self.active = False

            return {
                "success": False,
                "stage": "plan",
                "message": (
                    "I could not create a plan "
                    "for this goal."
                ),
                "history": self.task_history
            }

        # =====================================================
        # EXECUTION LOOP
        # =====================================================

        for step in plan:

            self.step_count += 1

            if self.step_count > self.max_steps:

                self.active = False

                return {
                    "success": False,
                    "stage": "safety_limit",
                    "message": (
                        "Autonomous step limit reached."
                    ),
                    "history": self.task_history
                }

            # -------------------------------------------------
            # DECIDE
            # -------------------------------------------------

            decision = self.decide(
                step
            )

            # -------------------------------------------------
            # EXECUTE
            # -------------------------------------------------

            result = self.execute_decision(
                decision
            )

            # -------------------------------------------------
            # OBSERVE
            # -------------------------------------------------

            observation = self.observe(
                result
            )

            # -------------------------------------------------
            # RECORD
            # -------------------------------------------------

            self._record(
                self.step_count,
                decision.get(
                    "action",
                    "unknown"
                ),
                observation
            )

            # -------------------------------------------------
            # CONTINUE?
            # -------------------------------------------------

            if not self.should_continue(
                observation
            ):

                self.active = False

                return {
                    "success": True,
                    "stage": "completed",
                    "goal": self.current_goal,
                    "message": (
                        "Autonomous planning cycle "
                        "completed."
                    ),
                    "history": self.task_history
                }

        self.active = False

        return {
            "success": True,
            "stage": "completed",
            "goal": self.current_goal,
            "message": (
                "Autonomous task completed."
            ),
            "history": self.task_history
        }

    # =========================================================
    # RESET
    # =========================================================

    def reset(self):

        self.current_goal = ""

        self.task_history = []

        self.step_count = 0

        self.active = False
