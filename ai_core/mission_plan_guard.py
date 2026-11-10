"""Structural safety checks for dependency-aware mission plans.

This module validates data only. It does not whitelist operation names and
never executes a mission step.
"""
from typing import Any, Dict, List, Optional


class MissionPlanGuard:
    @staticmethod
    def validate(plan: Any, max_steps: int) -> Optional[str]:
        if not isinstance(plan, list):
            return "Mission plan must be a list."
        if not plan:
            return "Mission plan is empty."
        limit = max(1, int(max_steps))
        if len(plan) > limit:
            return f"Mission plan exceeds the {limit}-step safety limit."

        ids = set()
        dependencies: Dict[str, List[str]] = {}
        for index, step in enumerate(plan, start=1):
            if not isinstance(step, dict):
                return f"Mission step {index} is not an object."
            step_id = str(step.get("id") or "").strip()
            if not step_id:
                return f"Mission step {index} has no id."
            if step_id in ids:
                return f"Mission plan has duplicate step id '{step_id}'."
            ids.add(step_id)

            raw_dependencies = step.get("depends_on", [])
            if not isinstance(raw_dependencies, list):
                return f"Mission step {index} has an invalid dependency list."
            normalized = []
            seen = set()
            for raw_dependency in raw_dependencies:
                dependency = str(raw_dependency or "").strip()
                if not dependency:
                    return f"Mission step {index} has an empty dependency."
                if dependency == step_id:
                    return f"Mission step {index} cannot depend on itself."
                if dependency in seen:
                    return f"Mission step {index} repeats dependency '{dependency}'."
                seen.add(dependency)
                normalized.append(dependency)
            dependencies[step_id] = normalized

        for index, items in enumerate(dependencies.values(), start=1):
            for dependency in items:
                if dependency not in ids:
                    return f"Mission step {index} depends on unknown id '{dependency}'."

        visiting = set()
        visited = set()

        def visit(node: str, trail: List[str]) -> Optional[str]:
            if node in visiting:
                try:
                    start = trail.index(node)
                except ValueError:
                    start = 0
                return "Mission dependency cycle: " + " -> ".join(trail[start:] + [node])
            if node in visited:
                return None
            visiting.add(node)
            for dependency in dependencies.get(node, []):
                error = visit(dependency, trail + [node])
                if error:
                    return error
            visiting.remove(node)
            visited.add(node)
            return None

        for step_id in ids:
            error = visit(step_id, [])
            if error:
                return error
        return None


__all__ = ["MissionPlanGuard"]
