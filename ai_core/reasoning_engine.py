"""
Project : Vyom AI
Version : 0.2
Module  : Reasoning Engine

Purpose:
    Goal understanding + route selection + capability
    discovery.

IMPORTANT:
    This version does not generate or execute arbitrary code.
"""

from ai_core.capability_manager import CapabilityManager


class ReasoningEngine:

    # =========================================================
    # INITIALIZATION
    # =========================================================

    def __init__(
        self,
        capability_manager=None
    ):

        self.capability_manager = (
            capability_manager
            if capability_manager is not None
            else CapabilityManager()
        )

        self.last_goal = ""

        self.last_analysis = None

        self.last_plan = []

        self.last_capabilities = []

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
    # ANALYZE
    # =========================================================

    def analyze_goal(
        self,
        goal,
        intent=None
    ):

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
        # Existing known intent
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

        capabilities = (
            self.capability_manager.match(
                goal
            )
        )

        self.last_capabilities = capabilities

        analysis = {
            "understood": True,
            "goal": goal,
            "type": "unknown_goal",
            "complexity": "unknown",
            "intent": intent,
            "capabilities": capabilities,
            "reason": (
                "Existing command engine did not "
                "recognize this goal."
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

        if analysis.get(
            "type"
        ) == "known_command":

            return {
                "route": "existing_tools",
                "reason": (
                    "Existing ToolManager "
                    "can execute this command."
                )
            }

        capabilities = analysis.get(
            "capabilities",
            []
        )

        if capabilities:

            return {
                "route": "capability",
                "reason": (
                    "A matching capability "
                    "was found."
                ),
                "capability": capabilities[0]
            }

        return {
            "route": "missing_capability",
            "reason": (
                "No enabled capability "
                "matches this goal."
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

        if not isinstance(
            analysis,
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
        # Existing tools
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
        # Capability found
        # -----------------------------------------------------

        if route_name == "capability":

            capability = route.get(
                "capability"
            )

            plan = [
                {
                    "step": 1,
                    "type": "use_capability",
                    "goal": goal,
                    "capability": capability
                }
            ]

            self.last_plan = plan

            return plan

        # -----------------------------------------------------
        # Missing capability
        # -----------------------------------------------------

        if route_name == "missing_capability":

            plan = [
                {
                    "step": 1,
                    "type": "request_new_capability",
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
    # RESET
    # =========================================================

    def reset(self):

        self.last_goal = ""

        self.last_analysis = None

        self.last_plan = []

        self.last_capabilities = []
