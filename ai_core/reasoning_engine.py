"""
Project : Vyom AI
Version : 1.0
Module  : Reasoning Engine

Purpose:
    Context-aware goal reasoning for Vyom.

Architecture:

    Goal
      |
      v
    Goal Analysis
      |
      +--> Existing Intent
      |
      +--> Known Capability
      |
      +--> Compound Goal
      |
      +--> Missing Capability
      |
      v
    Route Decision
      |
      v
    Structured Mission Plan

IMPORTANT:
    - Never executes computer actions.
    - Never executes generated code.
    - ToolManager remains the executor.
"""

from typing import Any, Dict, List, Optional

from ai_core.goal_compiler import GoalCompiler
from ai_core.capability_manager import CapabilityManager


class ReasoningEngine:

    def __init__(
        self,
        capability_manager=None,
        goal_compiler=None
    ):
        self.capability_manager = (
            capability_manager
            if capability_manager is not None
            else CapabilityManager()
        )

        self.goal_compiler = (
            goal_compiler
            if goal_compiler is not None
            else GoalCompiler()
        )

        self.last_goal = ""
        self.last_analysis: Optional[Dict[str, Any]] = None
        self.last_plan: List[Dict[str, Any]] = []
        self.last_route: Dict[str, Any] = {}

    # =========================================================
    # NORMALIZE
    # =========================================================

    def _normalize(self, value: Any) -> str:
        return str(value or "").strip()

    # =========================================================
    # ANALYZE GOAL
    # =========================================================

    def analyze_goal(
        self,
        goal: str,
        intent: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
        previous_result: Any = None
    ) -> Dict[str, Any]:

        goal = self._normalize(goal)

        self.last_goal = goal

        if not goal:
            result = {
                "understood": False,
                "goal": "",
                "objective": "",
                "type": "empty",
                "complexity": "none",
                "intent": intent,
                "suggested_intents": [],
                "sub_goals": [],
                "requires_new_capability": False,
                "reason": "Empty goal."
            }

            self.last_analysis = result
            return result

        ctx = (
            context
            if isinstance(context, dict)
            else {}
        )

        # -----------------------------------------------------
        # GOAL COMPILATION
        # -----------------------------------------------------

        try:
            compiled = self.goal_compiler.compile(
                goal=goal,
                intent=intent,
                context=ctx
            )
        except Exception as error:
            compiled = {
                "success": False,
                "understood": False,
                "goal": goal,
                "objective": goal,
                "complexity": "unknown",
                "suggested_intents": [],
                "sub_goals": [],
                "requires_new_capability": True,
                "reason": str(error)
            }

        suggested_intents = compiled.get(
            "suggested_intents",
            []
        )

        sub_goals = compiled.get(
            "sub_goals",
            []
        )

        # -----------------------------------------------------
        # CAPABILITY DISCOVERY
        # -----------------------------------------------------

        capabilities = []

        if not suggested_intents:
            try:
                capabilities = (
                    self.capability_manager.match(
                        goal
                    )
                )
            except Exception:
                capabilities = []

        # -----------------------------------------------------
        # CLASSIFY
        # -----------------------------------------------------

        if suggested_intents:
            if len(suggested_intents) == 1:
                goal_type = "known_action"
                complexity = (
                    compiled.get(
                        "complexity",
                        "simple"
                    )
                )
            else:
                goal_type = "compound_goal"
                complexity = "medium"

        elif capabilities:
            goal_type = "capability_goal"
            complexity = "complex"

        else:
            goal_type = "unknown_goal"
            complexity = "unknown"

        analysis = {
            "understood": True,
            "goal": goal,
            "objective": compiled.get(
                "objective",
                goal
            ),
            "type": goal_type,
            "complexity": complexity,
            "intent": intent,
            "suggested_intents": suggested_intents,
            "sub_goals": sub_goals,
            "capabilities": capabilities,
            "requires_new_capability": (
                not bool(suggested_intents)
                and not bool(capabilities)
            ),
            "context": ctx,
            "previous_result": previous_result,
            "compiled_goal": compiled
        }

        self.last_analysis = analysis

        return analysis

    # =========================================================
    # ROUTE DECISION
    # =========================================================

    def decide_route(
        self,
        analysis: Dict[str, Any]
    ) -> Dict[str, Any]:

        if not isinstance(
            analysis,
            dict
        ):
            route = {
                "route": "stop",
                "reason": "Invalid analysis."
            }

            self.last_route = route
            return route

        if not analysis.get(
            "understood",
            False
        ):
            route = {
                "route": "stop",
                "reason": "Goal could not be understood."
            }

            self.last_route = route
            return route

        suggested = analysis.get(
            "suggested_intents",
            []
        )

        capabilities = analysis.get(
            "capabilities",
            []
        )

        # -----------------------------------------------------
        # SINGLE KNOWN ACTION
        # -----------------------------------------------------

        if (
            isinstance(suggested, list)
            and len(suggested) == 1
        ):
            route = {
                "route": "existing_tools",
                "reason": (
                    "A directly executable "
                    "intent is available."
                )
            }

            self.last_route = route
            return route

        # -----------------------------------------------------
        # COMPOUND MISSION
        # -----------------------------------------------------

        if (
            isinstance(suggested, list)
            and len(suggested) > 1
        ):
            route = {
                "route": "mission",
                "reason": (
                    "The goal contains multiple "
                    "executable stages."
                )
            }

            self.last_route = route
            return route

        # -----------------------------------------------------
        # KNOWN CAPABILITY
        # -----------------------------------------------------

        if capabilities:
            route = {
                "route": "capability",
                "reason": (
                    "A capability can potentially "
                    "satisfy the goal."
                ),
                "capability": capabilities[0]
            }

            self.last_route = route
            return route

        # -----------------------------------------------------
        # NEW CAPABILITY
        # -----------------------------------------------------

        route = {
            "route": "missing_capability",
            "reason": (
                "No existing executable intent "
                "or enabled capability matches "
                "the goal."
            )
        }

        self.last_route = route
        return route

    # =========================================================
    # CREATE PLAN
    # =========================================================

    def create_plan(
        self,
        analysis: Dict[str, Any],
        route: Dict[str, Any]
    ) -> List[Dict[str, Any]]:

        if not isinstance(
            analysis,
            dict
        ):
            self.last_plan = []
            return []

        route_name = (
            route.get(
                "route",
                "stop"
            )
            if isinstance(route, dict)
            else "stop"
        )

        goal = analysis.get(
            "goal",
            ""
        )

        suggested = analysis.get(
            "suggested_intents",
            []
        )

        # -----------------------------------------------------
        # SINGLE ACTION
        # -----------------------------------------------------

        if route_name == "existing_tools":

            if (
                isinstance(suggested, list)
                and suggested
            ):
                intent = suggested[0]

                plan = [{
                    "step": 1,
                    "id": "action_1",
                    "type": "execute_existing_intent",
                    "goal": goal,
                    "intent": {
                        "intent": intent.get(
                            "intent"
                        ),
                        "target": intent.get(
                            "target"
                        )
                    },
                    "depends_on": [],
                    "status": "pending"
                }]

                self.last_plan = plan
                return plan

        # -----------------------------------------------------
        # COMPOUND MISSION
        # -----------------------------------------------------

        if route_name == "mission":

            plan = []

            for index, intent in enumerate(
                suggested,
                start=1
            ):

                if not isinstance(
                    intent,
                    dict
                ):
                    continue

                name = self._normalize(
                    intent.get("intent")
                )

                target = self._normalize(
                    intent.get("target")
                )

                if not name or not target:
                    continue

                depends_on = []

                if index > 1:
                    depends_on.append(
                        f"action_{index - 1}"
                    )

                plan.append({
                    "step": index,
                    "id": f"action_{index}",
                    "type": "execute_existing_intent",
                    "goal": goal,
                    "intent": {
                        "intent": name,
                        "target": target
                    },
                    "depends_on": depends_on,
                    "status": "pending"
                })

            self.last_plan = plan
            return plan

        # -----------------------------------------------------
        # CAPABILITY
        # -----------------------------------------------------

        if route_name == "capability":

            plan = [{
                "step": 1,
                "id": "capability_1",
                "type": "use_capability",
                "goal": goal,
                "capability": route.get(
                    "capability"
                ),
                "depends_on": [],
                "status": "pending"
            }]

            self.last_plan = plan
            return plan

        # -----------------------------------------------------
        # MISSING CAPABILITY
        # -----------------------------------------------------

        if route_name == "missing_capability":

            plan = [{
                "step": 1,
                "id": "capability_request_1",
                "type": "request_new_capability",
                "goal": goal,
                "depends_on": [],
                "status": "pending"
            }]

            self.last_plan = plan
            return plan

        self.last_plan = []

        return []

    # =========================================================
    # MAIN REASON
    # =========================================================

    def reason(
        self,
        goal: str,
        intent: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
        previous_result: Any = None
    ) -> Dict[str, Any]:

        analysis = self.analyze_goal(
            goal=goal,
            intent=intent,
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
            "success": True,
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
        self.last_route = {}
