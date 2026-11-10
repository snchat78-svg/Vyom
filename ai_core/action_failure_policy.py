"""Classify failed actions before choosing a safe recovery path.

The policy is intentionally conservative: repeating is allowed only when a
known stage proves that the action was rejected before dispatch. Unknown or
post-dispatch outcomes stop the mission rather than duplicating side effects.
"""
from __future__ import annotations

from typing import Any, Dict, List


class ActionFailurePolicy:
    """Return a small serializable recovery decision for one failed step."""

    PRE_DISPATCH_RETRY_STAGES = frozenset({
        "observation_failed_before_action",
        "ui_observation_unavailable_before_action",
        "ui_target_changed_before_action",
        "ui_target_context_mismatch",
        "ui_target_window_mismatch",
        "ui_target_unavailable_before_action",
        "ui_element_not_found",
        "ui_element_unavailable",
    })

    CLARIFICATION_STAGES = frozenset({
        "ui_target_ambiguous",
        "ui_target_missing",
        "ui_target_identity_unverified",
    })

    UNSUPPORTED_STAGES = frozenset({
        "ui_pattern_unsupported",
        "unsupported_action",
        "unsupported_operation",
        "capability_runtime_missing",
        "capability_not_implemented",
    })

    UNCERTAIN_STAGES = frozenset({
        "verification_failed",
        "post_action_observation_failed",
        "post_action_observation_unavailable",
        "no_postcondition",
        "state_failed",
        "windows_ui_error",
    })

    @staticmethod
    def _nodes(result: Any) -> List[Dict[str, Any]]:
        nodes: List[Dict[str, Any]] = []
        pending = [result]
        seen = set()
        while pending and len(nodes) < 8:
            item = pending.pop(0)
            if not isinstance(item, dict) or id(item) in seen:
                continue
            seen.add(id(item))
            nodes.append(item)
            for key in ("result", "execution_result"):
                child = item.get(key)
                if isinstance(child, dict):
                    pending.append(child)
        return nodes

    @classmethod
    def classify(cls, result: Any, step: Any = None) -> Dict[str, Any]:
        """Classify an unsuccessful step; never trust stage names as success."""
        nodes = cls._nodes(result)
        stages = [
            str(node.get("stage") or "").strip().lower()
            for node in nodes
            if node.get("stage")
        ]
        verifications = [
            node.get("verification")
            for node in nodes
            if isinstance(node.get("verification"), dict)
        ]
        verification_levels = [
            str(item.get("verification_level") or "").strip().lower()
            for item in verifications
        ]
        detail = next((
            str(node.get("message") or node.get("error") or "").strip()
            for node in nodes
            if node.get("message") or node.get("error")
        ), "")

        common = {
            "schema_version": "m5.5",
            "stages": stages[:5],
            "retry_same_action": False,
            "stop_mission": True,
            "requires_user_input": False,
            "reobserve_before_retry": True,
        }

        if any(stage in cls.CLARIFICATION_STAGES for stage in stages):
            return {
                **common,
                "category": "target_ambiguous",
                "response_stage": "clarification_required",
                "user_message": (
                    detail
                    or "I could not uniquely identify the UI target. Please specify the intended control or window."
                ),
                "requires_user_input": True,
                "reobserve_before_retry": False,
            }

        if any(stage in cls.UNSUPPORTED_STAGES for stage in stages):
            return {
                **common,
                "category": "unsupported_operation",
                "response_stage": "capability_unavailable",
                "user_message": (
                    detail
                    or "This UI operation is not supported by the selected control; no repeated action was sent."
                ),
                "reobserve_before_retry": False,
            }

        # A post-dispatch verification failure takes precedence over any
        # incidental nested stage because the action may already have happened.
        uncertain = any(stage in cls.UNCERTAIN_STAGES for stage in stages)
        uncertain = uncertain or any(
            level.startswith("post_action_observation")
            or level in {"state_failed", "no_postcondition", "dispatch_fallback_no_observer"}
            for level in verification_levels
        )
        uncertain = uncertain or any(stage == "verification_failed" for stage in stages)
        if uncertain or any(node.get("success") is True for node in nodes):
            reason = next((
                str(item.get("reason") or "").strip()
                for item in verifications
                if item.get("reason")
            ), detail)
            message = (
                "The action may have taken effect, but its result could not be verified. "
                "I stopped without repeating it. Check the current window and confirm whether to continue."
            )
            if reason:
                message = (
                    "The action may have taken effect, but verification failed: "
                    f"{reason} I stopped without repeating it. Check the current window and confirm whether to continue."
                )
            return {
                **common,
                "category": "outcome_uncertain",
                "response_stage": "outcome_unverified",
                "user_message": message,
                "reobserve_before_retry": False,
            }

        if any(stage in cls.PRE_DISPATCH_RETRY_STAGES for stage in stages):
            return {
                **common,
                "category": "pre_dispatch_failure",
                "response_stage": "retry_after_observation",
                "user_message": (
                    detail
                    or "The action was rejected before dispatch. A bounded retry after fresh observation is safe."
                ),
                "retry_same_action": True,
                "stop_mission": False,
                "reobserve_before_retry": True,
            }

        return {
            **common,
            "category": "unknown_outcome",
            "response_stage": "outcome_unverified",
            "user_message": (
                "Vyom could not determine whether the action took effect. "
                "To avoid duplicating a possible side effect, it stopped. Check the current window and confirm how to proceed."
            ),
            "reobserve_before_retry": False,
        }


__all__ = ["ActionFailurePolicy"]
