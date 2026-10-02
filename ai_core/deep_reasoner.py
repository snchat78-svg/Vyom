"""
Project : Vyom AI
Version : 1.0
Module  : Deep Reasoner

Purpose:
    Hybrid local/cloud reasoning layer.

Priority:
    1. Configured AI model through the validated AI Reasoning Gateway.
    2. Lightweight local goal reasoning when no model is configured.

The local path is intentionally dependency-free so Vyom can work on
low-resource Windows machines without requiring a paid API.

This module never executes computer actions.
"""

from typing import Any, Dict, Optional

from ai_core.reasoning_gateway import AIReasoningGateway
from ai_core.model_gateway import ModelGateway
from ai_core.goal_compiler import GoalCompiler
from ai_core.logger import log


class DeepReasoner:

    def __init__(
        self,
        model_gateway: Optional[ModelGateway] = None,
        goal_compiler: Optional[GoalCompiler] = None,
        reasoning_gateway: Optional[AIReasoningGateway] = None,
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
        self.reasoning_gateway = (
            reasoning_gateway
            if reasoning_gateway is not None
            else AIReasoningGateway(self.model_gateway)
        )
        self.last_result = None

    @staticmethod
    def _looks_like_information_question(goal: str) -> bool:
        value = " ".join(str(goal or "").strip().lower().split())
        if not value:
            return False

        if "?" in value:
            return True

        # Language structure only: this does not encode facts, commands, or
        # application aliases. It separates a natural question from a task
        # that should enter the capability planner.
        question_markers = (
            "what", "who", "why", "when", "where", "how", "which",
            "kya", "kaun", "kyu", "kyun", "kab", "kahan", "kaise",
            "kitna", "kitni", "kitne",
        )
        pattern = r"\\b(?:" + "|".join(
            __import__("re").escape(item)
            for item in question_markers
        ) + r")\\b"

        return bool(
            __import__("re").search(
                r"^(?:what|who|why|when|where|how|which|is|are|can|could|would|kya|kaun|kyu(?:n)?|kab|kahan|kaise|kitna|kitni|kitne)\\b",
                value,
            )
            or __import__("re").search(
                r"^(?:tum|aap)\\b.*\\b(?:kya|kaise|kaun|kyu(?:n)?|kab|kahan|kitna|kitni|kitne)\\b",
                value,
            )
            or __import__("re").search(
                pattern + r"\\s*(?:hai|hain|tha|thi|the|hoga|hogi|honge)?$",
                value,
            )
        )

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
        elif self._looks_like_information_question(goal):
            route = "conversation"
            plan = [{
                "step": 1,
                "type": "conversation",
                "description": (
                    "Answer the user's natural-language question from the "
                    "configured conversational knowledge provider when available."
                ),
                "capability": None,
                "intent": None,
            }]
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
        # A configured real model always enters through the validated gateway.
        model_available = False
        try:
            model_available = bool(self.reasoning_gateway.is_available())
        except Exception:
            model_available = False

        log("[AI] DEEP REASONER: model_available=%s" % model_available)

        if model_available:
            result = self.reasoning_gateway.reason(
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
                log("[AI] DEEP REASONER SOURCE: model")
                return result

            # If the real model is configured but its response fails validation,
            # do not execute an unvalidated model decision. Fall back to the
            # existing deterministic local reasoner.

        log("[AI] DEEP REASONER SOURCE: local_reasoner")
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
        return self.reasoning_gateway.is_available()

    def reset(self):
        self.last_result = None
        try:
            self.reasoning_gateway.reset()
        except Exception:
            pass
        try:
            self.goal_compiler.last_compilation = None
        except Exception:
            pass
