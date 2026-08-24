"""
Project : Vyom AI
Version : 1.0
Module  : Autonomous Agent

Purpose:
    Persistent autonomous task coordinator.

Architecture:

    User instruction
          |
          v
    Session Context
          |
          v
    Reasoning
          |
          v
       Planning
          |
          v
       ToolManager
          |
          v
       Result
          |
          v
       Context Update

Important:

    This version does NOT generate or execute arbitrary code.

    Capability creation remains controlled by the existing
    SkillBuilder / SkillRegistry architecture.

    Security and permanent self-modification are NOT allowed.
"""

from typing import Any, Dict, Optional, List

from ai_core.brain import Brain
from ai_core.reasoning_engine import ReasoningEngine
from tools.tool_manager import ToolManager
from ai_core.skill_builder import SkillBuilder
from ai_core.session_context import SessionContext


class AutonomousAgent:

    def __init__(
        self,
        tool_manager: Optional[ToolManager] = None,
        brain: Optional[Brain] = None,
        reasoning_engine: Optional[ReasoningEngine] = None,
        max_steps: int = 10
    ):

        # =========================================================
        # COMPONENTS
        # =========================================================

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

        self.skill_builder = SkillBuilder()

        # =========================================================
        # SAFETY
        # =========================================================

        self.max_steps = max(
            1,
            int(max_steps)
        )

        # =========================================================
        # PERSISTENT SESSION
        # =========================================================

        self.context = SessionContext()

        # Backward-compatible fields
        self.current_goal = ""
        self.task_history: List[
            Dict[str, Any]
        ] = []

        self.step_count = 0
        self.active = False

    # =============================================================
    # RESULT CHECK
    # =============================================================

    def _result_is_successful(
        self,
        result
    ) -> bool:

        if result is None:
            return False

        if isinstance(result, dict):

            if "success" in result:
                return bool(
                    result.get("success")
                )

            if "error" in result:
                return False

            return True

        if isinstance(result, bool):
            return result

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
            "do not understand",
            "no tool available",
            "unable to",
            "exception"
        ]

        for phrase in failure_phrases:

            if phrase in text:
                return False

        return True

    # =============================================================
    # UPDATE CONTEXT FROM INTENT
    # =============================================================

    def _update_context_from_intent(
        self,
        intent: Optional[Dict[str, Any]]
    ):

        if not isinstance(intent, dict):
            return

        intent_name = intent.get(
            "intent"
        )

        target = intent.get(
            "target"
        )

        if target:
            self.context.set_current_target(
                target
            )

        # ---------------------------------------------------------
        # OPEN
        # ---------------------------------------------------------

        if intent_name == "open":

            if target:
                self.context.set_current_app(
                    target
                )

        # ---------------------------------------------------------
        # FILE
        # ---------------------------------------------------------

        elif intent_name in (
            "open_file",
            "search_file",
            "search_and_open_file"
        ):

            if target:
                self.context.set_current_file(
                    target
                )

        # ---------------------------------------------------------
        # CLOSE
        # ---------------------------------------------------------

        elif intent_name == "close_app":

            if target:
                self.context.set_current_app(
                    target
                )

    # =============================================================
    # EXECUTE ONE STEP
    # =============================================================

    def _execute_step(
        self,
        step
    ) -> Dict[str, Any]:

        if self.step_count >= self.max_steps:

            return {
                "success": False,
                "stage": "safety_limit",
                "message": (
                    "Autonomous step limit reached."
                )
            }

        if not isinstance(step, dict):

            return {
                "success": False,
                "stage": "invalid_step",
                "message": (
                    "Invalid autonomous plan step."
                )
            }

        self.step_count += 1

        current_intent = step.get(
            "intent"
        )

        step_type = step.get(
            "type",
            ""
        )

        # =========================================================
        # CAPABILITY ROUTES
        # =========================================================

        if step_type in (
            "use_capability",
            "request_new_capability"
        ):

            return {
                "success": False,
                "stage": "capability_route",
                "message": (
                    "This step requires a capability route."
                ),
                "step": step
            }

        # =========================================================
        # RECORD ACTION
        # =========================================================

        self.context.record_action(
            {
                "type": step_type,
                "intent": current_intent,
                "step": step
            }
        )

        # =========================================================
        # EXECUTE
        # =========================================================

        try:

            result = self.tool_manager.execute(
                current_intent
            )

        except Exception as error:

            result = {
                "success": False,
                "error": str(error)
            }

            self.context.record_result(
                result,
                False
            )

            return {
                "success": False,
                "stage": "execution_error",
                "error": str(error),
                "step": step
            }

        # =========================================================
        # VERIFY BASIC RESULT
        # =========================================================

        successful = (
            self._result_is_successful(
                result
            )
        )

        self.context.record_result(
            result,
            successful
        )

        history_item = {
            "step": self.step_count,
            "type": step_type,
            "intent": current_intent,
            "result": result,
            "verified": False,
            "result_success": successful
        }

        self.task_history.append(
            history_item
        )

        # =========================================================
        # PENDING SELECTION DETECTION
        # =========================================================

        if isinstance(result, str):

            result_lower = result.lower()

            if (
                "multiple items found" in result_lower
                or "please select a number" in result_lower
            ):

                self.context.set_pending_selection(
                    self.current_goal
                )

        # =========================================================
        # SUCCESS
        # =========================================================

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

    # =============================================================
    # RUN
    # =============================================================

    def run(
        self,
        goal: str,
        intent: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:

        goal = str(
            goal or ""
        ).strip()

        if not goal:

            return {
                "success": False,
                "stage": "empty_goal",
                "message": (
                    "Please tell me what you want me to do."
                )
            }

        # =========================================================
        # PERSISTENT CONTEXT
        # =========================================================

        self.current_goal = goal
        self.step_count = 0
        self.active = True

        self.context.start_goal(
            goal,
            preserve_context=True
        )

        self._update_context_from_intent(
            intent
        )

        # =========================================================
        # BRAIN
        # =========================================================

        if isinstance(intent, dict):

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

        # =========================================================
        # REASONING
        # =========================================================

        try:

            reasoning = (
                self.reasoning_engine.reason(
                    goal,
                    intent
                )
            )

        except Exception as error:

            self.active = False

            return {
                "success": False,
                "stage": "reasoning_error",
                "error": str(error),
                "goal": goal
            }

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

        # =========================================================
        # EXISTING TOOLS
        # =========================================================

        if route.get(
            "route"
        ) == "existing_tools":

            if not plan:

                self.active = False

                return {
                    "success": False,
                    "stage": "empty_plan",
                    "message": (
                        "I understood the goal, "
                        "but there is no execution step "
                        "available yet."
                    ),
                    "analysis": analysis
                }

            execution_failed = False

            # =====================================================
            # EXECUTION LOOP
            # =====================================================

            for step in plan:

                result = self._execute_step(
                    step
                )

                if result.get(
                    "stage"
                ) == "safety_limit":

                    self.active = False

                    return {
                        "success": False,
                        "stage": "safety_limit",
                        "message": (
                            "The task reached Vyom's "
                            "safe execution limit."
                        ),
                        "history": self.task_history
                    }

                if not result.get(
                    "success",
                    False
                ):

                    execution_failed = True

                    break

            # =====================================================
            # SUCCESS
            # =====================================================

            if not execution_failed:

                self.active = False

                last_result = None

                if self.task_history:

                    last_result = (
                        self.task_history[-1]
                        .get("result")
                    )

                # Task remains available as conversational context.
                self.context.task_state = "completed"

                return {
                    "success": True,
                    "stage": "completed",
                    "result": last_result,
                    "history": self.task_history,
                    "context": self.context.snapshot()
                }

            # =====================================================
            # FAILURE
            # =====================================================

            self.active = False

            return {
                "success": False,
                "stage": "execution_failed",
                "message": (
                    "I could not complete that action."
                ),
                "history": self.task_history,
                "context": self.context.snapshot()
            }

        # =========================================================
        # CAPABILITY FOUND
        # =========================================================

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
                    "I identified the required capability, "
                    "but its executor is not implemented yet."
                ),
                "capability": capability,
                "goal": goal,
                "plan": plan,
                "context": self.context.snapshot()
            }

        # =========================================================
        # MISSING CAPABILITY
        # =========================================================

        if route.get(
            "route"
        ) == "missing_capability":

            try:

                skill_result = (
                    self.skill_builder.build(
                        goal
                    )
                )

            except Exception as error:

                self.active = False

                return {
                    "success": False,
                    "stage": "skill_builder_error",
                    "message": (
                        "I understood the goal, "
                        "but I could not prepare "
                        "the capability plan."
                    ),
                    "error": str(error),
                    "goal": goal
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
                        "I created a capability plan."
                    ),
                    "goal": goal,
                    "plan": plan,
                    "skill": skill_result.get(
                        "skill"
                    ),
                    "next_stage": skill_result.get(
                        "next_stage"
                    ),
                    "context": self.context.snapshot()
                }

            return {
                "success": False,
                "stage": "skill_builder_error",
                "message": str(
                    skill_result
                ),
                "goal": goal
            }

        # =========================================================
        # STOP
        # =========================================================

        self.active = False

        return {
            "success": False,
            "stage": "stopped",
            "message": route.get(
                "reason",
                "Task stopped."
            ),
            "context": self.context.snapshot()
        }

    # =============================================================
    # SESSION CONTEXT
    # =============================================================

    def get_context(self):

        return self.context.snapshot()

    # =============================================================
    # RESET TASK
    # =============================================================

    def reset_task(self):

        self.context.clear_task()

        self.current_goal = ""
        self.task_history = []
        self.step_count = 0
        self.active = False

        try:

            self.reasoning_engine.reset()

        except Exception:

            pass

    # =============================================================
    # RESET COMPLETE SESSION
    # =============================================================

    def reset(self):

        self.context.reset()

        self.current_goal = ""
        self.task_history = []
        self.step_count = 0
        self.active = False

        try:

            self.reasoning_engine.reset()

        except Exception:

            pass
