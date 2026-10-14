"""
Project : Vyom AI
Version : 1.2
Module  : Mission Planner

Purpose:
    Convert reasoning output into a dependency-aware mission.

This module DOES NOT execute actions.

Step 1 change:
    The planner now understands the generic Action Schema while preserving
    the existing execute_existing_intent format used by the current agent.
"""

from typing import Any, Dict, List, Optional

from ai_core.action_validator import ActionValidator


class MissionPlanner:

    def __init__(
        self,
        max_steps: int = 10
    ):
        self.max_steps = max(
            1,
            int(max_steps)
        )

        self.action_validator = ActionValidator(
            max_steps=self.max_steps
        )

        self.last_plan: List[
            Dict[str, Any]
        ] = []
        self.last_error = ""

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
    # NORMALIZE GENERIC ACTION
    # =========================================================

    def _normalize_action(
        self,
        value: Any,
        index: int
    ) -> Optional[Dict[str, Any]]:
        validation = self.action_validator.validate_action(
            value,
            index=index
        )

        if not validation.get(
            "valid",
            False
        ):
            return None

        action = dict(
            validation["action"]
        )
        action["step"] = index
        action["type"] = "action"
        return action

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

        # -----------------------------------------------------
        # Generic Action Schema
        # -----------------------------------------------------

        if step_type == "action":
            action = self._normalize_action(
                raw,
                index
            )

            if action is None:
                return None

            item: Dict[str, Any] = {
                "step": index,
                "id": str(
                    action.get(
                        "id"
                    ) or f"action_{index}"
                ).strip(),
                "type": "action",
                "goal": goal,
                "status": "pending",
                "depends_on": []
            }
            item.update(action)
            item["step"] = index
            item["type"] = "action"
            item["goal"] = goal
            item["status"] = "pending"

            depends = item.get(
                "depends_on",
                []
            )

            if isinstance(
                depends,
                list
            ) and depends:
                item["depends_on"] = [
                    str(x)
                    for x in depends
                    if str(x).strip()
                ]
            elif previous_id:
                item["depends_on"] = [
                    previous_id
                ]

            return item

        # -----------------------------------------------------
        # Existing legacy mission step
        # -----------------------------------------------------

        step_id = str(
            raw.get(
                "id"
            ) or f"action_{index}"
        ).strip()

        item = {
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


    def _validate_plan_graph(self, plan: List[Dict[str, Any]]) -> Optional[str]:
        """Validate the complete mixed legacy/generic plan before execution."""
        if len(plan) > self.max_steps:
            return f"Mission exceeds the {self.max_steps}-step safety limit."
        positions: Dict[str, int] = {}
        for index, step in enumerate(plan):
            step_id = str(step.get("id") or "").strip()
            if not step_id:
                return f"Mission step {index + 1} has no id."
            if step_id in positions:
                return f"Mission contains duplicate step id '{step_id}'."
            positions[step_id] = index
        graph_steps: List[Dict[str, Any]] = []
        for index, step in enumerate(plan, start=1):
            dependencies = step.get("depends_on", [])
            if not isinstance(dependencies, list):
                return f"Mission step {index} has an invalid dependency list."
            seen = set()
            for value in dependencies:
                dependency = str(value or "").strip()
                if not dependency:
                    return f"Mission step {index} contains an empty dependency."
                if dependency in seen:
                    return f"Mission step {index} repeats dependency '{dependency}'."
                seen.add(dependency)
                if dependency not in positions:
                    return f"Mission step {index} depends on unknown id '{dependency}'."
                if dependency == step.get("id"):
                    return f"Mission step {index} cannot depend on itself."
            graph_steps.append({"id": str(step.get("id")), "depends_on": [str(v) for v in dependencies]})
        cycle = self.action_validator._find_cycle(graph_steps)
        if cycle:
            return "Mission dependency cycle: " + " -> ".join(cycle)
        return None

    def _reject_plan(self, message: str) -> List[Dict[str, Any]]:
        """Fail closed: a malformed compound goal must never become partial work."""
        self.last_error = str(message or "Mission plan was rejected.")
        self.last_plan = []
        return []

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
        self.last_error = ""
        self.last_plan = []

        # -----------------------------------------------------
        # 1. USE REASONING PLAN
        # -----------------------------------------------------
        # Supplied plans are atomic: never drop or truncate an invalid step.
        # -----------------------------------------------------
        reasoning_plan = analysis.get("plan")
        if isinstance(reasoning_plan, list) and reasoning_plan:
            if len(reasoning_plan) > self.max_steps:
                return self._reject_plan(
                    f"Reasoning plan has {len(reasoning_plan)} steps; safety limit is {self.max_steps}."
                )
            for raw in reasoning_plan:
                normalized = self._normalize_step(raw, len(plan) + 1, goal, previous_id)
                if not normalized:
                    return self._reject_plan(
                        f"Reasoning plan step {len(plan) + 1} is invalid; refusing to execute a partial plan."
                    )
                plan.append(normalized)
                previous_id = normalized["id"]
            graph_error = self._validate_plan_graph(plan)
            if graph_error:
                return self._reject_plan(graph_error)

        # -----------------------------------------------------
        # 2. FALLBACK TO COMPILED INTENTS
        # -----------------------------------------------------
        if not plan:
            intents = compiled_goal.get("suggested_intents", [])
            if isinstance(intents, list) and intents:
                if len(intents) > self.max_steps:
                    return self._reject_plan(
                        f"Compiled goal has {len(intents)} steps; safety limit is {self.max_steps}."
                    )
                for intent in intents:
                    normalized_intent = self._normalize_intent(intent)
                    if not normalized_intent:
                        return self._reject_plan(
                            "Compiled goal contains an invalid intent; refusing to execute a partial plan."
                        )
                    step_id = f"action_{len(plan) + 1}"
                    plan.append({
                        "step": len(plan) + 1,
                        "id": step_id,
                        "type": "execute_existing_intent",
                        "goal": goal,
                        "intent": normalized_intent,
                        "depends_on": [previous_id] if previous_id else [],
                        "status": "pending",
                    })
                    previous_id = step_id

        # -----------------------------------------------------
        # 3. CAPABILITY FALLBACK
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

                # Preserve validated generic actions as real mission steps.
                # No action name is translated into a fixed legacy intent.
                generic_actions = analysis.get(
                    "generic_actions",
                    []
                )

                if isinstance(generic_actions, list) and generic_actions:
                    if len(generic_actions) > self.max_steps:
                        return self._reject_plan(
                            f"Generic plan has {len(generic_actions)} steps; safety limit is {self.max_steps}."
                        )
                    for raw_action in generic_actions:
                        action = self._normalize_action(raw_action, len(plan) + 1)
                        if not action:
                            return self._reject_plan(
                                f"Generic plan step {len(plan) + 1} is invalid; refusing to execute a partial plan."
                            )

                        action_id = str(
                            action.get("id")
                            or f"action_{len(plan) + 1}"
                        ).strip()

                        depends_on = action.get("depends_on", [])
                        if not isinstance(depends_on, list):
                            depends_on = []
                        depends_on = [
                            str(item)
                            for item in depends_on
                            if str(item).strip()
                        ]
                        if not depends_on and previous_id:
                            depends_on = [previous_id]

                        item = dict(action)
                        item.update({
                            "step": len(plan) + 1,
                            "id": action_id,
                            "type": "action",
                            "goal": goal,
                            "status": "pending",
                            "depends_on": depends_on,
                        })
                        plan.append(item)
                        previous_id = action_id

                # Preserve the legacy capability fallback when no concrete
                # generic actions were supplied.
                if not plan:
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

        graph_error = self._validate_plan_graph(plan) if plan else None
        if graph_error:
            return self._reject_plan(graph_error)
        self.last_plan = plan
        return plan

    # =========================================================
    # RESET
    # =========================================================

    def reset(self):

        self.last_plan = []
        self.last_error = ""
