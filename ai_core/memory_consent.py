"""Explicit, default-off consent gate for future user-approved Vyom memory.

M9.2 stores consent and record approvals in process memory only. It does not
persist personal memories or write records to disk; that remains a later phase.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import math
import re
import uuid
from typing import Any, Dict, List, Optional


SCHEMA_VERSION = 1
CONSENT_VERSION = "vyom-memory-consent-v1"
MAX_PENDING = 32
MAX_APPROVED = 32

_TYPES = {"correction", "preference", "verified_workflow"}
_SCOPES = {"global", "application", "workflow"}
_TYPE_FIELDS = {
    "correction": {
        "surface_form": 256,
        "preferred_form": 256,
        "language": 32,
        "context_hint": 256,
    },
    "preference": {
        "key": 96,
        "value_text": 256,
        "scope_hint": 96,
    },
    "verified_workflow": {
        "workflow_id": 128,
        "display_name": 160,
        "verified_summary": 512,
    },
}
_REQUIRED_FIELDS = {
    "correction": {"surface_form", "preferred_form"},
    "preference": {"key", "value_text"},
    "verified_workflow": {"workflow_id", "display_name", "verified_summary"},
}
_PROVENANCE_KIND = {
    "correction": "explicit_correction",
    "preference": "explicit_preference",
    "verified_workflow": "verified_workflow",
}
_OPAQUE_REF = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,159}$")
_SENSITIVE_TEXT = re.compile(
    r"(?i)(?:password\s*[:=]|api[_ -]?key\s*[:=]|bearer\s+[A-Za-z0-9._-]{12,}|"
    r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|"
    r"AIza[0-9A-Za-z_-]{25,}|sk-[A-Za-z0-9]{16,})"
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: Optional[datetime] = None) -> str:
    current = value or _utc_now()
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    return current.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_datetime(value: Any) -> Optional[datetime]:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except (ValueError, OverflowError):
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


class MemoryConsentManager:
    """Session-only opt-in and per-record approval gate; defaults to OFF."""

    def __init__(self) -> None:
        self._enabled = False
        self._pending: Dict[str, Dict[str, Any]] = {}
        self._approved: Dict[str, Dict[str, Any]] = {}

    def status(self) -> Dict[str, Any]:
        return {
            "enabled": self._enabled,
            "mode": "session_only",
            "consent_version": CONSENT_VERSION,
            "persistent_memory_storage": "local_versioned_storage_available_after_approval",
            "pending_count": len(self._pending),
            "approved_count": len(self._approved),
        }

    def opt_in(self, *, explicit_user_action: bool = False) -> Dict[str, Any]:
        if explicit_user_action is not True:
            return {"success": False, "reason": "explicit_user_action_required"}
        self._enabled = True
        return {"success": True, "status": self.status()}

    def opt_out(self, *, explicit_user_action: bool = False) -> Dict[str, Any]:
        if explicit_user_action is not True:
            return {"success": False, "reason": "explicit_user_action_required"}
        self._enabled = False
        # Withdrawal immediately invalidates all session candidates/approvals.
        self._pending.clear()
        self._approved.clear()
        return {"success": True, "status": self.status()}

    @staticmethod
    def _validate_value(memory_type: str, value: Any) -> Optional[Dict[str, str]]:
        if not isinstance(value, dict):
            return None
        allowed = _TYPE_FIELDS[memory_type]
        required = _REQUIRED_FIELDS[memory_type]
        if set(value) - set(allowed) or not required.issubset(value):
            return None
        clean: Dict[str, str] = {}
        for key, maximum in allowed.items():
            if key not in value:
                continue
            item = value[key]
            if not isinstance(item, str):
                return None
            item = item.strip()
            if not item or len(item) > maximum or any(ord(char) < 32 and char not in "\t" for char in item):
                return None
            if _SENSITIVE_TEXT.search(item):
                return None
            clean[key] = item
        return clean

    def propose(
        self,
        *,
        memory_type: str,
        value: Dict[str, Any],
        scope: str,
        provenance_kind: str,
        source_ref: str,
        confidence: float,
        expires_at: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create an ephemeral candidate for review; never writes it to disk."""
        if not self._enabled:
            return {"success": False, "reason": "consent_disabled"}
        if memory_type not in _TYPES:
            return {"success": False, "reason": "invalid_memory_type"}
        if scope not in _SCOPES:
            return {"success": False, "reason": "invalid_scope"}
        if provenance_kind != _PROVENANCE_KIND[memory_type]:
            return {"success": False, "reason": "invalid_provenance_kind"}
        if not isinstance(source_ref, str) or not _OPAQUE_REF.fullmatch(source_ref):
            return {"success": False, "reason": "invalid_opaque_source_ref"}
        if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
            return {"success": False, "reason": "invalid_confidence"}
        confidence = float(confidence)
        if not math.isfinite(confidence) or not 0.0 <= confidence <= 1.0:
            return {"success": False, "reason": "invalid_confidence"}
        clean_value = self._validate_value(memory_type, value)
        if clean_value is None:
            return {"success": False, "reason": "invalid_or_unsafe_value"}
        expiry = None
        if expires_at is not None:
            parsed_expiry = _parse_datetime(expires_at)
            if parsed_expiry is None or parsed_expiry <= _utc_now():
                return {"success": False, "reason": "invalid_or_expired_expiry"}
            expiry = _iso(parsed_expiry)
        if len(self._pending) >= MAX_PENDING:
            return {"success": False, "reason": "pending_candidate_limit"}

        candidate_id = str(uuid.uuid4())
        candidate = {
            "candidate_id": candidate_id,
            "schema_version": SCHEMA_VERSION,
            "memory_type": memory_type,
            "value": clean_value,
            "scope": scope,
            "provenance": {"kind": provenance_kind, "source_ref": source_ref},
            "confidence": confidence,
            "created_at": _iso(),
            "expires_at": expiry,
        }
        self._pending[candidate_id] = candidate
        return {"success": True, "candidate": deepcopy(candidate)}

    def list_pending(self) -> List[Dict[str, Any]]:
        """Return bounded candidates so the caller can show a review preview."""
        if not self._enabled:
            return []
        return [deepcopy(item) for item in list(self._pending.values())[:MAX_PENDING]]

    def approve_record(
        self,
        candidate_id: str,
        *,
        explicit_user_action: bool = False,
    ) -> Dict[str, Any]:
        """Approve one candidate after a separate explicit user action."""
        if explicit_user_action is not True:
            return {"success": False, "reason": "explicit_user_action_required"}
        if not self._enabled:
            return {"success": False, "reason": "consent_disabled"}
        if not isinstance(candidate_id, str) or candidate_id not in self._pending:
            return {"success": False, "reason": "candidate_not_found"}
        if len(self._approved) >= MAX_APPROVED:
            return {"success": False, "reason": "approved_record_limit"}

        candidate = self._pending[candidate_id]
        now = _utc_now()
        expiry = _parse_datetime(candidate.get("expires_at")) if candidate.get("expires_at") else None
        if candidate.get("expires_at") and (expiry is None or expiry <= now):
            del self._pending[candidate_id]
            return {"success": False, "reason": "candidate_expired"}

        record = {
            "schema_version": SCHEMA_VERSION,
            "memory_id": candidate_id,
            "memory_type": candidate["memory_type"],
            "value": deepcopy(candidate["value"]),
            "scope": candidate["scope"],
            "provenance": deepcopy(candidate["provenance"]),
            "confidence": candidate["confidence"],
            "created_at": candidate["created_at"],
            "updated_at": _iso(now),
            "expires_at": candidate["expires_at"],
            "approval": {
                "status": "approved",
                "actor": "user",
                "consent_version": CONSENT_VERSION,
                "decision_ref": "consent-" + uuid.uuid4().hex,
                "decided_at": _iso(now),
            },
            "lifecycle": "active",
        }
        self._approved[candidate_id] = deepcopy(record)
        del self._pending[candidate_id]
        return {"success": True, "record": record, "persistence": "not_written"}

    def can_write(self, record: Any, *, required_scope: Optional[str] = None) -> bool:
        """Authorize only an unchanged, explicitly approved, unexpired session record."""
        if not self._enabled or not isinstance(record, dict):
            return False
        memory_id = record.get("memory_id")
        if not isinstance(memory_id, str):
            return False
        approved = self._approved.get(memory_id)
        if not isinstance(approved, dict) or record != approved:
            return False
        if record.get("lifecycle") != "active":
            return False
        approval = record.get("approval")
        if not isinstance(approval, dict):
            return False
        if (
            approval.get("status") != "approved"
            or approval.get("actor") != "user"
            or approval.get("consent_version") != CONSENT_VERSION
        ):
            return False
        if required_scope is not None and record.get("scope") != required_scope:
            return False
        if record.get("scope") not in _SCOPES:
            return False
        if record.get("expires_at") is not None:
            expiry = _parse_datetime(record.get("expires_at"))
            if expiry is None or expiry <= _utc_now():
                return False
        return True

    authorize_write = can_write

    def get_approved_record(self, candidate_id: str) -> Optional[Dict[str, Any]]:
        """Return a defensive copy only while current process consent is enabled."""
        if not self._enabled or not isinstance(candidate_id, str):
            return None
        record = self._approved.get(candidate_id)
        return deepcopy(record) if isinstance(record, dict) else None


def handle_memory_command(
    command: str,
    manager: MemoryConsentManager,
    store: Optional[Any] = None,
) -> Optional[str]:
    """Handle explicit typed CLI commands; return None for normal Vyom commands."""
    normalized = " ".join(str(command or "").strip().lower().split())
    if not normalized.startswith((
        "memory consent", "memory pending", "memory approve", "memory propose", "memory save"
    )):
        return None

    if normalized in {"memory consent", "memory consent status"}:
        current = manager.status()
        enabled = "ON" if current["enabled"] else "OFF"
        return (
            f"Personal-memory consent is {enabled} for this session only. "
            "Saved records are accessible only while consent is ON. Writes require explicit record approval and 'memory save <candidate-id>'. "
            f"Pending records: {current['pending_count']}; approved this session: {current['approved_count']}."
        )

    if normalized == "memory consent on":
        result = manager.opt_in(explicit_user_action=True)
        if result["success"]:
            return (
                "Personal-memory opt-in is ON for this running session only. "
                "Nothing is saved automatically. Review a proposal, type 'memory approve <candidate-id>', then 'memory save <candidate-id>'. "
                "Type 'memory consent off' to withdraw."
            )
        return "Consent could not be enabled; an explicit user action is required."

    if normalized == "memory consent off":
        manager.opt_out(explicit_user_action=True)
        return (
            "Personal-memory consent is OFF. Pending candidates and session approvals were cleared. "
            "Previously saved local records are retained but cannot be used while consent is OFF; this command does not delete them."
        )

    # Proposals must be user-initiated typed commands. Raw STT transcripts are never learned automatically.
    raw_command = str(command or "").strip()
    proposal_match = re.match(
        r"(?is)^memory\s+propose\s+(correction|preference)\s+(.+?)\s*=>\s*(.+)$",
        raw_command,
    )
    if proposal_match:
        memory_type = proposal_match.group(1).lower()
        left = proposal_match.group(2).strip()
        right = proposal_match.group(3).strip()
        if memory_type == "correction":
            value = {"surface_form": left, "preferred_form": right}
            provenance_kind = "explicit_correction"
        else:
            value = {"key": left, "value_text": right}
            provenance_kind = "explicit_preference"
        proposed = manager.propose(
            memory_type=memory_type,
            value=value,
            scope="global",
            provenance_kind=provenance_kind,
            source_ref="cli:" + uuid.uuid4().hex,
            confidence=1.0,
        )
        if proposed.get("success"):
            candidate_id = proposed["candidate"]["candidate_id"]
            return (
                f"Candidate created for review only: {candidate_id}. It is not saved. "
                "Use 'memory pending', then approve and save it separately."
            )
        return "Memory proposal rejected: " + str(proposed.get("reason") or "invalid_request") + "."

    if normalized == "memory pending":
        pending = manager.list_pending()
        if not pending:
            return "There are no pending memory candidates for this session."
        lines = ["Pending memory candidates (not saved):"]
        for item in pending[:MAX_PENDING]:
            lines.append(
                f"- {item['candidate_id']} | {item['memory_type']} | scope={item['scope']} | "
                f"review value={item['value']}"
            )
        lines.append("Approve only an item you have reviewed by typing: memory approve <candidate-id>")
        return "\n".join(lines)

    parts = normalized.split()
    if len(parts) == 3 and parts[:2] == ["memory", "save"]:
        if store is None:
            return "Memory save unavailable: local storage has not been configured."
        record = manager.get_approved_record(parts[2])
        if record is None:
            return "Memory save denied: enable consent and separately approve this record first."
        result = store.save_approved(record)
        if result.get("success"):
            return f"Memory record {parts[2]} saved locally. It is accessible only while consent is ON."
        return "Memory save denied: " + str(result.get("reason") or "invalid_record") + "."

    if len(parts) == 3 and parts[:2] == ["memory", "approve"]:
        result = manager.approve_record(parts[2], explicit_user_action=True)
        if result["success"]:
            return (
                f"Record {parts[2]} approved for this session only. "
                "It was not written to disk."
            )
        return "Memory approval denied: " + str(result.get("reason") or "invalid_request") + "."

    return (
        "Memory commands: 'memory consent status', 'memory consent on', 'memory consent off', "
        "'memory pending', 'memory approve <candidate-id>', and 'memory save <candidate-id>'. "
        "Propose with 'memory propose correction <old> => <new>' or 'memory propose preference <key> => <value>'. "
        "Consent and approvals reset when Vyom exits."
    )
