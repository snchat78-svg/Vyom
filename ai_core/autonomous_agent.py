"""
Project : Vyom AI
Version : 1.1
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
    Goal Compiler
          |
          v
    World State
          |
          v
       Brain
          |
          v
    Deep Reasoning
          |
          v
    Mission Planning
          |
          v
    Capability / Tool Route
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
    - GoalCompiler only understands/structures goals.
    - MissionPlanner only creates/normalizes plans.
    - ReasoningEngine remains the central reasoning layer.
    - DeepReasoner may enrich complex goals.
    - ObservationVerifier checks the actual computer state.
    - SkillBuilder does not execute arbitrary generated code.
    - Autonomous execution is limited by max_steps.
    - Security/core modification is not allowed here.
    - SessionMemory keeps the current conversational state.
    - Existing fast execution for simple commands is preserved.
"""

from typing import Any, Dict, Optional, List

from ai_core.brain import Brain
from ai_core.reasoning_engine import ReasoningEngine
from ai_core.goal_compiler import GoalCompiler
from ai_core.mission_planner import MissionPlanner

from tools.tool_manager import ToolManager

from ai_core.skill_builder import SkillBuilder

from memory.session_memory import SessionMemory

from ai_core.observation_verifier import ObservationVerifier
from ai_core.world_state import WorldStateModel


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

        # =========================================================
        # GOAL-CENTRIC ARCHITECTURE
        # =========================================================

        # GoalCompiler understands natural-language goals.
        #
        # It NEVER executes anything.
        #
        # Existing ReasoningEngine also owns a GoalCompiler,
        # but keeping a reference here allows AutonomousAgent
        # to perform the first goal-understanding stage before
        # deciding whether a fast lane is appropriate.

        self.goal_compiler = GoalCompiler()

        # MissionPlanner never executes actions.
        #
        # It converts structured reasoning/goal information
        # into executable plan steps.

        self.mission_planner = MissionPlanner(
            max_steps=max_steps
        )

        # =========================================================
        # CAPABILITY BUILDING
        # =========================================================

        self.skill_builder = SkillBuilder()

        # =========================================================
        # OBSERVATION / VERIFICATION
        # =========================================================

        self.verifier = ObservationVerifier()

        # Lightweight computer-state observer.
        #
        # It never executes actions.

        self.world_state = WorldStateModel()

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

        # =========================================================
        # CURRENT COMPILED GOAL
        # =========================================================

        self.current_compilation: Dict[
            str,
            Any
        ] = {}

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
    # GOAL COMPILATION
    # =============================================================

    def _compile_goal(
        self,
        goal: str,
        intent: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:

        """
        Convert the user's natural-language goal into
        a structured goal.

        This method only understands the goal.

        It does NOT execute anything.
        """

        try:

            context_snapshot = (
                self.context.snapshot()
            )

            compilation = (
                self.goal_compiler.compile(
                    goal=goal,
                    intent=intent,
                    context=context_snapshot
                )
            )

            if isinstance(
                compilation,
                dict
            ):

                self.current_compilation = (
                    compilation
                )

                return compilation

        except Exception as error:

            compilation = {
                "success": False,
                "understood": False,
                "goal": goal,
                "objective": goal,
                "suggested_intents": [],
                "sub_goals": [],
                "requires_new_capability": True,
                "reason": (
                    "GoalCompiler failed."
                ),
                "error": str(error)
            }

            self.current_compilation = (
                compilation
            )

            return compilation

        compilation = {
            "success": False,
            "understood": False,
            "goal": goal,
            "objective": goal,
            "suggested_intents": [],
            "sub_goals": [],
            "requires_new_capability": True,
            "reason": (
                "GoalCompiler returned "
                "an invalid result."
            )
        }

        self.current_compilation = (
            compilation
        )

        return compilation

    # =============================================================
    # GET SAFE COMPILED INTENT
    # =============================================================

    def _get_compiled_intent(
        self,
        compilation: Optional[
            Dict[str, Any]
        ]
    ) -> Optional[Dict[str, Any]]:

        if not isinstance(
            compilation,
            dict
        ):

            return None

        suggested = compilation.get(
            "suggested_intents",
            []
        )

        if not isinstance(
            suggested,
            list
        ):

            return None

        for candidate in suggested:

            if not isinstance(
                candidate,
                dict
            ):

                continue

            intent_name = str(
                candidate.get(
                    "intent",
                    ""
                )
            ).strip()

            target = str(
                candidate.get(
                    "target",
                    ""
                )
            ).strip()

            if (
                intent_name
                and
                target
            ):

                return {
                    "intent": intent_name,
                    "target": target,
                    "source": candidate.get(
                        "source",
                        "goal_compiler"
                    )
                }

        return None

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
    # CREATE FALLBACK PLAN
    # =============================================================

    def _create_fallback_plan(
        self,
        goal: str,
        analysis: Optional[
            Dict[str, Any]
        ],
        route: Optional[
            Dict[str, Any]
        ],
        compilation: Optional[
            Dict[str, Any]
        ]
    ) -> List[
        Dict[str, Any]
    ]:

        """
        MissionPlanner fallback.

        ReasoningEngine normally creates the plan itself.
        This method exists so AutonomousAgent remains robust
        if an older/custom ReasoningEngine returns analysis
        without a plan.
        """

        try:

            plan = self.mission_planner.plan(
                goal=goal,
                analysis=(
                    analysis
                    if isinstance(
                        analysis,
                        dict
                    )
                    else {}
                ),
                compiled_goal=(
                    compilation
                    if isinstance(
                        compilation,
                        dict
                    )
                    else {}
                ),
                route=(
                    route
                    if isinstance(
                        route,
                        dict
                    )
                    else {}
                )
            )

            if isinstance(
                plan,
                list
            ):

                return plan

        except Exception as error:

            self.task_history.append(
                {
                    "stage": "mission_planner",
                    "error": str(error)
                }
            )

        return []

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
        # INVALID EXECUTION INTENT
        # =========================================================

        if not isinstance(
            current_intent,
            dict
        ):

            return {
                "success": False,
                "stage": "invalid_intent",
                "message": (
                    "The execution step does not "
                    "contain a valid intent."
                ),
                "step": step
            }

        intent_name = str(
            current_intent.get(
                "intent",
                ""
            )
        ).strip()

        intent_target = str(
            current_intent.get(
                "target",
                ""
            )
        ).strip()

        if not intent_name:

            return {
                "success": False,
                "stage": "invalid_intent",
                "message": (
                    "Execution intent is missing."
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
                    "state": (
                        "invalid_verification_result"
                    ),
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
        # ToolManager success alone is NOT enough.
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
        # UPDATE CURRENT CONTEXT
        # =========================================================

        self._update_context_from_intent(
            current_intent
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
                "multiple items found"
                in result_lower
                or
                "please select a number"
                in result_lower
            ):

                self.context.set_pending_selection(
                    target=self.context.current_target,
                    options=[]
                )

        # Dictionary selection result support.

        elif isinstance(
            result,
            dict
        ):

            if (
                result.get(
                    "multiple"
                )
                or
                result.get(
                    "requires_selection"
                )
            ):

                options = result.get(
                    "options",
                    []
                )

                if not isinstance(
                    options,
                    list
                ):

                    options = []

                self.context.set_pending_selection(
                    target=self.context.current_target,
                    options=options
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

        if (
            result_successful
            and
            not verified
        ):

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

        # =========================================================
        # GOAL COMPILER
        # =========================================================

        compilation = self._compile_goal(
            goal=goal,
            intent=intent
        )

        # =========================================================
        # COMPILED INTENT
        # =========================================================

        compiled_intent = (
            self._get_compiled_intent(
                compilation
            )
        )

        # Explicit intent always has priority.
        #
        # If no explicit intent was provided,
        # use the safe intent discovered by GoalCompiler.

        effective_intent = (
            intent
            if isinstance(
                intent,
                dict
            )
            else compiled_intent
        )

        self._update_context_from_intent(
            effective_intent
        )

        # =========================================================
        # FAST LANE FOR SIMPLE, ALREADY-KNOWN ACTIONS
        #
        # GoalCompiler now performs the first understanding stage.
        #
        # A simple command such as:
        #
        #     Chrome खोल दो
        #
        # can still execute immediately.
        #
        # It does NOT bypass safety:
        #
        # GoalCompiler
        #       |
        #       v
        # ToolManager
        #       |
        #       v
        # ObservationVerifier
        #
        # Complex goals continue through ReasoningEngine.
        # =========================================================

        if isinstance(
            effective_intent,
            dict
        ):

            fast_intent = str(
                effective_intent.get(
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

            target_value = str(
                effective_intent.get(
                    "target"
                ) or ""
            ).strip()

            # Only use fast lane when the GoalCompiler itself
            # recognizes the goal as a safe/simple intent,
            # or when the caller supplied an explicit intent.

            compiler_confirmed = bool(
                compiled_intent
            )

            explicit_intent = isinstance(
                intent,
                dict
            )

            if (
                fast_intent in fast_targets
                and
                target_value
                and
                (
                    compiler_confirmed
                    or
                    explicit_intent
                )
            ):

                fast_plan = [
                    {
                        "step": 1,
                        "type": "execute_existing_intent",
                        "goal": goal,
                        "intent": effective_intent
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
                        "goal": goal,
                        "goal_compilation": compilation,
                        "history": self.task_history,
                        "context": self.context.snapshot()
                    }

                # -------------------------------------------------
                # Simple command failed.
                #
                # Do not execute blindly.
                #
                # Return the failure so caller can decide whether
                # to provide another instruction.
                # -------------------------------------------------

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
                    "goal": goal,
                    "goal_compilation": compilation,
                    "history": self.task_history,
                    "context": self.context.snapshot()
                }

        # =========================================================
        # BRAIN
        # =========================================================

        if isinstance(
            effective_intent,
            dict
        ):

            try:

                self.brain.think(
                    effective_intent
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

            state_snapshot = (
                self.world_state.snapshot(
                    self.context.snapshot()
                )
            )

            reasoning = (
                self.reasoning_engine.reason(
                    goal,
                    effective_intent,
                    context=state_snapshot,
                    previous_result=(
                        self.context.last_result
                    )
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
                "goal_compilation": compilation,
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
                "goal": goal,
                "goal_compilation": compilation
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
        # KEEP GOAL COMPILATION AVAILABLE
        # =========================================================

        reasoning_compilation = (
            analysis.get(
                "goal_compilation"
            )
            if isinstance(
                analysis,
                dict
            )
            else None
        )

        if isinstance(
            reasoning_compilation,
            dict
        ):

            compilation = (
                reasoning_compilation
            )

            self.current_compilation = (
                compilation
            )

        # =========================================================
        # FALLBACK PLAN
        #
        # Normally ReasoningEngine already calls MissionPlanner.
        #
        # If a custom/older ReasoningEngine returns no plan,
        # AutonomousAgent uses its own MissionPlanner.
        # =========================================================

        if not plan:

            fallback_plan = (
                self._create_fallback_plan(
                    goal=goal,
                    analysis=analysis,
                    route=route,
                    compilation=compilation
                )
            )

            if fallback_plan:

                plan = fallback_plan

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
                    "goal_compilation": compilation,
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
                        "goal": goal,
                        "goal_compilation": compilation,
                        "analysis": analysis,
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

                    # ---------------------------------------------
                    # Refresh world state after failure.
                    # ---------------------------------------------

                    refreshed_state = (
                        self.world_state.snapshot(
                            self.context.snapshot()
                        )
                    )

                    re_reasoning = (
                        self.reasoning_engine.reason(
                            self.current_goal,
                            effective_intent,
                            context=refreshed_state,
                            previous_result=(
                                self.context.last_result
                            )
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
                # Refresh compilation from re-planning.
                # -------------------------------------------------

                new_compilation = (
                    analysis.get(
                        "goal_compilation"
                    )
                    if isinstance(
                        analysis,
                        dict
                    )
                    else None
                )

                if isinstance(
                    new_compilation,
                    dict
                ):

                    compilation = (
                        new_compilation
                    )

                    self.current_compilation = (
                        compilation
                    )

                # -------------------------------------------------
                # Refresh effective intent if the reasoner
                # discovered a better safe intent.
                # -------------------------------------------------

                refreshed_intent = (
                    self._get_compiled_intent(
                        compilation
                    )
                )

                if refreshed_intent:

                    effective_intent = (
                        refreshed_intent
                    )

                # -------------------------------------------------
                # If ReasoningEngine returned no plan, use the
                # MissionPlanner fallback.
                # -------------------------------------------------

                if not plan:

                    plan = (
                        self._create_fallback_plan(
                            goal=self.current_goal,
                            analysis=analysis,
                            route=route,
                            compilation=compilation
                        )
                    )

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
                "goal_compilation": compilation,
                "history": self.task_history,
                "context": self.context.snapshot()
            }

        # =========================================================
        # CONVERSATION ROUTE
        # =========================================================

        if route.get(
            "route"
        ) == "conversation":

            self.active = False

            return {
                "success": True,
                "stage": "conversation",
                "message": analysis.get(
                    "response",
                    analysis.get(
                        "reason",
                        "The task requires conversation."
                    )
                ),
                "goal": self.current_goal,
                "goal_compilation": compilation,
                "analysis": analysis,
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
                "goal_compilation": compilation,
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
                    "goal_compilation": compilation,
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
                    "goal_compilation": compilation,
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
                "goal_compilation": compilation,
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
            "goal": self.current_goal,
            "goal_compilation": compilation,
            "analysis": analysis,
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
    # GET CURRENT GOAL COMPILATION
    # =============================================================

    def get_goal_compilation(
        self
    ):

        return dict(
            self.current_compilation
        )

    # =============================================================
    # RESET CURRENT TASK
    # =============================================================

    def reset_task(
        self
    ):

        self.context.clear_task()

        self.current_goal = ""

        self.current_compilation = {}

        self.task_history = []

        self.step_count = 0

        self.active = False

        try:

            self.reasoning_engine.reset()

        except Exception:

            pass

        try:

            self.mission_planner.reset()

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

        self.current_compilation = {}

        self.task_history = []

        self.step_count = 0

        self.active = False

        try:

            self.reasoning_engine.reset()

        except Exception:

            pass

        try:

            self.mission_planner.reset()

        except Exception:

            pass
