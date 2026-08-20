"""
Project : Vyom AI
Version : 0.3
Module : Autonomous Agent

Purpose:
    Coordinate:

        User Goal
            ↓
        ReasoningEngine
            ↓
        Intent / Plan
            ↓
        ToolManager
            ↓
        Result
            ↓
        Observation

IMPORTANT:

    Arbitrary generated code is NOT executed directly.

    Existing ToolManager remains the controlled execution
    boundary.
"""

from typing import Any, Dict, Optional, List

from ai_core.brain import Brain
from ai_core.reasoning_engine import ReasoningEngine
from tools.tool_manager import ToolManager


class AutonomousAgent:

    # =========================================================
    # INITIALIZATION
    # =========================================================

    def __init__(
        self,
        tool_manager: Optional[ToolManager] = None,
        brain: Optional[Brain] = None,
        reasoning_engine: Optional[ReasoningEngine] = None,
        max_steps: int = 10
    ):

        self.tool_manager = (
            tool_manager
            if tool_manager is not None
            else ToolManager()
        )

        self.brain = (
            brain
            if brain is not None
            else Brain()
        )

        self.reasoning_engine = (
            reasoning_engine
            if reasoning_engine is not None
            else ReasoningEngine()
        )

        self.max_steps = max(
            1,
            int(max_steps)
        )

        self.current_goal = ""

        self.task_history: List[
            Dict[str, Any]
        ] = []

        self.step_count = 0

        self.active = False

    # =========================================================
    # RUN
    # =========================================================

    def run(
        self,
        goal: str,
        intent: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:

        self.current_goal = str(
            goal
        ).strip()

        self.task_history = []

        self.step_count = 0

        self.active = True

        # =====================================================
        # REASON
        # =====================================================

        reasoning = self.reasoning_engine.reason(
            self.current_goal,
            intent
        )

        analysis = reasoning.get(
            "analysis",
            {}
        )

        route = reasoning.get(
            "route",
            {}
        )

        plan = reasoning.get(
            "plan",
            []
        )

        # =====================================================
        # INVALID GOAL
        # =====================================================

        if not analysis.get(
            "understood",
            False
        ):

            self.active = False

            return {
                "success": False,
                "stage": "understand",
                "message": analysis.get(
                    "reason",
                    "Could not understand goal."
                ),
                "history": self.task_history
            }

        # =====================================================
        # BRAIN
        # =====================================================

        if isinstance(
            intent,
            dict
        ):

            try:

                self.brain.think(
                    intent
                )

            except Exception as error:

                self.task_history.append(
                    {
                        "step": 0,
                        "stage": "brain",
                        "error": str(error)
                    }
                )

        # =====================================================
        # REASONING ROUTE
        # =====================================================

        if route.get(
            "route"
        ) == "reasoning":

            self.active = False

            return {
                "success": False,
                "stage": "capability_required",
                "goal": self.current_goal,
                "message": (
                    "This goal is not supported by "
                    "the current capabilities yet."
                ),
                "analysis": analysis,
                "route": route,
                "plan": plan,
                "history": self.task_history
            }

        # =====================================================
        # EXISTING TOOL ROUTE
        # =====================================================

        if route.get(
            "route"
        ) != "existing_tools":

            self.active = False

            return {
                "success": False,
                "stage": "routing",
                "message": route.get(
                    "reason",
                    "No execution route available."
                ),
                "history": self.task_history
            }

        # =====================================================
        # EXECUTE EXISTING PLAN
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

            intent_to_execute = step.get(
                "intent"
            )

            if not isinstance(
                intent_to_execute,
                dict
            ):

                self.active = False

                return {
                    "success": False,
                    "stage": "invalid_intent",
                    "message": (
                        "No valid intent was generated."
                    ),
                    "history": self.task_history
                }

            # -------------------------------------------------
            # Execute through controlled ToolManager
            # -------------------------------------------------

            try:

                result = self.tool_manager.execute(
                    intent_to_execute
                )

                observation = {
                    "success": True,
                    "result": result
                }

            except Exception as error:

                observation = {
                    "success": False,
                    "error": str(error)
                }

            self.task_history.append(
                {
                    "step": self.step_count,
                    "intent": intent_to_execute,
                    "observation": observation
                }
            )

            self.active = False

            return {
                "success": observation.get(
                    "success",
                    False
                ),
                "stage": "completed",
                "goal": self.current_goal,
                "result": observation.get(
                    "result"
                ),
                "history": self.task_history
            }

        self.active = False

        return {
            "success": False,
            "stage": "empty_plan",
            "message": (
                "No executable plan was created."
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

        self.reasoning_engine.reset()
