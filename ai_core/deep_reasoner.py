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

import os
from typing import Any, Dict, Optional

from ai_core.reasoning_gateway import AIReasoningGateway
from ai_core.model_gateway import ModelGateway
from ai_core.goal_compiler import GoalCompiler
from ai_core.context_action_compiler import ContextActionCompiler
from ai_core.logger import log
from ai_core.semantic_brain import LocalSemanticBrain


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
        self.semantic_brain = LocalSemanticBrain(
            context_action_compiler=ContextActionCompiler(self.goal_compiler)
        )
        self.allow_remote_reasoning = bool(
            str(
                os.getenv("VYOM_REMOTE_REASONING", "false")
            ).strip().lower()
            in {"1", "true", "yes", "on"}
        )
        self.last_result = None

    @staticmethod
    def _looks_like_information_question(goal: str) -> bool:
        value = " ".join(str(goal or "").strip().lower().split())
        if not value:
            return False

        # This classifier only identifies interrogative language structure.
        # It does not contain factual answers, application aliases, or a
        # command dictionary. The actual answer remains open-ended.
        if "?" in value:
            return True

        tokens = value.replace("-", " ").split()
        if not tokens:
            return False

        question_words = {
            "what", "who", "why", "when", "where", "how", "which",
            "kya", "kaun", "kyu", "kyun", "kab", "kahan", "kaise",
            "kitna", "kitni", "kitne", "kitane", "kitney",
        }

        if tokens[0] in question_words:
            return True

        if tokens[0] in {"tum", "aap", "you"} and any(
            token in question_words for token in tokens[1:]
        ):
            return True

        # Hindi/Hinglish and colloquial English often place the interrogative
        # before a copular/auxiliary ending:
        #   "... kya hai", "... kaise ho", "... what is"
        auxiliaries = {
            "is", "are", "am", "was", "were",
            "hai", "hain", "tha", "thi", "the",
            "hoga", "hogi", "honge", "ho",
        }
        if len(tokens) >= 2 and tokens[-1] in auxiliaries:
            if any(token in question_words for token in tokens[:-1]):
                return True

        return False

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

    def _local_semantic_result(
        self,
        goal: str,
        context: Optional[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """Return a safe executable semantic plan without contacting a model."""
        try:
            semantic = self.semantic_brain.reason(
                goal=goal,
                context=context,
            )
        except Exception as error:
            log(
                "[AI] LOCAL SEMANTIC BRAIN ERROR: %s"
                % str(error)[:240]
            )
            return None

        if not isinstance(semantic, dict):
            return None

        route = str(semantic.get("route") or "").strip().lower()
        plan = semantic.get("plan")
        plan = plan if isinstance(plan, list) else []

        # A locally understood execution/conversation decision is authoritative
        # enough to avoid an unnecessary remote model dependency. A safe
        # clarification is also local terminal state; it must not burn a model
        # request merely to rephrase the same question.
        terminal_route = route
        output_route = "conversation" if route == "clarification" else route
        if output_route in {"capability", "mission", "conversation"} and (
            bool(plan) or output_route == "conversation"
        ):
            data = {
                "understood": True,
                "goal": str(semantic.get("goal") or goal),
                "objective": str(semantic.get("goal") or goal),
                "language": "hinglish",
                "complexity": "simple" if len(plan) <= 1 else "medium",
                "analysis": "Local semantic interpretation.",
                "route": output_route,
                "semantic_route": terminal_route,
                "response": str(semantic.get("message") or "").strip(),
                "capability": "windows_ui" if any(
                    isinstance(step, dict) and step.get("type") == "action"
                    for step in plan
                ) else "",
                "semantic_interpretation": semantic.get(
                    "semantic_interpretation", []
                ),
                "confidence": semantic.get("confidence", 0.0),
                "plan": plan,
                "needs_confirmation": bool(
                    semantic.get("needs_confirmation", False)
                ),
                "reason": "Resolved by local semantic brain.",
                "source": "local_semantic_brain",
            }
            return {
                "success": True,
                "available": False,
                "source": "local_semantic_brain",
                "data": data,
            }

        return None

    def reason(
        self,
        goal: str,
        context: Optional[Dict[str, Any]] = None,
        capabilities=None,
        previous_result=None,
        intent=None,
    ):
        # Local semantic reasoning is the first-class mind for executable
        # computer tasks. A remote model is an escalation path, not a
        # prerequisite for understanding or executing ordinary commands.
        local_result = self._local_semantic_result(
            goal=goal,
            context=context,
        )
        if local_result is not None:
            self.last_result = local_result
            log("[AI] DEEP REASONER SOURCE: local_semantic_brain")
            return local_result

        # Remote model reasoning is deliberately opt-in. The default
        # production control plane is the local Vyom semantic brain, so
        # Gemini quota/network state cannot prevent computer command execution.
        if not self.allow_remote_reasoning:
            result = self._local_reason(
                goal=goal,
                context=context,
                capabilities=capabilities,
                previous_result=previous_result,
                intent=intent,
            )
            self.last_result = result
            log("[AI] DEEP REASONER SOURCE: local_reasoner")
            return result

        # A configured real model is consulted only when explicitly enabled.
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
            # do not execute an unvalidated model decision. Record a bounded
            # diagnostic so runtime logs show why the model path was abandoned.
            if isinstance(result, dict):
                stage = str(result.get("stage") or "model_request_failed")
                reason = str(result.get("error") or result.get("reason") or "").strip()[:240]
                log(
                    "[AI] DEEP REASONER MODEL FALLBACK: stage=%s reason=%s"
                    % (stage, reason)
                )

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
        # The reasoning layer is always available because the dependency-free
        # local semantic brain can interpret and plan supported computer tasks.
        # A hosted/local model is an optional escalation source, not a
        # prerequisite for semantic execution.
        return True

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
        try:
            self.semantic_brain.last_result = None
        except Exception:
            pass
