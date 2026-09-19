"""
Project : Vyom AI
Version : 1.0
Module  : AI Reasoning Gateway

Purpose:
    Controlled boundary between Vyom's reasoning pipeline and a real AI model.

Flow:
    ReasoningEngine
        -> DeepReasoner
        -> AIReasoningGateway
        -> ModelGateway
        -> structured JSON
        -> schema validation

Safety:
    The model receives no executable tool object and no Windows executor.
    This gateway validates the model decision before it is returned upstream.
    It never executes actions.
"""

from typing import Any, Dict, List, Optional

from ai_core.model_gateway import ModelGateway


class AIReasoningGateway:
    """Validated reasoning-only gateway around the existing ModelGateway."""

    ALLOWED_LANGUAGES = {"hindi", "english", "hinglish"}
    ALLOWED_COMPLEXITIES = {"simple", "medium", "complex"}
    ALLOWED_ROUTES = {
        "existing_tools",
        "capability",
        "missing_capability",
        "conversation",
        "mission",
    }
    ALLOWED_INTENTS = {
        "open",
        "open_file",
        "search_file",
        "search_and_open_file",
        "close_app",
    }
    ALLOWED_STEP_TYPES = {
        "action",
        "execute_existing_intent",
        "use_capability",
        "request_new_capability",
        "conversation",
    }

    def __init__(self, model_gateway: Optional[ModelGateway] = None):
        self.model_gateway = model_gateway or ModelGateway()
        self.last_result: Optional[Dict[str, Any]] = None

    def is_available(self) -> bool:
        return self.model_gateway.is_available()

    def _capability_descriptions(self, capabilities: Any) -> List[Any]:
        if not isinstance(capabilities, list):
            return []
        # Do not pass executable Python objects/callables to the model.
        safe: List[Any] = []
        for item in capabilities:
            if isinstance(item, (str, int, float, bool)) or item is None:
                safe.append(item)
            elif isinstance(item, dict):
                safe.append({
                    str(k): v
                    for k, v in item.items()
                    if isinstance(v, (str, int, float, bool)) or v is None
                })
            else:
                safe.append(str(item))
        return safe

    def reason(
        self,
        goal: str,
        context: Optional[Dict[str, Any]] = None,
        capabilities: Optional[List[Any]] = None,
        previous_result: Any = None,
    ) -> Dict[str, Any]:
        result = self.model_gateway.complete(
            goal=goal,
            context=context if isinstance(context, dict) else {},
            capabilities=self._capability_descriptions(capabilities),
            previous_result=previous_result,
        )

        if not isinstance(result, dict) or not result.get("success", False):
            self.last_result = result if isinstance(result, dict) else {
                "success": False,
                "error": "Invalid gateway result.",
            }
            return self.last_result

        data = result.get("data")
        validation = self.validate(data)
        if not validation["valid"]:
            self.last_result = {
                "success": False,
                "available": True,
                "stage": "reasoning_validation_error",
                "error": validation["error"],
                "data": data,
            }
            return self.last_result

        self.last_result = {
            "success": True,
            "available": True,
            "source": "ai_reasoning_gateway",
            "data": validation["data"],
        }
        return self.last_result

    def validate(self, data: Any):
        if not isinstance(data, dict):
            return {"valid": False, "error": "Reasoning output must be a JSON object."}

        required = ("understood", "goal", "language", "complexity", "route", "plan")
        missing = [key for key in required if key not in data]
        if missing:
            return {"valid": False, "error": "Missing required fields: " + ", ".join(missing)}

        if not isinstance(data.get("understood"), bool):
            return {"valid": False, "error": "'understood' must be boolean."}

        if not isinstance(data.get("goal"), str) or not data.get("goal", "").strip():
            return {"valid": False, "error": "'goal' must be a non-empty string."}

        language = str(data.get("language", "")).strip().lower()
        if language not in self.ALLOWED_LANGUAGES:
            return {"valid": False, "error": "Unsupported reasoning language."}

        complexity = str(data.get("complexity", "")).strip().lower()
        if complexity not in self.ALLOWED_COMPLEXITIES:
            return {"valid": False, "error": "Unsupported reasoning complexity."}

        route = str(data.get("route", "")).strip().lower()
        if route not in self.ALLOWED_ROUTES:
            return {"valid": False, "error": "Unsupported reasoning route."}

        plan = data.get("plan")
        if not isinstance(plan, list):
            return {"valid": False, "error": "'plan' must be a list."}
        if len(plan) > 10:
            return {"valid": False, "error": "Reasoning plan exceeds the 10-step safety limit."}

        normalized_plan = []
        for index, raw in enumerate(plan, start=1):
            if not isinstance(raw, dict):
                return {"valid": False, "error": f"Plan step {index} must be an object."}

            step = dict(raw)
            step_type = str(step.get("type", "action")).strip().lower()
            if step_type not in self.ALLOWED_STEP_TYPES:
                return {"valid": False, "error": f"Unsupported plan step type at step {index}."}

            step["step"] = index

            intent = step.get("intent")
            if intent is not None:
                if not isinstance(intent, dict):
                    return {"valid": False, "error": f"Intent at step {index} must be an object."}
                name = str(intent.get("intent", "")).strip().lower()
                target = str(intent.get("target", "")).strip()
                if not name or not target:
                    return {"valid": False, "error": f"Intent at step {index} must contain intent and target."}
                if name not in self.ALLOWED_INTENTS:
                    return {"valid": False, "error": f"Unsupported executable intent at step {index}: {name}."}
                # The downstream ReasoningEngine applies the executable-intent allowlist.
                intent = dict(intent)
                intent["intent"] = name
                intent["target"] = target
                step["intent"] = intent

            if "capability" in step and step["capability"] is not None:
                capability = step["capability"]
                if not isinstance(capability, (str, dict)):
                    return {"valid": False, "error": f"Invalid capability value at step {index}."}

            normalized_plan.append(step)

        normalized = dict(data)
        normalized["language"] = language
        normalized["complexity"] = complexity
        normalized["route"] = route
        normalized["plan"] = normalized_plan
        normalized["needs_confirmation"] = bool(data.get("needs_confirmation", False))
        normalized["reason"] = str(data.get("reason", ""))
        normalized["analysis"] = str(data.get("analysis", ""))
        return {"valid": True, "data": normalized}

    def reset(self):
        self.last_result = None
