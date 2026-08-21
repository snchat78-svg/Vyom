"""
Project : Vyom AI
Version : 0.4
Module : Autonomous Agent
"""

from typing import Any, Dict, Optional, List

from ai_core.brain import Brain
from ai_core.reasoning_engine import ReasoningEngine
from tools.tool_manager import ToolManager
from ai_core.skill_builder import SkillBuilder



class AutonomousAgent:

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

        # =========================================================
        # SKILL BUILDER 
        # =========================================================
        #
        # Used when the required capability does not already
        # exist in the current tool system.
        #
        # SkillBuilder creates a capability plan.
        # It does NOT directly execute generated code.
        #

        self.skill_builder = SkillBuilder()

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
                        "stage": "brain",
                        "error": str(error)
                    }
                )

        # =====================================================
        # EXISTING TOOL ROUTE
        # =====================================================

        if route.get(
            "route"
        ) == "existing_tools":

            for step in plan:

                self.step_count += 1

                if self.step_count > self.max_steps:

                    self.active = False

                    return {
                        "success": False,
                        "stage": "safety_limit",
                        "message": (
                            "Autonomous step limit reached."
                        )
                    }

                current_intent = step.get(
                    "intent"
                )

                try:

                    result = self.tool_manager.execute(
                        current_intent
                    )

                    self.task_history.append(
                        {
                            "step": self.step_count,
                            "type": step.get(
                                "type"
                            ),
                            "result": result
                        }
                    )

                    self.active = False

                    return {
                        "success": True,
                        "stage": "completed",
                        "result": result,
                        "history": self.task_history
                    }

                except Exception as error:

                    self.active = False

                    return {
                        "success": False,
                        "stage": "execution_error",
                        "error": str(error),
                        "history": self.task_history
                    }

        # =====================================================
        # CAPABILITY FOUND
        # =====================================================

        if route.get(
            "route"
        ) == "capability":

            capability = route.get(
                "capability"
            )

            self.active = False

            return {
                "success": False,
                "stage": "capability_not_implemented",
                "message": (
                    "The required capability was "
                    "identified but its executor is "
                    "not implemented yet."
                ),
                "capability": capability,
                "goal": self.current_goal,
                "plan": plan
            }

        # =====================================================
        # MISSING CAPABILITY
        # =====================================================

        if route.get(
    "route"
) == "missing_capability":

    # -----------------------------------------------------
    # The old system stopped here.
    #
    # New system:
    #
    #     Unknown Goal
    #          ↓
    #     SkillBuilder
    #          ↓
    #     Skill Plan
    #
    # IMPORTANT:
    #
    # SkillBuilder does NOT execute generated code.
    # -----------------------------------------------------

    try:

        skill_result = self.skill_builder.build(
            self.current_goal
        )

    except Exception as error:

        self.active = False

        return {
            "success": False,
            "stage": "skill_builder_error",
            "message": (
                "I understood that I need a new "
                "capability, but the capability "
                "builder failed."
            ),
            "error": str(
                error
            ),
            "goal": self.current_goal,
            "plan": plan
        }

    self.active = False

    if isinstance(
        skill_result,
        dict
    ):

        return {
            "success": skill_result.get(
                "success",
                False
            ),
            "stage": skill_result.get(
                "stage",
                "skill_planned"
            ),
            "message": skill_result.get(
                "message",
                "A new capability plan was created."
            ),
            "goal": self.current_goal,
            "plan": plan,
            "skill": skill_result.get(
                "skill"
            ),
            "next_stage": skill_result.get(
                "next_stage"
            )
        }

    return {
        "success": False,
        "stage": "skill_builder_error",
        "message": str(
            skill_result
        ),
        "goal": self.current_goal,
        "plan": plan
    }
        # =====================================================
        # STOP
        # =====================================================

        self.active = False

        return {
            "success": False,
            "stage": "stopped",
            "message": route.get(
                "reason",
                "Task stopped."
            )
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
