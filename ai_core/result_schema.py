"""Canonical result schema for Vyom execution and conversation boundaries.

All structured runtime results use the same core keys. Optional subsystem
metadata is preserved unchanged, so this module standardizes the contract
without removing existing result payloads or legacy execution paths.
"""

from typing import Any, Dict, Optional


STANDARD_RESULT_DEFAULTS = {
    "success": False,
    "status": "failed",
    "stage": "unknown",
    "message": "",
    "error": None,
    "error_category": None,
}


def normalize_result(
    result: Any,
    *,
    default_stage: str = "completed",
    status_hint: Optional[str] = None,
) -> Dict[str, Any]:
    """Return a serializable result with the canonical core fields."""

    if isinstance(result, dict):
        normalized = dict(result)
        success = bool(normalized.get("success", False))

        explicit_status = status_hint or normalized.get("status")
        if explicit_status:
            status = str(explicit_status).strip().lower()
        else:
            status = "success" if success else "failed"

        message = normalized.get("message", normalized.get("text", ""))
        if message is None:
            message = ""

        normalized.setdefault("success", success)
        normalized.setdefault("status", status)
        normalized.setdefault("stage", default_stage)
        normalized.setdefault("message", str(message))
        normalized.setdefault("error", None)
        normalized.setdefault("error_category", None)
        return normalized

    if result is None:
        return {
            **STANDARD_RESULT_DEFAULTS,
            "stage": "no_result",
            "message": "No response from executor.",
            "error": "Executor returned None.",
            "error_category": "no_result",
        }

    if isinstance(result, bool):
        return {
            **STANDARD_RESULT_DEFAULTS,
            "success": result,
            "status": "success" if result else "failed",
            "stage": default_stage,
            "message": "",
        }

    # Legacy executor paths may still return display text. Preserve that
    # behaviour and do not guess failure by inspecting human-readable text.
    return {
        **STANDARD_RESULT_DEFAULTS,
        "success": True,
        "status": "success",
        "stage": "legacy_completed",
        "message": str(result),
    }


__all__ = ["STANDARD_RESULT_DEFAULTS", "normalize_result"]
