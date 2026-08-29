"""
Project : Vyom AI
Version : 0.3
Module  : Reasoning Engine

Purpose:
    Hybrid reasoning layer.

    Priority:

        1. Existing IntentEngine
        2. Deep AI Reasoner
        3. Capability Manager
        4. Missing Capability

IMPORTANT:

    Existing ToolManager behaviour is preserved.

    The AI model decides what the goal means.
    ToolManager remains responsible for actual execution.
"""

from ai_core.capability_manager import CapabilityManager
from ai_core.deep_reasoner import DeepReasoner


class ReasoningEngine:

    def __init__(
        self,
        capability_manager=None,
        deep_reasoner=None
    ):

        self.capability_manager = (
            capability_manager
            if capability_manager is not None
            else CapabilityManager()
        )

        self.deep_reasoner = (
            deep_reasoner
            if deep_reasoner is not None
            else DeepReasoner()
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
    # CAPABILITY LIST
    # =========================================================

    def _capabilities(self):

        return self.capability_manager.list_capabilities(
            enabled_only=True
        )

    # =========================================================
    # SIMPLE FALLBACK ANALYSIS
    # =========================================================

    def _fallback_analysis(
        self,
        goal,
        intent=None
    ):

        capabilities = (
            self.capability_manager.match(
                goal
            )
        )

        return {
            "understood": True,
            "goal": goal,
            "type": (
                "known_command"
                if isinstance(
                    intent,
                    dict
                )
                and
                intent.get(
                    "intent"
                ) not in (
                    None,
                    "",
                    "unknown"
                )
                else "unknown_goal"
            ),
            "complexity": "simple",
            "intent": intent,
            "capabilities": capabilities,
            "reason": (
                "Fallback reasoning was used."
            )
        }

    # =========================================================
    # ANALYZE
    # =========================================================

    def analyze_goal(
        self,
        goal,
        intent=None,
        context=None,
        previous_result=None
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
        # Existing command
        #
        # Preserve the fast path.
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
        # Deep AI reasoning
        # -----------------------------------------------------

        capabilities = (
            self._capabilities()
        )

        self.last_capabilities = capabilities

        if self.deep_reasoner.is_available():

            ai_result = (
                self.deep_reasoner.reason(
                    goal=goal,
                    context=context,
                    capabilities=capabilities,
                    previous_result=previous_result
                )
            )

            if (
                isinstance(
                    ai_result,
                    dict
                )
                and
                ai_result.get(
                    "success",
                    False
                )
            ):

                data = ai_result.get(
                    "data",
                    {}
                )

                if isinstance(
                    data,
                    dict
                ):

                    data.setdefault(
                        "goal",
                        goal
                    )

                    data.setdefault(
                        "intent",
                        intent
                    )

                    data.setdefault(
                        "capabilities",
                        capabilities
                    )

                    self.last_analysis = data

                    return data

        # -----------------------------------------------------
        # Safe fallback
        # -----------------------------------------------------

        analysis = self._fallback_analysis(
            goal,
            intent
        )

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

        # -----------------------------------------------------
        # AI can explicitly select a route.
        # -----------------------------------------------------

        requested_route = str(
            analysis.get(
                "route",
                ""
            )
        ).strip().lower()

        valid_routes = {
            "existing_tools",
            "capability",
            "missing_capability",
            "conversation"
        }

        if requested_route in valid_routes:

            route = {
                "route": requested_route,
                "reason": analysis.get(
                    "reason",
                    "AI reasoning selected this route."
                )
            }

            if analysis.get(
                "capability"
            ):

                route["capability"] = (
                    analysis.get(
                        "capability"
                    )
                )

            return route

        # -----------------------------------------------------
        # Existing command
        # -----------------------------------------------------

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

        # -----------------------------------------------------
        # Capability fallback
        # -----------------------------------------------------

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
                "No executable capability "
                "is currently available."
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

        goal = analysis.get(
            "goal",
            ""
        )

        route_name = route.get(
            "route",
            "stop"
        )

        # -----------------------------------------------------
        # Existing tool
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
        # AI-generated dynamic plan
        # -----------------------------------------------------

        ai_plan = analysis.get(
            "plan"
        )

        if (
            isinstance(
                ai_plan,
                list
            )
            and
            ai_plan
        ):

            normalized_plan = []

            for index, step in enumerate(
                ai_plan,
                start=1
            ):

                if not isinstance(
                    step,
                    dict
                ):

                    continue

                item = dict(
                    step
                )

                item.setdefault(
                    "step",
                    index
                )

                item.setdefault(
                    "goal",
                    goal
                )

                normalized_plan.append(
                    item
                )

            if normalized_plan:

                self.last_plan = (
                    normalized_plan
                )

                return normalized_plan

        # -----------------------------------------------------
        # Capability
        # -----------------------------------------------------

        if route_name == "capability":

            plan = [
                {
                    "step": 1,
                    "type": "use_capability",
                    "goal": goal,
                    "capability": route.get(
                        "capability"
                    )
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
        intent=None,
        context=None,
        previous_result=None
    ):

        analysis = self.analyze_goal(
            goal,
            intent,
            context=context,
            previous_result=previous_result
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

        try:

            self.deep_reasoner.reset()

        except Exception:

            pass
