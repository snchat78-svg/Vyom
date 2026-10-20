"""M2: structured meaning and intent hypotheses for Vyom.

This layer is deliberately downstream of the existing semantic compiler.
It describes the interpreted intent, entities, user payload, constraints,
references and desired result; it does not execute actions or invent aliases.
When runtime evidence contains competing target matches, the caller must ask
for clarification before dispatching a plan.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Mapping, Optional


class MeaningIntentEngine:
    """Create a provider-independent semantic frame from existing plan data."""

    _REFERENCE_PATTERN = re.compile(
        r"(?<!\w)(?:"
        r"in\s+(?:it|this|that)|there|here|"
        r"uske\s+andar|iske\s+andar|"
        r"isme(?:in|n|)?|usme(?:in|n|)?|"
        r"ye\s+wala|yeh\s+wala|woh\s+wala|wo\s+wala|"
        r"same\s+(?:file|window|one)|the\s+same\s+(?:file|window|one)|"
        r"इसमें|उसमें|इसके\s+अंदर|उसके\s+अंदर|यहाँ|वहाँ|"
        r"यह\s+वाला|वही|वो\s+वाला|वह\s+वाला"
        r")(?!\w)",
        flags=re.IGNORECASE,
    )

    _ENTITY_ACTIONS = {
        "open_application", "open_file", "close_application", "open",
        "close_app", "search_file", "search_and_open_file",
    }
    _PAYLOAD_KEYS = ("text", "query", "value")
    _PLACEHOLDER_TARGETS = {
        "", "focused_element", "active_window", "current_window",
        "current_app", "current_target", "selection",
    }

    @staticmethod
    def _text(value: Any, limit: int = 500) -> str:
        return str(value or "").strip()[:limit]

    @classmethod
    def _append_unique(cls, target: List[Any], value: Any) -> None:
        if value is None or value == "":
            return
        if value not in target:
            target.append(value)

    @classmethod
    def _step_operation(cls, step: Mapping[str, Any]) -> str:
        if str(step.get("type") or "").lower() == "execute_existing_intent":
            intent = step.get("intent")
            if isinstance(intent, Mapping):
                return cls._text(intent.get("intent"), 100)
        return cls._text(step.get("action") or step.get("operation"), 100)

    @classmethod
    def _step_target(cls, step: Mapping[str, Any], operation: str) -> str:
        if str(step.get("type") or "").lower() == "execute_existing_intent":
            intent = step.get("intent")
            target = intent.get("target") if isinstance(intent, Mapping) else ""
        else:
            target = step.get("target")
        value = cls._text(target, 300)
        # Targets are meaningful for generic UI actions too (for example,
        # click "Save" or focus a named control). Only contextual placeholders
        # are omitted; action type must not erase an explicitly grounded target.
        if value.casefold() in cls._PLACEHOLDER_TARGETS:
            return ""
        return value

    @classmethod
    def _extract_steps(cls, plan: Any) -> List[Mapping[str, Any]]:
        if not isinstance(plan, list):
            return []
        return [step for step in plan if isinstance(step, Mapping)]

    @classmethod
    def _references(cls, text: str) -> List[str]:
        found: List[str] = []
        for match in cls._REFERENCE_PATTERN.finditer(text or ""):
            cls._append_unique(found, cls._text(match.group(0), 80))
        return found[:12]

    def analyze(
        self,
        raw_text: Any,
        result: Mapping[str, Any],
        context: Optional[Mapping[str, Any]] = None,
        recovery: Optional[Mapping[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Build a stable frame and alternatives without modifying user data."""
        raw = self._text(raw_text, 2000)
        route = self._text(result.get("route"), 80).lower()
        recovery_data = recovery if isinstance(recovery, Mapping) else {}
        ambiguities = recovery_data.get("ambiguities")
        ambiguities = ambiguities if isinstance(ambiguities, list) else []
        steps = self._extract_steps(result.get("plan"))

        operations: List[str] = []
        targets: List[str] = []
        payloads: List[Dict[str, Any]] = []
        preconditions: List[str] = []
        postconditions: List[str] = []
        verification_checks: List[Dict[str, Any]] = []

        for index, step in enumerate(steps, start=1):
            operation = self._step_operation(step)
            if operation:
                self._append_unique(operations, operation)
            target = self._step_target(step, operation)
            if target:
                self._append_unique(targets, target)

            args = step.get("args")
            if not isinstance(args, Mapping):
                args = {}
            for key in self._PAYLOAD_KEYS:
                value = args.get(key)
                if isinstance(value, (str, int, float)) and str(value).strip():
                    entry = {"kind": key, "value": self._text(value), "step": index}
                    if entry not in payloads:
                        payloads.append(entry)

            for field, destination in (
                ("preconditions", preconditions),
                ("postconditions", postconditions),
            ):
                values = step.get(field)
                if isinstance(values, str):
                    values = [values]
                if isinstance(values, (list, tuple)):
                    for value in values[:20]:
                        if isinstance(value, str):
                            self._append_unique(destination, self._text(value, 300))

            metadata = step.get("metadata")
            verification = metadata.get("verification") if isinstance(metadata, Mapping) else None
            checks = verification.get("checks") if isinstance(verification, Mapping) else None
            if isinstance(checks, list):
                for check in checks[:20]:
                    if isinstance(check, Mapping):
                        safe_check = {
                            str(key): value
                            for key, value in check.items()
                            if key in {"kind", "source", "field", "operator", "value"}
                            and isinstance(value, (str, int, float, bool, type(None)))
                        }
                        if safe_check and safe_check not in verification_checks:
                            verification_checks.append(safe_check)

        target_alternatives: List[Dict[str, Any]] = []
        ambiguity_operations: List[str] = []
        for ambiguity in ambiguities[:5]:
            if not isinstance(ambiguity, Mapping):
                continue
            operation = self._text(ambiguity.get("operation"), 100)
            if operation:
                self._append_unique(ambiguity_operations, operation)
            candidates = ambiguity.get("candidates")
            if isinstance(candidates, list):
                for candidate in candidates[:3]:
                    if not isinstance(candidate, Mapping):
                        continue
                    value = self._text(candidate.get("value"), 300)
                    if value:
                        try:
                            candidate_confidence = max(0.0, min(1.0, float(candidate.get("confidence", 0.0) or 0.0)))
                        except (TypeError, ValueError):
                            candidate_confidence = 0.0
                        target_alternatives.append({
                            "target": value,
                            "confidence": round(candidate_confidence, 4),
                            "status": "alternative",
                        })
        for operation in ambiguity_operations:
            self._append_unique(operations, operation)

        # When the action addresses a focused input rather than naming an
        # app in its own action schema, retain the observed context target.
        # Do this only when the plan did not already name an explicit entity.
        ctx = context if isinstance(context, Mapping) else {}
        if steps and not targets and not target_alternatives:
            for key in ("current_target", "current_app", "current_file"):
                value = ctx.get(key)
                if isinstance(value, Mapping):
                    value = value.get("title") or value.get("name") or value.get("path")
                value = self._text(value, 300)
                if value:
                    self._append_unique(targets, value)
            ui = ctx.get("ui")
            active = ui.get("active_window") if isinstance(ui, Mapping) else None
            if not targets and isinstance(active, Mapping):
                value = self._text(active.get("title") or active.get("name"), 300)
                if value:
                    self._append_unique(targets, value)

        references = self._references(raw)
        try:
            confidence = max(0.0, min(1.0, float(result.get("confidence", 0.0))))
        except (TypeError, ValueError):
            confidence = 0.0

        requires_clarification = bool(ambiguities) or route == "clarification"
        if requires_clarification:
            task_kind = "clarification"
            desired_result = "Resolve ambiguity before dispatching any action."
        elif route == "conversation":
            task_kind = "answer_question"
            desired_result = "Answer the user's question using available, supportable knowledge."
        elif steps:
            task_kind = "computer_action"
            desired_result = (
                "Complete the interpreted plan and satisfy its verification checks."
                if verification_checks
                else "Complete the interpreted task and verify observable postconditions."
            )
        elif route == "escalate":
            task_kind = "reasoning_request"
            desired_result = "Resolve the request with semantic reasoning before any unvalidated action."
        else:
            task_kind = "unresolved"
            desired_result = "Clarify missing information before acting."

        hypotheses: List[Dict[str, Any]] = []
        if target_alternatives:
            for alternative in target_alternatives:
                hypotheses.append({
                    "task_kind": "computer_action",
                    "operations": list(operations),
                    "target": alternative["target"],
                    "confidence": alternative["confidence"],
                    "status": "competing_target",
                })
        elif operations or task_kind == "answer_question":
            hypotheses.append({
                "task_kind": task_kind,
                "operations": list(operations),
                "targets": list(targets),
                "confidence": round(confidence, 4),
                "status": "selected" if not requires_clarification else "unresolved",
            })

        return {
            "schema_version": "m2.1",
            "intent": {
                "kind": task_kind,
                "operations": operations[:20],
                "confidence": round(confidence, 4),
            },
            "entities": {
                "targets": targets[:20] if not target_alternatives else [],
                "target_candidates": target_alternatives,
            },
            "payloads": payloads[:30],
            "constraints": {
                "preconditions": preconditions[:30],
                "postconditions": postconditions[:30],
                "verification_checks": verification_checks[:30],
            },
            "references": references,
            "desired_result": desired_result,
            "hypotheses": hypotheses[:10],
            "requires_clarification": requires_clarification,
        }


__all__ = ["MeaningIntentEngine"]
