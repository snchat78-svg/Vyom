"""
Project : Vyom AI
Version : 1.0
Module  : Action Validator

Purpose:
    Validate generic action plans before an action can enter the execution
    pipeline.

Safety:
    - Schema only; never executes anything.
    - Rejects executable Python/callable/tool-object data from model output.
    - Detects duplicate IDs and dependency cycles.
    - Does not maintain a fixed list of action/intent names.
"""

from typing import Any, Dict, List, Optional, Set

from ai_core.action_schema import ActionSchema, ActionSchemaError


class ActionValidator:

    # These keys are specifically disallowed in the reasoning protocol.
    # Capabilities may implement controlled operations later without asking
    # the reasoning model to return executable code.
    FORBIDDEN_EXECUTABLE_KEYS = {
        "code",
        "python",
        "python_code",
        "script",
        "source_code",
        "eval",
        "exec",
        "callable",
        "function",
        "tool_object",
    }

    def __init__(self, max_steps: int = 10):
        self.max_steps = max(1, int(max_steps))

    def validate_action(self, raw: Any, index: int = 1) -> Dict[str, Any]:
        if not isinstance(raw, dict):
            return {"valid": False, "error": f"Action step {index} must be an object."}

        forbidden = self._find_forbidden_keys(raw)
        if forbidden:
            return {
                "valid": False,
                "error": (
                    f"Action step {index} contains forbidden executable field(s): "
                    + ", ".join(sorted(forbidden))
                ),
            }

        try:
            action = ActionSchema.from_dict(raw, index=index)
        except (ActionSchemaError, TypeError, ValueError) as error:
            return {"valid": False, "error": f"Invalid action step {index}: {error}"}

        return {"valid": True, "action": action.to_dict()}

    def validate_plan(self, plan: Any) -> Dict[str, Any]:
        if not isinstance(plan, list):
            return {"valid": False, "error": "'plan' must be a list."}
        if len(plan) > self.max_steps:
            return {
                "valid": False,
                "error": f"Action plan exceeds the {self.max_steps}-step safety limit.",
            }

        normalized: List[Dict[str, Any]] = []
        ids: Set[str] = set()

        for index, raw in enumerate(plan, start=1):
            result = self.validate_action(raw, index=index)
            if not result["valid"]:
                return result

            item = result["action"]
            step_id = str(item.get("id") or "").strip()
            if not step_id:
                return {"valid": False, "error": f"Action step {index} has no id."}
            if step_id in ids:
                return {"valid": False, "error": f"Duplicate action id: {step_id}."}
            ids.add(step_id)
            item["step"] = index
            normalized.append(item)

        for index, item in enumerate(normalized, start=1):
            for dependency in item.get("depends_on", []):
                if dependency not in ids:
                    return {
                        "valid": False,
                        "error": f"Action step {index} depends on unknown id '{dependency}'.",
                    }
                if dependency == item.get("id"):
                    return {
                        "valid": False,
                        "error": f"Action step {index} cannot depend on itself.",
                    }

        cycle = self._find_cycle(normalized)
        if cycle:
            return {"valid": False, "error": "Action plan dependency cycle: " + " -> ".join(cycle)}

        return {"valid": True, "plan": normalized}

    def _find_forbidden_keys(self, raw: Dict[str, Any]) -> Set[str]:
        found: Set[str] = set()

        def walk(value: Any, path: str):
            if isinstance(value, dict):
                for key, child in value.items():
                    normalized = str(key).strip().lower()
                    child_path = f"{path}.{normalized}" if path else normalized
                    if normalized in self.FORBIDDEN_EXECUTABLE_KEYS:
                        found.add(child_path)
                    walk(child, child_path)
            elif isinstance(value, list):
                for index, child in enumerate(value):
                    walk(child, f"{path}[{index}]")

        walk(raw, "")
        return found

    def _find_cycle(self, plan: List[Dict[str, Any]]) -> Optional[List[str]]:
        graph = {
            str(step["id"]): [str(dep) for dep in step.get("depends_on", [])]
            for step in plan
        }
        visiting: Set[str] = set()
        visited: Set[str] = set()

        def visit(node: str, trail: List[str]) -> Optional[List[str]]:
            if node in visiting:
                try:
                    start = trail.index(node)
                except ValueError:
                    start = 0
                return trail[start:] + [node]
            if node in visited:
                return None

            visiting.add(node)
            for dependency in graph.get(node, []):
                found = visit(dependency, trail + [node])
                if found:
                    return found
            visiting.remove(node)
            visited.add(node)
            return None

        for node in graph:
            found = visit(node, [])
            if found:
                return found
        return None

