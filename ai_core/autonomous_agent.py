"""
Project : Vyom AI
Version : 0.2
Module  : Autonomous Agent

Purpose:
    Connect Vyom's natural-language command flow with the
    existing IntentEngine and ToolManager.

    Current architecture:

        User Command
             |
             v
        IntentEngine
             |
             v
        AutonomousAgent
             |
        +----+----+
        |         |
       Brain   ToolManager
                  |
                  v
              Windows
                  |
                  v
               Result

IMPORTANT:
    This version does NOT generate or execute arbitrary code.

    It creates the foundation for future autonomous reasoning.

Future versions will add:

    - real reasoning model
    - multi-step planning
    - dynamic tool selection
    - observation/reasoning loop
    - capability discovery
    - self-created skills
    - sandbox testing
    - browser automation
    - vision
    - coding agent
"""

from typing import Any, Dict, Optional, List

from ai_core.brain import Brain
from tools.tool_manager import ToolManager


class AutonomousAgent:

    # =========================================================
    # INITIALIZATION
    # =========================================================

    def __init__(
        self,
        tool_manager: Optional[ToolManager] = None,
        brain: Optional[Brain] = None,
        max_steps: int = 10
    ):
        """
        Initialize AutonomousAgent.
        """

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
    # NORMALIZE COMMAND
    # =========================================================

    def _normalize_goal(
        self,
        goal: Any
    ) -> str:

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
        goal: str,
        intent: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Understand the current goal.

        v0.2 uses the existing IntentEngine result.

        A future reasoning model will expand this method.
        """

        clean_goal = self._normalize_goal(
            goal
        )

        if not clean_goal:

            return {
                "understood": False,
                "goal": "",
                "intent": intent,
                "reason": "Empty command."
            }

        return {
            "understood": True,
            "goal": clean_goal,
            "intent": intent
        }

    # =========================================================
    # PLAN
    # =========================================================

    def create_plan(
        self,
        understood: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Create an initial execution plan.

        v0.2 contains one executable step.

        This separation allows a future reasoning model to
        generate multiple steps.
        """

        if not understood.get(
            "understood",
            False
        ):

            return []

        return [
            {
                "step": 1,
                "action": "execute_intent",
                "goal": understood.get(
                    "goal",
                    ""
                ),
                "intent": understood.get(
                    "intent"
                )
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
        Decide what to execute.

        For v0.2 the IntentEngine has already converted the
        natural-language command into an intent.

        Future versions will allow the Agent itself to decide
        which tool/capability should be used.
        """

        return {
            "action": step.get(
                "action",
                "execute_intent"
            ),
            "goal": step.get(
                "goal",
                ""
            ),
            "intent": step.get(
                "intent"
            )
        }

    # =========================================================
    # EXECUTE
    # =========================================================

    def execute_decision(
        self,
        decision: Dict[str, Any]
    ) -> Any:
        """
        Execute through the existing ToolManager.

        IMPORTANT:

        We intentionally do NOT bypass ToolManager.

        Existing application/file/process handling remains
        intact.
        """

        intent = decision.get(
            "intent"
        )

        if not isinstance(
            intent,
            dict
        ):

            return {
                "success": False,
                "status": "invalid_intent",
                "message": (
                    "No valid intent was provided."
                )
            }

        try:

            result = self.tool_manager.execute(
                intent
            )

            return {
                "success": True,
                "status": "executed",
                "result": result
            }

        except Exception as error:

            return {
                "success": False,
                "status": "execution_error",
                "error": str(error)
            }

    # =========================================================
    # OBSERVE
    # =========================================================

    def observe(
        self,
        result: Any
    ) -> Dict[str, Any]:
        """
        Observe the result of an action.
        """

        if not isinstance(
            result,
            dict
        ):

            return {
                "success": True,
                "status": "completed",
                "result": result
            }

        return result

    # =========================================================
    # SHOULD CONTINUE
    # =========================================================

    def should_continue(
        self,
        observation: Dict[str, Any]
    ) -> bool:
        """
        Decide whether another step is required.

        v0.2 has one-step execution.

        Multi-step reasoning will be added later.
        """

        return False

    # =========================================================
    # RECORD
    # =========================================================

    def _record(
        self,
        step: int,
        decision: Dict[str, Any],
        observation: Dict[str, Any]
    ):

        self.task_history.append(
            {
                "step": step,
                "decision": decision,
                "observation": observation
            }
        )

    # =========================================================
    # RUN
    # =========================================================

    def run(
        self,
        goal: str,
        intent: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Main autonomous execution entry point.

        Pipeline:

            Goal
             ↓
          Understand
             ↓
            Plan
             ↓
           Decide
             ↓
          Execute
             ↓
          Observe
             ↓
           Result
        """

        self.current_goal = self._normalize_goal(
            goal
        )

        self.task_history = []

        self.step_count = 0

        self.active = True

        # =====================================================
        # UNDERSTAND
        # =====================================================

        understood = self.understand(
            self.current_goal,
            intent
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
                    "Could not understand command."
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
                        "decision": {
                            "action": "brain"
                        },
                        "observation": {
                            "success": False,
                            "status": "brain_error",
                            "error": str(error)
                        }
                    }
                )

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
                    "Could not create an execution plan."
                ),
                "history": self.task_history
            }

        # =====================================================
        # AUTONOMOUS EXECUTION LOOP
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
                decision,
                observation
            )

            # -------------------------------------------------
            # CONTINUE
            # -------------------------------------------------

            if not self.should_continue(
                observation
            ):

                self.active = False

                return {
                    "success": observation.get(
                        "success",
                        True
                    ),
                    "stage": "completed",
                    "goal": self.current_goal,
                    "message": (
                        "Autonomous execution completed."
                    ),
                    "result": observation.get(
                        "result",
                        observation
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
