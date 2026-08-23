"""
Project : Vyom AI
Version : 0.5
Module  : Autonomous Agent

Purpose:
    Coordinate Vyom's autonomous execution.

Architecture:

    User Goal
        |
        v
    ReasoningEngine
        |
        v
    Plan
        |
        v
    ToolManager
        |
        v
    Result
        |
        v
    Result Check
        |
        +---- Success ----> Complete
        |
        +---- Failure ----> Re-plan
                                |
                                v
                           Execute Again

IMPORTANT:

    Existing ToolManager behaviour is preserved.

    SkillBuilder does NOT execute generated code.

    Autonomous execution is limited by max_steps.

    No security bypass or arbitrary generated-code
    execution is allowed here.
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

        # =========================================================
        # EXISTING TOOL MANAGER
        # =========================================================

        self.tool_manager = (
            tool_manager
            if tool_manager is not None
            else ToolManager()
        )

        # =========================================================
        # EXISTING BRAIN
        # =========================================================

        self.brain = (
            brain
            if brain is not None
            else Brain()
        )

        # =========================================================
        # EXISTING REASONING ENGINE
        # =========================================================

        self.reasoning_engine = (
            reasoning_engine
            if reasoning_engine is not None
            else ReasoningEngine()
        )

        # =========================================================
        # EXISTING SKILL BUILDER
        # =========================================================
        #
        # SkillBuilder creates capability plans.
        #
        # It does NOT execute generated code.
        #

        self.skill_builder = SkillBuilder()

        # =========================================================
        # SAFETY LIMIT
        # =========================================================

        self.max_steps = max(
            1,
            int(max_steps)
        )

        # =========================================================
        # TASK STATE
        # =========================================================

        self.current_goal = ""

        self.task_history: List[
            Dict[str, Any]
        ] = []

        self.step_count = 0

        self.active = False

    # =========================================================
    # RESULT CHECK
    # =========================================================

    def _result_is_successful(
        self,
        result
    ) -> bool:
        """
        Perform a conservative first-level result check.

        ToolManager currently returns mostly text messages.
        Therefore this method does not assume every result
        is a dictionary.

        This is NOT the final verification system.

        The future verification layer will inspect the
        actual Windows/application state.
        """

        if result is None:

            return False

        # ---------------------------------------------------------
        # Dictionary result
        # ---------------------------------------------------------

        if isinstance(
            result,
            dict
        ):

            if "success" in result:

                return bool(
                    result.get(
                        "success"
                    )
                )

            if "error" in result:

                return False

            return True

        # ---------------------------------------------------------
        # Boolean result
        # ---------------------------------------------------------

        if isinstance(
            result,
            bool
        ):

            return result

        # ---------------------------------------------------------
        # Text result
        # ---------------------------------------------------------

        text = str(
            result
        ).strip().lower()

        if not text:

            return False

        failure_phrases = [
            "error",
            "failed",
            "failure",
            "could not",
            "not found",
            "invalid",
            "don't understand",
            "no tool available",
            "please tell me",
            "unable to",
            "exception"
        ]

        for phrase in failure_phrases:

            if phrase in text:

                return False

        return True

    # =========================================================
    # EXECUTE ONE PLAN STEP
    # =========================================================

    def _execute_step(
        self,
        step
    ) -> Dict[str, Any]:
        """
        Execute one planned step through the existing
        ToolManager.

        Existing ToolManager remains the actual executor.
        """

        self.step_count += 1

        # ---------------------------------------------------------
        # SAFETY LIMIT
        # ---------------------------------------------------------

        if self.step_count > self.max_steps:

            return {
                "success": False,
                "stage": "safety_limit",
                "message": (
                    "Autonomous step limit reached."
                )
            }

        if not isinstance(
            step,
            dict
        ):

            return {
                "success": False,
                "stage": "invalid_step",
                "message": (
                    "Invalid autonomous plan step."
                )
            }

        current_intent = step.get(
            "intent"
        )

        # ---------------------------------------------------------
        # Capability-only steps do not go to ToolManager.
        # ---------------------------------------------------------

        step_type = step.get(
            "type",
            ""
        )

        if step_type in (
            "use_capability",
            "request_new_capability"
        ):

            return {
                "success": False,
                "stage": "capability_route",
                "message": (
                    "This plan step requires a "
                    "capability route."
                ),
                "step": step
            }

        # ---------------------------------------------------------
        # Execute existing intent
        # ---------------------------------------------------------

        try:

            result = self.tool_manager.execute(
                current_intent
            )

        except Exception as error:

            return {
                "success": False,
                "stage": "execution_error",
                "error": str(error),
                "step": step
            }

        # ---------------------------------------------------------
        # Check result
        # ---------------------------------------------------------

        successful = (
            self._result_is_successful(
                result
            )
        )

        history_item = {
            "step": self.step_count,
            "type": step.get(
                "type"
            ),
            "intent": current_intent,
            "result": result,
            "verified": False,
            "result_success": successful
        }

        self.task_history.append(
            history_item
        )

        if successful:

            return {
                "success": True,
                "stage": "executed",
                "result": result,
                "step": self.step_count
            }

        return {
            "success": False,
            "stage": "execution_failed",
            "result": result,
            "step": self.step_count
        }

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
        # INITIAL REASONING
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

            if not plan:

                self.active = False

                return {
                    "success": False,
                    "stage": "empty_plan",
                    "message": (
                        "ReasoningEngine returned "
                        "an empty execution plan."
                    ),
                    "analysis": analysis
                }

            # -------------------------------------------------
            # EXECUTION / REPLAN LOOP
            # -------------------------------------------------

            while (
                self.step_count
                < self.max_steps
            ):

                # -------------------------------------------------
                # Execute current plan
                # -------------------------------------------------

                execution_failed = False

                for step in plan:

                    result = self._execute_step(
                        step
                    )

                    # -------------------------------------------------
                    # Safety limit
                    # -------------------------------------------------

                    if result.get(
                        "stage"
                    ) == "safety_limit":

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
                    # Capability route
                    # -------------------------------------------------

                    if result.get(
                        "stage"
                    ) == "capability_route":

                        execution_failed = True

                        break

                    # -------------------------------------------------
                    # Execution failed
                    # -------------------------------------------------

                    if not result.get(
                        "success",
                        False
                    ):

                        execution_failed = True

                        break

                # -------------------------------------------------
                # If all plan steps succeeded
                # -------------------------------------------------

                if not execution_failed:

                    # -------------------------------------------------
                    # Mark executed steps as provisional success.
                    #
                    # Actual state verification will be added in
                    # the next architecture stage.
                    # -------------------------------------------------

                    for item in self.task_history:

                        if (
                            item.get(
                                "result_success"
                            )
                            and not item.get(
                                "verified",
                                False
                            )
                        ):

                            item["verified"] = False

                    self.active = False

                    last_result = None

                    if self.task_history:

                        last_result = self.task_history[
                            -1
                        ].get(
                            "result"
                        )

                    return {
                        "success": True,
                        "stage": "completed",
                        "result": last_result,
                        "history": self.task_history
                    }

                # -------------------------------------------------
                # Execution failed.
                #
                # Ask ReasoningEngine to reason again.
                # -------------------------------------------------

                if self.step_count >= self.max_steps:

                    self.active = False

                    return {
                        "success": False,
                        "stage": "safety_limit",
                        "message": (
                            "Autonomous re-planning "
                            "limit reached."
                        ),
                        "history": self.task_history
                    }

                try:

                    re_reasoning = (
                        self.reasoning_engine.reason(
                            self.current_goal,
                            intent
                        )
                    )

                except Exception as error:

                    self.active = False

                    return {
                        "success": False,
                        "stage": "replanning_error",
                        "error": str(error),
                        "history": self.task_history
                    }

                route = re_reasoning.get(
                    "route",
                    {}
                )

                plan = re_reasoning.get(
                    "plan",
                    []
                )

                # -------------------------------------------------
                # If reasoning no longer has an existing tool route
                # -------------------------------------------------

                if route.get(
                    "route"
                ) != "existing_tools":

                    break

            self.active = False

            return {
                "success": False,
                "stage": "replanning_stopped",
                "message": (
                    "The task could not be completed "
                    "with the available execution route."
                ),
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

            try:

                skill_result = (
                    self.skill_builder.build(
                        self.current_goal
                    )
                )

            except Exception as error:

                self.active = False

                return {
                    "success": False,
                    "stage": "skill_builder_error",
                    "message": (
                        "I understood that I need "
                        "a new capability, but the "
                        "capability builder failed."
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
