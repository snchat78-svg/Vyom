"""
Project : Vyom AI
Version : 1.0
Module  : Mission Planner

Purpose:
    Turn a compiled goal/reasoning result into an executable mission
    plan while preserving ToolManager as the only computer executor.

Safety:
    - Never executes actions.
    - Never creates arbitrary executable code.
    - Unknown capabilities remain explicit.
"""

from typing import Any, Dict, List, Optional


class MissionPlanner:

    def __init__(self, max_steps: int = 10):
        self.max_steps = max(1, int(max_steps))
        self.last_plan: List[Dict[str, Any]] = []

    def _normalize_ai_step(
        self,
        step: Dict[str, Any],
        index: int,
        goal: str
    ) -> Optional[Dict[str, Any]]:
        if not isinstance(step, dict):
            return None

        item = dict(step)
        item["step"] = index
        item.setdefault("goal", goal)

        intent = item.get("intent")
        if isinstance(intent, dict):
            name = str(intent.get("intent") or "").strip()
            target = str(intent.get("target") or "").strip()
            if name and target:
                item["intent"] = {
                    "intent": name,
                    "target": target,
                }
                return item

        return item

    def plan(
        self,
        goal: str,
        analysis: Optional[Dict[str, Any]] = None,
        compiled_goal: Optional[Dict[str, Any]] = None,
        route: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        analysis = analysis if isinstance(analysis, dict) else {}
        compiled_goal = compiled_goal if isinstance(compiled_goal, dict) else {}
        route = route if isinstance(route, dict) else {}

        result: List[Dict[str, Any]] = []

        # Prefer explicit safe intents discovered by GoalCompiler.
        intents = compiled_goal.get("suggested_intents", [])
        if isinstance(intents, list) and intents:
            for index, intent in enumerate(intents[:self.max_steps], start=1):
                if isinstance(intent, dict):
                    name = str(intent.get("intent") or "").strip()
                    target = str(intent.get("target") or "").strip()
                    if name and target:
                        result.append({
                            "step": index,
                            "type": "execute_existing_intent",
                            "goal": goal,
                            "intent": {
                                "intent": name,
                                "target": target,
                            },
                        })
            if result:
                self.last_plan = result
                return result

        # Then trust a structured AI plan, but only normalize it.
        ai_plan = analysis.get("plan")
        if isinstance(ai_plan, list):
            for raw_index, step in enumerate(ai_plan, start=1):
                if len(result) >= self.max_steps:
                    break
                normalized = self._normalize_ai_step(step, raw_index, goal)
                if normalized is not None:
                    result.append(normalized)

        if result:
            self.last_plan = result
            return result

        route_name = str(route.get("route") or "").strip()

        if route_name == "missing_capability":
            result = [{
                "step": 1,
                "type": "request_new_capability",
                "goal": goal,
            }]
        elif route_name == "capability":
            result = [{
                "step": 1,
                "type": "use_capability",
                "goal": goal,
                "capability": route.get("capability"),
            }]

        self.last_plan = result
        return result

    def reset(self):
        self.last_plan = []
