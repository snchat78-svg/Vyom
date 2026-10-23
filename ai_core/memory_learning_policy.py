"""Policy for projecting consented memory into non-authoritative reasoning hints.

Only allow-listed presentation preferences are projected. Corrections, arbitrary
text, and workflow summaries remain review/export data and are not injected into
the execution planner. This module never changes a goal or creates a plan.
"""
from __future__ import annotations

from datetime import datetime, timezone
import math
import re
from typing import Any, Dict, List, Mapping, Optional

from ai_core.memory_consent import CONSENT_VERSION, SCHEMA_VERSION

MAX_SOURCE_RECORDS = 128
MAX_MEMORY_HINTS = 5
_SOURCE_REF = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,159}$")

# Only presentation preferences are allowed to cross into reasoning context.
# Arbitrary preference keys or free-form values are deliberately ignored.
_ALLOWED_VALUES = {
    "response_language": {
        "hi": "hindi",
        "hindi": "hindi",
        "english": "english",
        "en": "english",
        "hinglish": "hinglish",
        "roman hindi": "hinglish",
    },
    "response_style": {
        "concise": "concise",
        "brief": "concise",
        "step_by_step": "step_by_step",
        "step-by-step": "step_by_step",
        "detailed": "detailed",
    },
    "verbosity": {
        "brief": "brief",
        "normal": "normal",
        "detailed": "detailed",
    },
    "explanation_level": {
        "basic": "basic",
        "intermediate": "intermediate",
        "advanced": "advanced",
    },
    "answer_format": {
        "bullets": "bullets",
        "bullet points": "bullets",
        "paragraph": "paragraph",
        "table": "table",
    },
}
_KEY_ALIASES = {
    "language": "response_language",
    "preferred_language": "response_language",
    "style": "response_style",
    "format": "answer_format",
}


def _datetime(value: Any) -> Optional[datetime]:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except (TypeError, ValueError, OverflowError):
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def _scope_matches(record: Mapping[str, Any], context: Mapping[str, Any]) -> bool:
    scope = record.get("scope")
    value = record.get("value")
    if not isinstance(value, Mapping):
        return False
    if scope == "global":
        return True
    if scope == "application":
        expected = str(value.get("scope_hint") or "").strip().casefold()
        actual = str(context.get("current_app") or context.get("current_window") or "").strip().casefold()
        return bool(expected and actual and expected == actual)
    if scope == "workflow":
        expected = str(value.get("workflow_id") or "").strip()
        actual = str(context.get("current_workflow_id") or "").strip()
        return bool(expected and actual and expected == actual)
    return False


def _safe_preference(record: Any, context: Mapping[str, Any]) -> Optional[Dict[str, str]]:
    if not isinstance(record, Mapping):
        return None
    if record.get("schema_version") != SCHEMA_VERSION:
        return None
    if record.get("memory_type") != "preference" or record.get("lifecycle") != "active":
        return None

    approval = record.get("approval")
    if not isinstance(approval, Mapping):
        return None
    if (
        approval.get("status") != "approved"
        or approval.get("actor") != "user"
        or approval.get("consent_version") != CONSENT_VERSION
    ):
        return None

    provenance = record.get("provenance")
    if not isinstance(provenance, Mapping):
        return None
    source_ref = provenance.get("source_ref")
    if (
        provenance.get("kind") != "explicit_preference"
        or not isinstance(source_ref, str)
        or not _SOURCE_REF.fullmatch(source_ref)
    ):
        return None

    confidence = record.get("confidence")
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
        return None
    try:
        parsed_confidence = float(confidence)
    except (ValueError, TypeError, OverflowError):
        return None
    if not math.isfinite(parsed_confidence) or not 0.0 <= parsed_confidence <= 1.0:
        return None

    created = _datetime(record.get("created_at"))
    updated = _datetime(record.get("updated_at"))
    if created is None or updated is None or updated < created:
        return None
    expiry_raw = record.get("expires_at")
    if expiry_raw is not None:
        expiry = _datetime(expiry_raw)
        if expiry is None or expiry <= datetime.now(timezone.utc):
            return None

    if not _scope_matches(record, context):
        return None

    value = record.get("value")
    if not isinstance(value, Mapping) or set(value) - {"key", "value_text", "scope_hint"}:
        return None
    raw_key = str(value.get("key") or "").strip().casefold().replace("-", "_").replace(" ", "_")
    key = _KEY_ALIASES.get(raw_key, raw_key)
    allowed_values = _ALLOWED_VALUES.get(key)
    if allowed_values is None:
        return None
    raw_value = str(value.get("value_text") or "").strip().casefold()
    safe_value = allowed_values.get(raw_value)
    if safe_value is None:
        return None

    return {"key": key, "value": safe_value, "scope": str(record.get("scope"))}


def build_approved_memory_hints(
    records: Any,
    *,
    context: Optional[Mapping[str, Any]] = None,
) -> List[Dict[str, str]]:
    """Project only validated, in-scope presentation preferences as tiny hints."""
    if not isinstance(records, list):
        return []
    ctx = context if isinstance(context, Mapping) else {}
    selected: Dict[str, Dict[str, str]] = {}
    conflicted = set()

    for record in records[:MAX_SOURCE_RECORDS]:
        hint = _safe_preference(record, ctx)
        if hint is None:
            continue
        key = hint["key"]
        existing = selected.get(key)
        if existing is None:
            selected[key] = hint
        elif existing["value"] != hint["value"]:
            # Two approved but conflicting values are ambiguous: use neither.
            selected.pop(key, None)
            conflicted.add(key)
        elif key in conflicted:
            continue

    return [
        {
            "kind": "presentation_preference",
            "key": hint["key"],
            "value": hint["value"],
            "scope": hint["scope"],
            "authority": "advisory_only",
        }
        for key, hint in selected.items()
        if key not in conflicted
    ][:MAX_MEMORY_HINTS]


def attach_approved_memory_hints(
    context: Any,
    records: Any,
) -> Dict[str, Any]:
    """Return a copy of context with safe hints and a fixed non-authority contract."""
    safe_context = dict(context) if isinstance(context, Mapping) else {}
    # Do not trust injected context to self-assert memory-policy metadata.
    safe_context.pop("approved_memory_hints", None)
    safe_context.pop("memory_hint_contract", None)
    safe_context["approved_memory_hints"] = build_approved_memory_hints(
        records,
        context=safe_context,
    )
    safe_context["memory_hint_contract"] = {
        "mode": "advisory_only",
        "may_change_user_goal": False,
        "may_create_or_enable_capability": False,
        "may_bypass_clarification_or_confirmation": False,
        "may_claim_execution_success": False,
        "may_run_generated_code": False,
    }
    return safe_context
