"""
Project : Vyom AI
Version : 1.1
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
      +--> Deep Reasoning (when configured)
      +--> Known Capability
      +--> Compound Goal
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
    - DeepReasoner is advisory/decision support only.
    - Existing deterministic intent behaviour remains the fast path.
"""

from typing import Any, Dict, List, Optional

from ai_core.goal_compiler import GoalCompiler
from ai_core.capability_manager import CapabilityManager
from ai_core.deep_reasoner import DeepReasoner


class ReasoningEngine:

    SAFE_EXECUTABLE_INTENTS = {
        "open",
        "open_file",
        "search_file",
        "search_and_open_file",
        "close_app",
    }

    def __init__(
        self,
        capability_manager=None,
        goal_compiler=None,
        deep_reasoner=None
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

        self.deep_reasoner = (
            deep_reasoner
            if deep_reasoner is not None
            else DeepReasoner(
                goal_compiler=self.goal_compiler
            )
        )

        self.last_goal = ""
        self.last_analysis: Optional[Dict[str, Any]] = None
        self.last_plan: List[Dict[str, Any]] = []
        self.last_route: Dict[str, Any] = {}
        self.last_deep_reasoning: Optional[Dict[str, Any]] = None

    # =========================================================
    # NORMALIZE
    # =========================================================

    def _normalize(self, value: Any) -> str:
        return str(value or "").strip()

    # =========================================================
    # DEEP PLAN EXTRACTION
    # =========================================================

    def _extract_deep_intents(
        self,
        data: Any
    ) -> List[Dict[str, str]]:
        if not isinstance(data, dict):
            return []

        raw_plan = data.get("plan", [])
        if not isinstance(raw_plan, list):
            return []

        intents: List[Dict[str, str]] = []

        for item in raw_plan:
            if not isinstance(item, dict):
                continue

            raw_intent = item.get("intent")
            if not isinstance(raw_intent, dict):
                continue

            name = self._normalize(
                raw_intent.get("intent")
            ).lower()
            target = self._normalize(
                raw_intent.get("target")
            )

            # Only convert plans that the current ToolManager can
            # execute through an existing, known intent contract.
            if (
                name in self.SAFE_EXECUTABLE_INTENTS
                and target
            ):
                intents.append({
                    "intent": name,
                    "target": target,
                    "source": "deep_reasoner"
                })

        return intents

    # =========================================================
    # DEEP REASONING
    # =========================================================

    def _apply_deep_reasoning(
        self,
        goal: str,
        intent: Optional[Dict[str, Any]],
        context: Dict[str, Any],
        capabilities: List[Any],
        previous_result: Any,
        compiled: Dict[str, Any],
        suggested_intents: List[Dict[str, Any]],
        sub_goals: List[Any]
    ) -> Dict[str, Any]:
        """
        Ask DeepReasoner for additional planning only when a
        configured model is actually available.

        Deterministic GoalCompiler output always remains the source
        of truth for simple known actions. Model output is accepted
        only when it maps to an existing safe executable intent.
        """
        self.last_deep_reasoning = None

        try:
            if not self.deep_reasoner.is_available():
                return {
                    "suggested_intents": suggested_intents,
                    "sub_goals": sub_goals,
                    "route_hint": None,
                    "data": None,
                }
        except Exception:
            return {
                "suggested_intents": suggested_intents,
                "sub_goals": sub_goals,
                "route_hint": None,
                "data": None,
            }

        # Do not send trivial deterministic commands through the
        # remote model. This preserves the existing fast path.
        if (
            len(suggested_intents) == 1
            and not sub_goals
            and previous_result is None
        ):
            return {
                "suggested_intents": suggested_intents,
                "sub_goals": sub_goals,
                "route_hint": None,
                "data": None,
            }

        try:
            deep_result = self.deep_reasoner.reason(
                goal=goal,
                context=context,
                capabilities=capabilities,
                previous_result=previous_result,
                intent=intent,
            )
        except Exception as error:
            self.last_deep_reasoning = {
                "success": False,
                "error": str(error),
            }
            return {
                "suggested_intents": suggested_intents,
                "sub_goals": sub_goals,
                "route_hint": None,
                "data": None,
            }

        if not isinstance(deep_result, dict):
            return {
                "suggested_intents": suggested_intents,
                "sub_goals": sub_goals,
                "route_hint": None,
                "data": None,
            }

        self.last_deep_reasoning = deep_result

        if not deep_result.get("success", False):
            return {
                "suggested_intents": suggested_intents,
                "sub_goals": sub_goals,
                "route_hint": None,
                "data": None,
            }

        data = deep_result.get("data")
        if not isinstance(data, dict):
            return {
                "suggested_intents": suggested_intents,
                "sub_goals": sub_goals,
                "route_hint": None,
                "data": None,
            }

        deep_intents = self._extract_deep_intents(data)

        route_hint = self._normalize(
            data.get("route")
        ).lower()

        # Model-generated executable intents replace compiler intents
        # only for non-trivial goals. They are still restricted to the
        # known ToolManager contract above.
        if deep_intents:
            return {
                "suggested_intents": deep_intents,
                "sub_goals": sub_goals,
                "route_hint": route_hint,
                "data": data,
            }

        return {
            "suggested_intents": suggested_intents,
            "sub_goals": sub_goals,
            "route_hint": route_hint,
            "data": data,
        }

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

        ctx = context if isinstance(context, dict) else {}

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
        if not isinstance(suggested_intents, list):
            suggested_intents = []

        sub_goals = compiled.get(
            "sub_goals",
            []
        )
        if not isinstance(sub_goals, list):
            sub_goals = []

        # -----------------------------------------------------
        # CAPABILITY DISCOVERY
        # -----------------------------------------------------
        capabilities = []

        if not suggested_intents:
            try:
                capabilities = self.capability_manager.match(goal)
            except Exception:
                capabilities = []

        # -----------------------------------------------------
        # DEEP REASONER HANDOFF
        # -----------------------------------------------------
        deep = self._apply_deep_reasoning(
            goal=goal,
            intent=intent,
            context=ctx,
            capabilities=capabilities,
            previous_result=previous_result,
            compiled=compiled,
            suggested_intents=suggested_intents,
            sub_goals=sub_goals,
        )

        suggested_intents = deep.get(
            "suggested_intents",
            suggested_intents
        )
        sub_goals = deep.get(
            "sub_goals",
            sub_goals
        )
        deep_data = deep.get("data")
        deep_route = deep.get("route_hint")

        # -----------------------------------------------------
        # CLASSIFY
        # -----------------------------------------------------
        if suggested_intents:
            if len(suggested_intents) == 1:
                goal_type = "known_action"
                complexity = compiled.get(
                    "complexity",
                    "simple"
                )
            else:
                goal_type = "compound_goal"
                complexity = "medium"
        elif deep_route == "conversation":
            goal_type = "conversation_goal"
            complexity = "simple"
        elif capabilities:
            goal_type = "capability_goal"
            complexity = "complex"
        else:
            goal_type = "unknown_goal"
            complexity = "unknown"

        objective = compiled.get(
            "objective",
            goal
        )
        reason = compiled.get(
            "reason",
            ""
        )
        language = None

        if isinstance(deep_data, dict):
            objective = deep_data.get(
                "goal",
                objective
            ) or objective
            reason = deep_data.get(
                "reason",
                reason
            ) or reason
            language = deep_data.get("language")

            deep_complexity = self._normalize(
                deep_data.get("complexity")
            ).lower()
            if deep_complexity in (
                "simple",
                "medium",
                "complex"
            ) and goal_type != "known_action":
                complexity = deep_complexity

        analysis = {
            "understood": True,
            "goal": goal,
            "objective": objective,
            "type": goal_type,
            "complexity": complexity,
            "intent": intent,
            "suggested_intents": suggested_intents,
            "sub_goals": sub_goals,
            "capabilities": capabilities,
            "requires_new_capability": (
                not bool(suggested_intents)
                and not bool(capabilities)
                and deep_route not in ("conversation",)
            ),
            "context": ctx,
            "previous_result": previous_result,
            "compiled_goal": compiled,
            "deep_reasoning": deep_data,
            "deep_reasoning_source": (
                "model"
                if deep_data is not None
                else None
            ),
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

        if not isinstance(analysis, dict):
            route = {
                "route": "stop",
                "reason": "Invalid analysis."
            }
            self.last_route = route
            return route

        if not analysis.get("understood", False):
            route = {
                "route": "stop",
                "reason": "Goal could not be understood."
            }
            self.last_route = route
            return route

        suggested = analysis.get("suggested_intents", [])
        capabilities = analysis.get("capabilities", [])
        deep = analysis.get("deep_reasoning")

        if isinstance(suggested, list) and len(suggested) == 1:
            route = {
                "route": "existing_tools",
                "reason": "A directly executable intent is available."
            }
            self.last_route = route
            return route

        if isinstance(suggested, list) and len(suggested) > 1:
            route = {
                "route": "mission",
                "reason": "The goal contains multiple executable stages."
            }
            self.last_route = route
            return route

        if isinstance(deep, dict) and deep.get("route") == "conversation":
            route = {
                "route": "conversation",
                "reason": deep.get(
                    "reason",
                    "The task requires conversation."
                )
            }
            self.last_route = route
            return route

        if capabilities:
            route = {
                "route": "capability",
                "reason": "A capability can potentially satisfy the goal.",
                "capability": capabilities[0]
            }
            self.last_route = route
            return route

        route = {
            "route": "missing_capability",
            "reason": (
                "No existing executable intent or enabled capability "
                "matches the goal."
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

        if not isinstance(analysis, dict):
            self.last_plan = []
            return []

        route_name = (
            route.get("route", "stop")
            if isinstance(route, dict)
            else "stop"
        )

        goal = analysis.get("goal", "")
        suggested = analysis.get("suggested_intents", [])

        if route_name == "existing_tools":
            if isinstance(suggested, list) and suggested:
                intent = suggested[0]
                plan = [{
                    "step": 1,
                    "id": "action_1",
                    "type": "execute_existing_intent",
                    "goal": goal,
                    "intent": {
                        "intent": intent.get("intent"),
                        "target": intent.get("target")
                    },
                    "depends_on": [],
                    "status": "pending"
                }]
                self.last_plan = plan
                return plan

        if route_name == "mission":
            plan = []
            for index, intent in enumerate(suggested, start=1):
                if not isinstance(intent, dict):
                    continue

                name = self._normalize(intent.get("intent"))
                target = self._normalize(intent.get("target"))
                if not name or not target:
                    continue

                depends_on = []
                if index > 1:
                    depends_on.append(f"action_{index - 1}")

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

        if route_name == "capability":
            plan = [{
                "step": 1,
                "id": "capability_1",
                "type": "use_capability",
                "goal": goal,
                "capability": route.get("capability"),
                "depends_on": [],
                "status": "pending"
            }]
            self.last_plan = plan
            return plan

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

        route = self.decide_route(analysis)
        plan = self.create_plan(analysis, route)

        # Keep the executable plan visible to MissionPlanner. This
        # makes MissionPlanner the normalization boundary before
        # MissionRuntime, while retaining ReasoningEngine as the
        # decision layer.
        analysis["plan"] = plan

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
        self.last_deep_reasoning = None

        try:
            self.deep_reasoner.reset()
        except Exception:
            pass
