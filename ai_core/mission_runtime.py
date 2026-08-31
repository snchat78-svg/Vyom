"""
Project : Vyom AI
Version : 1.2
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
    Mission Runtime
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
          +------> Continue
          |
          +------> Retry
          |
          +------> Re-plan
          |
          +------> Complete

Important:

    - Existing ToolManager remains the actual executor.
    - GoalCompiler only understands/structures goals.
    - MissionPlanner only creates/normalizes plans.
    - MissionRuntime owns mission execution state.
    - ReasoningEngine remains the central reasoning layer.
    - DeepReasoner may enrich complex goals.
    - ObservationVerifier checks the actual computer state.
    - SkillBuilder does not execute arbitrary generated code.
    - Autonomous execution is limited by max_steps.
    - Security/core modification is not allowed here.
    - SessionMemory keeps the current conversational state.
    - Existing fast execution for simple commands is preserved.
    - Compound missions are controlled by MissionRuntime.
"""

from typing import Any, Dict, Optional, List

from ai_core.brain import Brain
from ai_core.reasoning_engine import ReasoningEngine
from ai_core.goal_compiler import GoalCompiler
from ai_core.mission_planner import MissionPlanner
from ai_core.mission_runtime import MissionRuntime

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

        self.goal_compiler = GoalCompiler()

        self.mission_planner = MissionPlanner(
            max_steps=max_steps
        )

        # =========================================================
        # MISSION RUNTIME
        #
        # MissionRuntime is now the owner of:
        #
        #     - mission state
        #     - current step
        #     - dependency resolution
        #     - retry state
        #     - re-plan request
        #     - mission history
        #
        # It NEVER executes Windows actions directly.
        # =========================================================

        self.mission_runtime = MissionRuntime(
            max_retries=2,
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

        # ---------------------------------------------------------
        # IMPORTANT:
        #
        # Only return an automatic intent when exactly ONE
        # executable intent was compiled.
        #
        # This prevents a compound mission such as:
        #
        #     Chrome खोलो और Google search करो
        #
        # from accidentally taking the first action through
        # the fast lane and skipping the rest of the mission.
        # ---------------------------------------------------------

        if len(suggested) != 1:

            return None

        candidate = suggested[0]

        if not isinstance(
            candidate,
            dict
        ):

            return None

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
        #
        # MissionRuntime keeps its own runtime step counter.
        #
        # AutonomousAgent also retains its backward-compatible
        # step counter for existing callers/history.
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

        # Keep variable intentionally available for validation/
        # future executor expansion.
        _ = intent_target

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
        # FINAL STEP SUCCESS
        #
        # ToolManager success alone is NOT enough.
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
    # RUN MISSION THROUGH RUNTIME
    # =============================================================

    def _run_mission(
        self,
        goal: str,
        plan: List[
            Dict[str, Any]
        ],
        intent: Optional[
            Dict[str, Any]
        ],
        analysis: Optional[
            Dict[str, Any]
        ],
        compilation: Optional[
            Dict[str, Any]
        ],
        route: Optional[
            Dict[str, Any]
        ]
    ) -> Dict[str, Any]:

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
                "goal": goal,
                "analysis": analysis,
                "goal_compilation": compilation,
                "context": self.context.snapshot()
            }

        # =========================================================
        # START MISSION RUNTIME
        # =========================================================

        runtime_snapshot = (
            self.mission_runtime.start(
                goal=goal,
                plan=plan
            )
        )

        # Defensive validation.

        if not isinstance(
            runtime_snapshot,
            dict
        ):

            self.active = False

            self.context.mark_failed()

            return {
                "success": False,
                "stage": "mission_runtime_start_error",
                "message": (
                    "Mission Runtime could not "
                    "start the mission."
                ),
                "goal": goal,
                "context": self.context.snapshot()
            }

        # =========================================================
        # MISSION LOOP
        #
        # MissionRuntime selects each dependency-ready step.
        #
        # AutonomousAgent only performs:
        #
        #     execute -> observe -> verify
        #
        # and reports the result back to Runtime.
        # =========================================================

        while (
            self.step_count
            < self.max_steps
        ):

            # -----------------------------------------------------
            # Re-plan requested
            # -----------------------------------------------------

            if self.mission_runtime.needs_replan():

                # If Runtime explicitly needs a new plan,
                # ReasoningEngine gets the latest world state
                # and session result.

                break

            # -----------------------------------------------------
            # Get next dependency-ready step.
            # -----------------------------------------------------

            step = (
                self.mission_runtime.get_next_step()
            )

            # -----------------------------------------------------
            # Runtime finished.
            # -----------------------------------------------------

            if step is None:

                runtime = (
                    self.mission_runtime.snapshot()
                )

                state = runtime.get(
                    "mission_state"
                )

                if state == "completed":

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
                        "mission": runtime,
                        "context": self.context.snapshot()
                    }

                if state == "blocked":

                    self.active = False

                    return {
                        "success": False,
                        "stage": "mission_blocked",
                        "message": runtime.get(
                            "last_error",
                            "Mission is blocked."
                        ),
                        "goal": goal,
                        "goal_compilation": compilation,
                        "analysis": analysis,
                        "mission": runtime,
                        "context": self.context.snapshot()
                    }

                break

            # -----------------------------------------------------
            # Execute the selected step.
            # -----------------------------------------------------

            result = self._execute_step(
                step
            )

            step_id = step.get(
                "id"
            )

            # -----------------------------------------------------
            # Safety limit.
            # -----------------------------------------------------

            if result.get(
                "stage"
            ) == "safety_limit":

                self.mission_runtime.mark_failed(
                    step_id=step_id,
                    result=result,
                    reason=(
                        "Autonomous step limit reached."
                    )
                )

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
                    "mission": (
                        self.mission_runtime.snapshot()
                    ),
                    "context": self.context.snapshot()
                }

            # -----------------------------------------------------
            # Capability route.
            # -----------------------------------------------------

            if result.get(
                "stage"
            ) == "capability_route":

                self.mission_runtime.block(
                    reason=(
                        "Capability route requires "
                        "a capability executor."
                    ),
                    capability=step.get(
                        "capability"
                    )
                )

                self.active = False

                return {
                    "success": False,
                    "stage": "capability_route",
                    "message": result.get(
                        "message"
                    ),
                    "step": step,
                    "history": self.task_history,
                    "mission": (
                        self.mission_runtime.snapshot()
                    ),
                    "context": self.context.snapshot()
                }

            # -----------------------------------------------------
            # STEP SUCCESS
            # -----------------------------------------------------

            if result.get(
                "success",
                False
            ):

                self.mission_runtime.mark_completed(
                    step_id=step_id,
                    result=result.get(
                        "result"
                    ),
                    verification=result.get(
                        "verification"
                    )
                )

                # Runtime now decides which next step is ready.

                continue

            # -----------------------------------------------------
            # STEP FAILURE / VERIFICATION FAILURE
            # -----------------------------------------------------

            retry_available = (
                self.mission_runtime.mark_failed(
                    step_id=step_id,
                    result=result.get(
                        "result"
                    ),
                    reason=result.get(
                        "stage",
                        "execution_failed"
                    ),
                    verification=result.get(
                        "verification"
                    )
                )
            )

            # -----------------------------------------------------
            # Bounded retry
            # -----------------------------------------------------

            if retry_available:

                continue

            # -----------------------------------------------------
            # Retries exhausted.
            #
            # Runtime has now requested re-planning.
            # -----------------------------------------------------

            if self.mission_runtime.needs_replan():

                break

        # =========================================================
        # RE-PLANNING
        # =========================================================

        if self.mission_runtime.needs_replan():

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
                    "mission": (
                        self.mission_runtime.snapshot()
                    ),
                    "context": self.context.snapshot()
                }

            try:

                refreshed_state = (
                    self.world_state.snapshot(
                        self.context.snapshot()
                    )
                )

                re_reasoning = (
                    self.reasoning_engine.reason(
                        self.current_goal,
                        intent,
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
                    "mission": (
                        self.mission_runtime.snapshot()
                    ),
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
                    "history": self.task_history,
                    "mission": (
                        self.mission_runtime.snapshot()
                    ),
                    "context": self.context.snapshot()
                }

            new_analysis = re_reasoning.get(
                "analysis",
                {}
            )

            new_route = re_reasoning.get(
                "route",
                {}
            )

            new_reasoning_plan = re_reasoning.get(
                "plan",
                []
            )

            if not isinstance(
                new_analysis,
                dict
            ):

                new_analysis = {}

            if not isinstance(
                new_route,
                dict
            ):

                new_route = {}

            if not isinstance(
                new_reasoning_plan,
                list
            ):

                new_reasoning_plan = []

            # -----------------------------------------------------
            # Refresh compilation if the ReasoningEngine exposes it.
            # -----------------------------------------------------

            new_compilation = (
                new_analysis.get(
                    "compiled_goal"
                )
                if isinstance(
                    new_analysis,
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

            # -----------------------------------------------------
            # Fallback plan if ReasoningEngine didn't provide one.
            # -----------------------------------------------------

            if not new_reasoning_plan:

                new_reasoning_plan = (
                    self._create_fallback_plan(
                        goal=self.current_goal,
                        analysis=new_analysis,
                        route=new_route,
                        compilation=compilation
                    )
                )

            # -----------------------------------------------------
            # New route must have an executable/mission plan.
            # -----------------------------------------------------

            if new_route.get(
                "route"
            ) not in (
                "existing_tools",
                "mission"
            ):

                self.active = False

                return {
                    "success": False,
                    "stage": "replanning_route_changed",
                    "message": (
                        "The task now requires "
                        "a different capability "
                        "or execution route."
                    ),
                    "route": new_route,
                    "analysis": new_analysis,
                    "history": self.task_history,
                    "mission": (
                        self.mission_runtime.snapshot()
                    ),
                    "context": self.context.snapshot()
                }

            if not new_reasoning_plan:

                self.active = False

                self.context.mark_failed()

                return {
                    "success": False,
                    "stage": "empty_replanned_plan",
                    "message": (
                        "I could not create a "
                        "new executable mission plan."
                    ),
                    "analysis": new_analysis,
                    "history": self.task_history,
                    "context": self.context.snapshot()
                }

            # -----------------------------------------------------
            # Apply new mission plan to Runtime.
            # -----------------------------------------------------

            if not self.mission_runtime.apply_replan(
                new_reasoning_plan
            ):

                self.active = False

                self.context.mark_failed()

                return {
                    "success": False,
                    "stage": "replan_apply_failed",
                    "message": (
                        "The new mission plan "
                        "could not be applied."
                    ),
                    "history": self.task_history,
                    "mission": (
                        self.mission_runtime.snapshot()
                    ),
                    "context": self.context.snapshot()
                }

            # -----------------------------------------------------
            # Continue from the updated Runtime.
            #
            # Do not call _run_mission() recursively.
            # Continue the same method with the new plan.
            # -----------------------------------------------------

            return self._continue_replanned_mission(
                goal=self.current_goal,
                intent=intent,
                analysis=new_analysis,
                compilation=compilation,
                route=new_route
            )

        # =========================================================
        # MISSION STOPPED WITHOUT A REPLAN
        # =========================================================

        self.active = False

        self.context.mark_failed()

        return {
            "success": False,
            "stage": "mission_stopped",
            "message": (
                "The mission could not be completed."
            ),
            "goal": goal,
            "goal_compilation": compilation,
            "analysis": analysis,
            "history": self.task_history,
            "mission": (
                self.mission_runtime.snapshot()
            ),
            "context": self.context.snapshot()
        }

    # =============================================================
    # CONTINUE REPLANNED MISSION
    # =============================================================

    def _continue_replanned_mission(
        self,
        goal: str,
        intent: Optional[Dict[str, Any]],
        analysis: Dict[str, Any],
        compilation: Dict[str, Any],
        route: Dict[str, Any]
    ) -> Dict[str, Any]:

        """
        Continue executing an already-started Runtime mission.

        This method deliberately does not call MissionRuntime.start()
        again, because start() would reset the live mission state.
        """

        while (
            self.step_count
            < self.max_steps
        ):

            if self.mission_runtime.needs_replan():

                break

            step = (
                self.mission_runtime.get_next_step()
            )

            if step is None:

                runtime = (
                    self.mission_runtime.snapshot()
                )

                if runtime.get(
                    "mission_state"
                ) == "completed":

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
                        "mission": runtime,
                        "context": self.context.snapshot()
                    }

                break

            result = self._execute_step(
                step
            )

            step_id = step.get(
                "id"
            )

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
                        "reached the safe step limit."
                    ),
                    "history": self.task_history,
                    "mission": (
                        self.mission_runtime.snapshot()
                    ),
                    "context": self.context.snapshot()
                }

            if result.get(
                "stage"
            ) == "capability_route":

                self.active = False

                self.mission_runtime.block(
                    reason=result.get(
                        "message",
                        "Capability route required."
                    ),
                    capability=step.get(
                        "capability"
                    )
                )

                return {
                    "success": False,
                    "stage": "capability_route",
                    "message": result.get(
                        "message"
                    ),
                    "mission": (
                        self.mission_runtime.snapshot()
                    ),
                    "context": self.context.snapshot()
                }

            if result.get(
                "success",
                False
            ):

                self.mission_runtime.mark_completed(
                    step_id=step_id,
                    result=result.get(
                        "result"
                    ),
                    verification=result.get(
                        "verification"
                    )
                )

                continue

            retry_available = (
                self.mission_runtime.mark_failed(
                    step_id=step_id,
                    result=result.get(
                        "result"
                    ),
                    reason=result.get(
                        "stage",
                        "execution_failed"
                    ),
                    verification=result.get(
                        "verification"
                    )
                )

            if retry_available:

                continue

            break

        runtime = (
            self.mission_runtime.snapshot()
        )

        if runtime.get(
            "mission_state"
        ) == "completed":

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
                "mission": runtime,
                "context": self.context.snapshot()
            }

        self.active = False
        self.context.mark_failed()

        return {
            "success": False,
            "stage": "replanned_mission_stopped",
            "message": (
                "The replanned mission could not "
                "be completed within the safe limit."
            ),
            "goal": goal,
            "goal_compilation": compilation,
            "analysis": analysis,
            "route": route,
            "history": self.task_history,
            "mission": runtime,
            "context": self.context.snapshot()
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

        # New run = new runtime mission.
        #
        # SessionMemory itself remains persistent.

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
        # SIMPLE FAST LANE
        #
        # IMPORTANT:
        #
        # It only runs when exactly one safe executable intent
        # was recognized.
        #
        # Compound goals ALWAYS continue to Reasoning/Mission.
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

            compiler_confirmed = bool(
                compiled_intent
            )

            explicit_intent = isinstance(
                intent,
                dict
            )

            # Also ensure the compilation itself is not compound.

            suggested_intents = compilation.get(
                "suggested_intents",
                []
            )

            single_compiled_action = (
                isinstance(
                    suggested_intents,
                    list
                )
                and
                len(suggested_intents) == 1
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
                and
                (
                    explicit_intent
                    or
                    single_compiled_action
                )
            ):

                # -------------------------------------------------
                # Brain still observes explicit intent.
                # -------------------------------------------------

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

                fast_plan = [
                    {
                        "step": 1,
                        "id": "action_1",
                        "type": (
                            "execute_existing_intent"
                        ),
                        "goal": goal,
                        "intent": effective_intent,
                        "depends_on": [],
                        "status": "pending"
                    }
                ]

                # Use the normal MissionRuntime even for one-step
                # commands. This keeps a single execution lifecycle
                # across fast and mission paths.

                result = self._run_mission(
                    goal=goal,
                    plan=fast_plan,
                    intent=effective_intent,
                    analysis={
                        "type": "known_action",
                        "goal": goal
                    },
                    compilation=compilation,
                    route={
                        "route": "existing_tools",
                        "reason": (
                            "Single known action."
                        )
                    }
                )

                return result

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
            analysis,
            dict
        ):

            analysis = {}

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

        # =========================================================
        # KEEP COMPILED GOAL
        # =========================================================

        reasoning_compilation = (
            analysis.get(
                "compiled_goal"
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
        # EXECUTABLE / MISSION ROUTES
        #
        # ReasoningEngine uses:
        #
        #     existing_tools
        #     mission
        #
        # for known executable goals.
        # =========================================================

        if route.get(
            "route"
        ) in (
            "existing_tools",
            "mission"
        ):

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

            return self._run_mission(
                goal=goal,
                plan=plan,
                intent=effective_intent,
                analysis=analysis,
                compilation=compilation,
                route=route
            )

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

            self.mission_runtime.block(
                reason=(
                    "Required capability is available "
                    "but its executor is not implemented "
                    "in AutonomousAgent yet."
                ),
                capability=capability
            )

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
                "mission": (
                    self.mission_runtime.snapshot()
                ),
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
    # GET MISSION STATE
    # =============================================================

    def get_mission_state(
        self
    ):

        return self.mission_runtime.snapshot()

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

        self.mission_runtime.reset()

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

        self.mission_runtime.reset()

        try:

            self.reasoning_engine.reset()

        except Exception:

            pass

        try:

            self.mission_planner.reset()

        except Exception:

            pass
