"""
Project : Vyom AI
Version : 1.0
Module  : Deep Reasoner

Purpose:
    Hybrid local/cloud reasoning layer.

Priority:
    1. Configured AI model through ModelGateway.
    2. Lightweight local goal reasoning when no model is configured.

The local path is intentionally dependency-free so Vyom can work on
low-resource Windows machines without requiring a paid API.

This module never executes computer actions.
"""

from typing import Any, Dict, Optional

from ai_core.model_gateway import ModelGateway
from ai_core.goal_compiler import GoalCompiler


class DeepReasoner:

    def __init__(
        self,
        model_gateway: Optional[ModelGateway] = None,
        goal_compiler: Optional[GoalCompiler] = None
    ):
        self.model_gateway = (
            model_gateway
            if model_gateway is not None
            else ModelGateway()
        )
        self.goal_compiler = (
            goal_compiler
            if goal_compiler is not None
            else GoalCompiler()
        )
        self.last_result = None

    def _local_reason(
        self,
        goal: str,
        context: Optional[Dict[str, Any]] = None,
        capabilities=None,
        previous_result=None,
        intent=None,
    ) -> Dict[str, Any]:
        compiled = self.goal_compiler.compile(
            goal=goal,
            intent=intent,
            context=context,
        )
        intents = compiled.get("suggested_intents", [])

        if intents:
            route = "existing_tools"
            plan = []
            for index, item in enumerate(intents, start=1):
                plan.append({
                    "step": index,
                    "type": "execute_existing_intent",
                    "description": f"Execute the required action for: {item.get('target', '')}",
                    "capability": (
                        "application_control"
                        if item.get("intent") == "open"
                        else "process_control"
                        if item.get("intent") == "close_app"
                        else "file_search"
                        if item.get("intent") == "search_file"
                        else "file_open"
                    ),
                    "intent": item,
                })
        else:
            route = "missing_capability"
            plan = [{
                "step": 1,
                "type": "request_new_capability",
                "description": (
                    "Analyze and prepare the missing capability; "
                    "do not execute arbitrary generated code."
                ),
                "capability": None,
                "intent": None,
            }]

        return {
            "success": True,
            "available": False,
            "source": "local_reasoner",
            "data": {
                "understood": True,
                "goal": goal,
                "objective": compiled.get("objective", goal),
                "language": "hindi"
                if any("\u0900" <= ch <= "\u097F" for ch in goal)
                else "english",
                "complexity": compiled.get("complexity", "simple"),
                "analysis": compiled.get("reason", ""),
                "route": route,
                "capability": "",
                "plan": plan,
                "needs_confirmation": False,
                "reason": compiled.get("reason", ""),
                "goal_compilation": compiled,
            },
        }

    def reason(
        self,
        goal: str,
        context: Optional[Dict[str, Any]] = None,
        capabilities=None,
        previous_result=None,
        intent=None,
    ):
        # If a model is configured, keep the existing gateway path.
        if self.model_gateway.is_available():
            result = self.model_gateway.complete(
                goal=goal,
                context=context,
                capabilities=capabilities,
                previous_result=previous_result,
            )
            if (
                isinstance(result, dict)
                and result.get("success", False)
            ):
                self.last_result = result
                return result

        result = self._local_reason(
            goal=goal,
            context=context,
            capabilities=capabilities,
            previous_result=previous_result,
            intent=intent,
        )
        self.last_result = result
        return result

    def is_available(self):
        # "Available" means a real model endpoint is configured.
        return self.model_gateway.is_available()

    def reset(self):
        self.last_result = None
        try:
            self.goal_compiler.last_compilation = None
        except Exception:
            pass
