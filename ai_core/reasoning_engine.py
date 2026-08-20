"""
Project : Vyom AI
Version : 0.1
Module  : Reasoning Engine

Purpose:
    Provide a lightweight reasoning/planning layer for Vyom.

IMPORTANT:

    This module intentionally has NO external AI/LLM dependency.

    It provides the architecture required for:

        Goal Understanding
        Decision
        Planning
        Capability Selection
        Verification

    Future versions can connect a real reasoning model here
    without changing the main Agent architecture.
"""


class ReasoningEngine:

    # =========================================================
    # INITIALIZATION
    # =========================================================

    def __init__(self):

        self.last_goal = ""

        self.last_analysis = None

        self.last_plan = []

    # =========================================================
    # NORMALIZE
    # =========================================================

    def _normalize(
        self,
        text
    ):

        if text is None:

            return ""

        return str(
            text
        ).strip()

    # =========================================================
    # ANALYZE GOAL
    # =========================================================

    def analyze_goal(
        self,
        goal,
        intent=None
    ):
        """
        Analyze the user's goal.

        The current version uses lightweight deterministic
        reasoning.

        It does NOT pretend to understand arbitrary tasks
        like a full AI model yet.
        """

        goal = self._normalize(
            goal
        )

        self.last_goal = goal

        if not goal:

            analysis = {
                "understood": False,
                "goal": "",
                "type": "empty",
                "complexity": "none",
                "intent": intent,
                "reason": "Empty goal."
            }

            self.last_analysis = analysis

            return analysis

        # -----------------------------------------------------
        # Known intent
        # -----------------------------------------------------

        if isinstance(
            intent,
            dict
        ):

            intent_name = str(
                intent.get(
                    "intent",
                    "unknown"
                )
            ).strip()

            if (
                intent_name
                and
                intent_name != "unknown"
            ):

                analysis = {
                    "understood": True,
                    "goal": goal,
                    "type": "known_command",
                    "complexity": "simple",
                    "intent": intent,
                    "reason": (
                        "Existing IntentEngine "
                        "understood the command."
                    )
                }

                self.last_analysis = analysis

                return analysis

        # -----------------------------------------------------
        # Unknown goal
        # -----------------------------------------------------

        analysis = {
            "understood": True,
            "goal": goal,
            "type": "unknown_goal",
            "complexity": "unknown",
            "intent": intent,
            "reason": (
                "The existing command engine "
                "did not recognize this goal."
            )
        }

        self.last_analysis = analysis

        return analysis

    # =========================================================
    # DECIDE ROUTE
    # =========================================================

    def decide_route(
        self,
        analysis
    ):
        """
        Decide which execution route should be used.
        """

        if not isinstance(
            analysis,
            dict
        ):

            return {
                "route": "stop",
                "reason": "Invalid analysis."
            }

        if not analysis.get(
            "understood",
            False
        ):

            return {
                "route": "stop",
                "reason": analysis.get(
                    "reason",
                    "Goal not understood."
                )
            }

        goal_type = analysis.get(
            "type",
            "unknown"
        )

        # -----------------------------------------------------
        # Known command
        # -----------------------------------------------------

        if goal_type == "known_command":

            return {
                "route": "existing_tools",
                "reason": (
                    "Use existing IntentEngine "
                    "and ToolManager."
                )
            }

        # -----------------------------------------------------
        # Unknown goal
        # -----------------------------------------------------

        if goal_type == "unknown_goal":

            return {
                "route": "reasoning",
                "reason": (
                    "Goal requires autonomous "
                    "reasoning/capability selection."
                )
            }

        return {
            "route": "stop",
            "reason": (
                "No execution route available."
            )
        }

    # =========================================================
    # CREATE PLAN
    # =========================================================

    def create_plan(
        self,
        analysis,
        route
    ):
        """
        Create an execution plan.

        Current version creates a safe plan description.

        It does NOT execute arbitrary generated code.
        """

        if not isinstance(
            analysis,
            dict
        ):

            self.last_plan = []

            return []

        if not isinstance(
            route,
            dict
        ):

            self.last_plan = []

            return []

        route_name = route.get(
            "route",
            "stop"
        )

        goal = analysis.get(
            "goal",
            ""
        )

        # -----------------------------------------------------
        # Existing command
        # -----------------------------------------------------

        if route_name == "existing_tools":

            plan = [
                {
                    "step": 1,
                    "type": "execute_existing_intent",
                    "goal": goal,
                    "intent": analysis.get(
                        "intent"
                    )
                }
            ]

            self.last_plan = plan

            return plan

        # -----------------------------------------------------
        # Autonomous reasoning
        # -----------------------------------------------------

        if route_name == "reasoning":

            plan = [
                {
                    "step": 1,
                    "type": "analyze_capabilities",
                    "goal": goal
                },
                {
                    "step": 2,
                    "type": "select_capability",
                    "goal": goal
                },
                {
                    "step": 3,
                    "type": "execute_capability",
                    "goal": goal
                },
                {
                    "step": 4,
                    "type": "verify_result",
                    "goal": goal
                }
            ]

            self.last_plan = plan

            return plan

        self.last_plan = []

        return []

    # =========================================================
    # REASON
    # =========================================================

    def reason(
        self,
        goal,
        intent=None
    ):
        """
        Complete reasoning pipeline.

        Returns:

            analysis
            route
            plan
        """

        analysis = self.analyze_goal(
            goal,
            intent
        )

        route = self.decide_route(
            analysis
        )

        plan = self.create_plan(
            analysis,
            route
        )

        return {
            "analysis": analysis,
            "route": route,
            "plan": plan
        }

    # =========================================================
    # GET LAST PLAN
    # =========================================================

    def get_last_plan(self):

        return list(
            self.last_plan
        )

    # =========================================================
    # RESET
    # =========================================================

    def reset(self):

        self.last_goal = ""

        self.last_analysis = None

        self.last_plan = []
