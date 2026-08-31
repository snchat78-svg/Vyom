"""
Project : Vyom AI
Version : 1.1
Module  : Mission Planner

Purpose:
    Convert reasoning output into a dependency-aware mission.

This module DOES NOT execute actions.
"""

from typing import Any, Dict, List, Optional


class MissionPlanner:

    def __init__(
        self,
        max_steps: int = 10
    ):
        self.max_steps = max(
            1,
            int(max_steps)
        )

        self.last_plan: List[
            Dict[str, Any]
        ] = []

    # =========================================================
    # NORMALIZE INTENT
    # =========================================================

    def _normalize_intent(
        self,
        value: Any
    ) -> Optional[Dict[str, str]]:

        if not isinstance(
            value,
            dict
        ):
            return None

        name = str(
            value.get(
                "intent"
            ) or ""
        ).strip()

        target = str(
            value.get(
                "target"
            ) or ""
        ).strip()

        if not name or not target:
            return None

        return {
            "intent": name,
            "target": target
        }

    # =========================================================
    # NORMALIZE STEP
    # =========================================================

    def _normalize_step(
        self,
        raw: Dict[str, Any],
        index: int,
        goal: str,
        previous_id: Optional[str]
    ) -> Optional[Dict[str, Any]]:

        if not isinstance(
            raw,
            dict
        ):
            return None

        step_type = str(
            raw.get(
                "type"
            ) or "execute_existing_intent"
        ).strip()

        step_id = str(
            raw.get(
                "id"
            ) or f"action_{index}"
        ).strip()

        item: Dict[str, Any] = {
            "step": index,
            "id": step_id,
            "type": step_type,
            "goal": goal,
            "status": "pending",
            "depends_on": []
        }

        # -----------------------------------------------------
        # DEPENDENCY
        # -----------------------------------------------------

        depends = raw.get(
            "depends_on"
        )

        if isinstance(
            depends,
            list
        ):
            item["depends_on"] = [
                str(x)
                for x in depends
                if str(x).strip()
            ]

        elif previous_id:
            item["depends_on"] = [
                previous_id
            ]

        # -----------------------------------------------------
        # INTENT
        # -----------------------------------------------------

        intent = self._normalize_intent(
            raw.get(
                "intent"
            )
        )

        if intent is not None:
            item["intent"] = intent

        # -----------------------------------------------------
        # CAPABILITY
        # -----------------------------------------------------

        if "capability" in raw:
            item["capability"] = (
                raw.get(
                    "capability"
                )
            )

        # -----------------------------------------------------
        # VALIDATION
        # -----------------------------------------------------

        if (
            step_type
            == "execute_existing_intent"
            and "intent" not in item
        ):
            return None

        return item

    # =========================================================
    # PLAN
    # =========================================================

    def plan(
        self,
        goal: str,
        analysis: Optional[Dict[str, Any]] = None,
        compiled_goal: Optional[Dict[str, Any]] = None,
        route: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:

        analysis = (
            analysis
            if isinstance(
                analysis,
                dict
            )
            else {}
        )

        compiled_goal = (
            compiled_goal
            if isinstance(
                compiled_goal,
                dict
            )
            else {}
        )

        route = (
            route
            if isinstance(
                route,
                dict
            )
            else {}
        )

        plan: List[
            Dict[str, Any]
        ] = []

        previous_id = None

        # -----------------------------------------------------
        # 1. USE REASONING PLAN
        # -----------------------------------------------------

        reasoning_plan = analysis.get(
            "plan"
        )

        if isinstance(
            reasoning_plan,
            list
        ):

            for raw in reasoning_plan:

                if len(plan) >= self.max_steps:
                    break

                normalized = self._normalize_step(
                    raw,
                    len(plan) + 1,
                    goal,
                    previous_id
                )

                if normalized:
                    plan.append(
                        normalized
                    )

                    previous_id = normalized[
                        "id"
                    ]

        # -----------------------------------------------------
        # 2. FALLBACK TO COMPILED INTENTS
        # -----------------------------------------------------

        if not plan:

            intents = (
                compiled_goal.get(
                    "suggested_intents",
                    []
                )
            )

            if isinstance(
                intents,
                list
            ):

                for intent in intents:

                    if len(plan) >= self.max_steps:
                        break

                    normalized_intent = (
                        self._normalize_intent(
                            intent
                        )
                    )

                    if not normalized_intent:
                        continue

                    step_id = (
                        f"action_{len(plan) + 1}"
                    )

                    item = {
                        "step": len(plan) + 1,
                        "id": step_id,
                        "type": (
                            "execute_existing_intent"
                        ),
                        "goal": goal,
                        "intent": normalized_intent,
                        "depends_on": (
                            [previous_id]
                            if previous_id
                            else []
                        ),
                        "status": "pending"
                    }

                    plan.append(item)

                    previous_id = step_id

        # -----------------------------------------------------
        # 3. CAPABILITY FALLBACK
        # -----------------------------------------------------

        if not plan:

            route_name = str(
                route.get(
                    "route"
                ) or ""
            ).strip()

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

            elif route_name == "missing_capability":

                plan = [{
                    "step": 1,
                    "id": (
                        "capability_request_1"
                    ),
                    "type": (
                        "request_new_capability"
                    ),
                    "goal": goal,
                    "depends_on": [],
                    "status": "pending"
                }]

        self.last_plan = plan

        return plan

    # =========================================================
    # RESET
    # =========================================================

    def reset(self):

        self.last_plan = []
