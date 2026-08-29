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
    Session Memory
          |
          v
       Brain
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
    Observation / Verification
          |
          v
    Session Update
          |
          v
    Continue / Re-plan

Important:

    - Existing ToolManager remains the actual executor.
    - ObservationVerifier checks the actual computer state.
    - SkillBuilder does not execute arbitrary generated code.
    - Autonomous execution is limited by max_steps.
    - Security/core modification is not allowed here.
    - SessionMemory keeps the current conversational state.
"""

from typing import Any, Dict, Optional, List

from ai_core.brain import Brain
from ai_core.reasoning_engine import ReasoningEngine
from tools.tool_manager import ToolManager
from ai_core.skill_builder import SkillBuilder
from memory.session_memory import SessionMemory
from ai_core.observation_verifier import ObservationVerifier


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
        # OBSERVATION / VERIFICATION
        # =========================================================

        self.verifier = ObservationVerifier()

        # =========================================================
        # SESSION MEMORY
        # =========================================================

        self.context = SessionMemory()

        # =========================================================
        # SAFETY
        # =========================================================

        self.max_steps = max(
            1,
            int(max_steps)
        )

        # =========================================================
        # BACKWARD-COMPATIBLE TASK STATE
        # =========================================================

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
    # UPDATE SESSION CONTEXT FROM INTENT
    # =============================================================

    def _update_context_from_intent(
        self,
        intent: Optional[Dict[str, Any]]
    ):

        if not isinstance(
            intent,
            dict
        ):

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
        # OPEN APPLICATION
        # ---------------------------------------------------------

        if intent_name == "open":

            if target:

                self.context.set_current_app(
                    target
                )

        # ---------------------------------------------------------
        # FILE OPERATIONS
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
        # CLOSE APPLICATION
        # ---------------------------------------------------------

        elif intent_name == "close_app":

            if target:

                self.context.set_current_app(
                    target
                )

    # =============================================================
    # EXECUTE ONE PLAN STEP
    # =============================================================

    def _execute_step(
        self,
        step
    ) -> Dict[str, Any]:

        # =========================================================
        # VALIDATE STEP
        # =========================================================

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

        # =========================================================
        # SAFETY LIMIT
        # =========================================================

        if self.step_count >= self.max_steps:

            return {
                "success": False,
                "stage": "safety_limit",
                "message": (
                    "Autonomous step limit reached."
                )
            }

        # =========================================================
        # STEP COUNT
        # =========================================================

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
                    "This plan step requires "
                    "a capability route."
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
        # EXECUTE THROUGH TOOL MANAGER
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

            history_item = {
                "step": self.step_count,
                "type": step_type,
                "intent": current_intent,
                "result": result,
                "verified": False,
                "result_success": False
            }

            self.task_history.append(
                history_item
            )

            return {
                "success": False,
                "stage": "execution_error",
                "error": str(error),
                "step": step
            }

        # =========================================================
        # BASIC RESULT VERIFICATION
        # =========================================================

        result_successful = (
            self._result_is_successful(
                result
            )
        )

        # =========================================================
        # OBSERVATION / ACTUAL COMPUTER STATE VERIFICATION
        # =========================================================

        verification = {}

        verified = False

        try:

            verification = (
                self.verifier.verify(
                    current_intent,
                    result
                )
            )

            if isinstance(
                verification,
                dict
            ):

                verified = bool(
                    verification.get(
                        "verified",
                        False
                    )
                )

            else:

                verification = {
                    "verified": False,
                    "state": "invalid_verification_result",
                    "reason": (
                        "ObservationVerifier returned "
                        "an invalid result."
                    )
                }

                verified = False

        except Exception as error:

            verification = {
                "verified": False,
                "state": "verification_error",
                "reason": (
                    "Observation verification failed."
                ),
                "error": str(error)
            }

            verified = False

        # =========================================================
        # FINAL TASK SUCCESS
        #
        # A ToolManager success result alone is NOT enough.
        #
        # The action must also be verified by observing the
        # expected computer state.
        # =========================================================

        successful = (
            result_successful
            and
            verified
        )

        self.context.record_result(
            result,
            successful
        )

        # =========================================================
        # HISTORY
        # =========================================================

        history_item = {
            "step": self.step_count,
            "type": step_type,
            "intent": current_intent,
            "result": result,
            "verified": verified,
            "verification": verification,
            "result_success": result_successful
        }

        self.task_history.append(
            history_item
        )

        # =========================================================
        # PENDING SELECTION DETECTION
        # =========================================================

        if isinstance(
            result,
            str
        ):

            result_lower = result.lower()

            if (
                "multiple items found" in result_lower
                or
                "please select a number" in result_lower
            ):

                self.context.set_pending_selection(
                    target=self.context.current_target,
                    options=[]
                )

        # =========================================================
        # SUCCESS
        # =========================================================

        if successful:

            return {
                "success": True,
                "stage": "verified",
                "result": result,
                "verification": verification,
                "step": self.step_count
            }

        # =========================================================
        # VERIFICATION FAILURE
        # =========================================================

        if result_successful and not verified:

            return {
                "success": False,
                "stage": "verification_failed",
                "result": result,
                "verification": verification,
                "step": self.step_count
            }

        # =========================================================
        # FAILURE
        # =========================================================

        return {
            "success": False,
            "stage": "execution_failed",
            "result": result,
            "verification": verification,
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
        # PERSISTENT SESSION
        # =========================================================

        self.current_goal = goal

        self.step_count = 0

        self.active = True

        # IMPORTANT:
        #
        # Do NOT clear previous session context here.
        #
        # This allows:
        #
        #     open notepad
        #     one
        #     type hello
        #
        # to remain in one conversational session.

        try:

            self.context.start_task(
                goal,
                preserve_context=True
            )

        except Exception as error:

            self.active = False

            return {
                "success": False,
                "stage": "session_error",
                "message": (
                    "Session memory could not "
                    "start the task."
                ),
                "error": str(error)
            }

        self._update_context_from_intent(
            intent
        )

        # =========================================================
        # FAST LANE FOR SIMPLE, ALREADY-KNOWN ACTIONS
        #
        # A simple command such as "Chrome खोल दो" should not spend
        # time in unnecessary planning layers. It still goes through
        # ToolManager and ObservationVerifier, so the action remains
        # observable and verifiable.
        # =========================================================

        if isinstance(
            intent,
            dict
        ):

            fast_intent = str(
                intent.get(
                    "intent",
                    ""
                )
            ).strip().lower()

            fast_targets = (
                "open",
                "open_file",
                "search_file",
                "search_and_open_file",
                "close_app"
            )

            if (
                fast_intent in fast_targets
                and
                str(
                    intent.get(
                        "target"
                    ) or ""
                ).strip()
            ):

                fast_plan = [
                    {
                        "step": 1,
                        "type": "execute_existing_intent",
                        "goal": goal,
                        "intent": intent
                    }
                ]

                fast_result = self._execute_step(
                    fast_plan[0]
                )

                if fast_result.get(
                    "success",
                    False
                ):

                    self.active = False

                    self.context.mark_completed()

                    return {
                        "success": True,
                        "stage": "completed",
                        "result": fast_result.get(
                            "result"
                        ),
                        "history": self.task_history,
                        "context": self.context.snapshot()
                    }

                # Do not run the old multi-step re-planning loop for a
                # simple command that already has a concrete intent.

                self.active = False

                self.context.mark_failed()

                return {
                    "success": False,
                    "stage": fast_result.get(
                        "stage",
                        "execution_failed"
                    ),
                    "result": fast_result.get(
                        "result"
                    ),
                    "verification": fast_result.get(
                        "verification"
                    ),
                    "message": fast_result.get(
                        "message",
                        "The requested action could not be completed."
                    ),
                    "history": self.task_history,
                    "context": self.context.snapshot()
                }

        # =========================================================
        # BRAIN
        # =========================================================

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

        # =========================================================
        # INITIAL REASONING
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

            self.context.mark_failed()

            return {
                "success": False,
                "stage": "reasoning_error",
                "error": str(error),
                "goal": goal,
                "context": self.context.snapshot()
            }

        # =========================================================
        # REASONING DATA
        # =========================================================

        if not isinstance(
            reasoning,
            dict
        ):

            self.active = False

            self.context.mark_failed()

            return {
                "success": False,
                "stage": "invalid_reasoning_result",
                "message": (
                    "ReasoningEngine returned "
                    "an invalid result."
                ),
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

        if not isinstance(
            route,
            dict
        ):

            route = {}

        if not isinstance(
            plan,
            list
        ):

            plan = []

        if not isinstance(
            analysis,
            dict
        ):

            analysis = {}

        # =========================================================
        # EXISTING TOOLS
        # =========================================================

        if route.get(
            "route"
        ) == "existing_tools":

            if not plan:

                self.active = False

                self.context.mark_failed()

                return {
                    "success": False,
                    "stage": "empty_plan",
                    "message": (
                        "I understood the goal, "
                        "but there is no execution "
                        "step available yet."
                    ),
                    "analysis": analysis,
                    "context": self.context.snapshot()
                }

            # =====================================================
            # EXECUTION / RE-PLANNING LOOP
            # =====================================================

            while (
                self.step_count
                < self.max_steps
            ):

                execution_failed = False

                # -------------------------------------------------
                # EXECUTE CURRENT PLAN
                # -------------------------------------------------

                for step in plan:

                    result = self._execute_step(
                        step
                    )

                    # ---------------------------------------------
                    # SAFETY LIMIT
                    # ---------------------------------------------

                    if result.get(
                        "stage"
                    ) == "safety_limit":

                        self.active = False

                        self.context.mark_failed()

                        return {
                            "success": False,
                            "stage": "safety_limit",
                            "message": (
                                "The autonomous task "
                                "stopped because the "
                                "safe execution limit "
                                "was reached."
                            ),
                            "history": self.task_history,
                            "context": self.context.snapshot()
                        }

                    # ---------------------------------------------
                    # CAPABILITY ROUTE
                    # ---------------------------------------------

                    if result.get(
                        "stage"
                    ) == "capability_route":

                        execution_failed = True

                        break

                    # ---------------------------------------------
                    # EXECUTION FAILED
                    # ---------------------------------------------

                    if not result.get(
                        "success",
                        False
                    ):

                        execution_failed = True

                        break

                # =================================================
                # SUCCESS
                # =================================================

                if not execution_failed:

                    self.active = False

                    self.context.mark_completed()

                    last_result = None

                    if self.task_history:

                        last_result = (
                            self.task_history[-1]
                            .get(
                                "result"
                            )
                        )

                    return {
                        "success": True,
                        "stage": "completed",
                        "result": last_result,
                        "history": self.task_history,
                        "context": self.context.snapshot()
                    }

                # =================================================
                # FAILED -> REASON AGAIN
                # =================================================

                if self.step_count >= self.max_steps:

                    self.active = False

                    self.context.mark_failed()

                    return {
                        "success": False,
                        "stage": "safety_limit",
                        "message": (
                            "Autonomous re-planning "
                            "limit reached."
                        ),
                        "history": self.task_history,
                        "context": self.context.snapshot()
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

                    self.context.mark_failed()

                    return {
                        "success": False,
                        "stage": "replanning_error",
                        "error": str(error),
                        "history": self.task_history,
                        "context": self.context.snapshot()
                    }

                if not isinstance(
                    re_reasoning,
                    dict
                ):

                    self.active = False

                    self.context.mark_failed()

                    return {
                        "success": False,
                        "stage": "invalid_replanning_result",
                        "message": (
                            "Re-planning returned "
                            "an invalid result."
                        ),
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

                analysis = re_reasoning.get(
                    "analysis",
                    {}
                )

                if not isinstance(
                    route,
                    dict
                ):

                    route = {}

                if not isinstance(
                    plan,
                    list
                ):

                    plan = []

                if not isinstance(
                    analysis,
                    dict
                ):

                    analysis = {}

                # -------------------------------------------------
                # Route changed
                # -------------------------------------------------

                if route.get(
                    "route"
                ) != "existing_tools":

                    break

            # =====================================================
            # REPLANNING STOPPED
            # =====================================================

            self.active = False

            self.context.mark_failed()

            return {
                "success": False,
                "stage": "replanning_stopped",
                "message": (
                    "The task could not be completed "
                    "with the available execution route."
                ),
                "analysis": analysis,
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
                    "The required capability was "
                    "identified but its executor is "
                    "not implemented yet."
                ),
                "capability": capability,
                "goal": self.current_goal,
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
                        self.current_goal
                    )
                )

            except Exception as error:

                self.active = False

                self.context.mark_failed()

                return {
                    "success": False,
                    "stage": "skill_builder_error",
                    "message": (
                        "I understood the goal, "
                        "but I could not prepare "
                        "the capability plan."
                    ),
                    "error": str(error),
                    "goal": self.current_goal,
                    "plan": plan,
                    "context": self.context.snapshot()
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
                        "I analyzed the goal and "
                        "created a capability plan."
                    ),
                    "goal": self.current_goal,
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
                "goal": self.current_goal,
                "plan": plan,
                "context": self.context.snapshot()
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
    # GET SESSION CONTEXT
    # =============================================================

    def get_context(
        self
    ):

        return self.context.snapshot()

    # =============================================================
    # RESET CURRENT TASK
    # =============================================================

    def reset_task(
        self
    ):

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

    def reset(
        self
    ):

        self.context.reset()

        self.current_goal = ""

        self.task_history = []

        self.step_count = 0

        self.active = False

        try:

            self.reasoning_engine.reset()

        except Exception:

            pass
