"""Validated, versioned local storage for explicitly approved Vyom user memory.

This module stores only bounded record metadata that has explicit, current
user consent and per-record approval. It does not store raw transcripts,
complete runnable plans, clipboard contents, arbitrary webpage text or
credentials. Reads are blocked while process-local consent is OFF.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import re
import tempfile
from typing import Any, Dict, List, Optional
import uuid

from ai_core.memory_consent import (
    CONSENT_VERSION,
    MemoryConsentManager,
    SCHEMA_VERSION,
    _OPAQUE_REF,
    _PROVENANCE_KIND,
    _SCOPES,
    _TYPE_FIELDS,
    _TYPES,
)

MAX_RECORDS = 256
MAX_STORE_BYTES = 1_000_000
_ENVELOPE_KEYS = {"schema_version", "updated_at", "records"}
_RECORD_KEYS = {
    "schema_version", "memory_id", "memory_type", "value", "scope",
    "provenance", "confidence", "created_at", "updated_at", "expires_at",
    "approval", "lifecycle",
}
_APPROVAL_KEYS = {"status", "actor", "consent_version", "decision_ref", "decided_at"}
_PROVENANCE_KEYS = {"kind", "source_ref"}
_DECISION_REF = re.compile(r"^consent-[0-9a-f]{32}$")


class MemoryStoreError(RuntimeError):
    """An existing local memory store was inaccessible or failed validation."""


def _parse_datetime(value: Any) -> Optional[datetime]:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except (TypeError, ValueError, OverflowError):
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class UserMemoryStore:
    """Bounded schema-v1 local store; construction performs no filesystem I/O."""

    def __init__(
        self,
        consent_manager: MemoryConsentManager,
        storage_path: Optional[Any] = None,
    ) -> None:
        if not isinstance(consent_manager, MemoryConsentManager):
            raise TypeError("A MemoryConsentManager is required.")
        self.consent_manager = consent_manager
        self.storage_path = (
            Path(storage_path).expanduser()
            if storage_path is not None
            else self.default_storage_path()
        )
        self._records: Dict[str, Dict[str, Any]] = {}
        self._loaded = False

    @staticmethod
    def default_storage_path() -> Path:
        if os.name == "nt":
            root = Path(
                os.environ.get("LOCALAPPDATA")
                or (Path.home() / "AppData" / "Local")
            )
            return root / "Vyom" / "user_memory.v1.json"
        root = Path(
            os.environ.get("XDG_STATE_HOME")
            or (Path.home() / ".local" / "state")
        )
        return root / "vyom" / "user_memory.v1.json"

    @staticmethod
    def _valid_record(record: Any) -> bool:
        if not isinstance(record, dict) or set(record) != _RECORD_KEYS:
            return False
        if isinstance(record.get("schema_version"), bool):
            return False
        if record.get("schema_version") != SCHEMA_VERSION:
            return False

        memory_id = record.get("memory_id")
        if not isinstance(memory_id, str):
            return False
        try:
            if str(uuid.UUID(memory_id)) != memory_id:
                return False
        except (ValueError, TypeError, AttributeError):
            return False

        memory_type = record.get("memory_type")
        if not isinstance(memory_type, str) or memory_type not in _TYPES:
            return False
        if record.get("scope") not in _SCOPES:
            return False

        value = record.get("value")
        if not isinstance(value, dict):
            return False
        required_fields = {
            "correction": {"surface_form", "preferred_form"},
            "preference": {"key", "value_text"},
            "verified_workflow": {"workflow_id", "display_name", "verified_summary"},
        }[memory_type]
        if set(value) - set(_TYPE_FIELDS[memory_type]):
            return False
        if not required_fields.issubset(value):
            return False
        if MemoryConsentManager._validate_value(memory_type, value) != value:
            return False

        provenance = record.get("provenance")
        if not isinstance(provenance, dict) or set(provenance) != _PROVENANCE_KEYS:
            return False
        if provenance.get("kind") != _PROVENANCE_KIND[memory_type]:
            return False
        source_ref = provenance.get("source_ref")
        if not isinstance(source_ref, str) or not _OPAQUE_REF.fullmatch(source_ref):
            return False

        confidence = record.get("confidence")
        if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
            return False
        try:
            confidence = float(confidence)
        except (TypeError, ValueError, OverflowError):
            return False
        if not math.isfinite(confidence) or not 0.0 <= confidence <= 1.0:
            return False

        created = _parse_datetime(record.get("created_at"))
        updated = _parse_datetime(record.get("updated_at"))
        if created is None or updated is None or updated < created:
            return False
        expiry_raw = record.get("expires_at")
        if expiry_raw is not None and _parse_datetime(expiry_raw) is None:
            return False

        approval = record.get("approval")
        if not isinstance(approval, dict) or set(approval) != _APPROVAL_KEYS:
            return False
        if approval.get("status") != "approved" or approval.get("actor") != "user":
            return False
        consent_version = approval.get("consent_version")
        if not isinstance(consent_version, str) or not 1 <= len(consent_version) <= 64:
            return False
        decision_ref = approval.get("decision_ref")
        if not isinstance(decision_ref, str) or not _DECISION_REF.fullmatch(decision_ref):
            return False
        if _parse_datetime(approval.get("decided_at")) is None:
            return False
        if record.get("lifecycle") not in {"active", "suspended", "expired", "revoked"}:
            return False
        return True

    def _load(self) -> None:
        if self._loaded:
            return
        try:
            stat = self.storage_path.stat()
        except FileNotFoundError:
            self._records = {}
            self._loaded = True
            return
        except Exception as exc:
            raise MemoryStoreError("memory_store_access_failed") from exc

        if stat.st_size > MAX_STORE_BYTES:
            raise MemoryStoreError("memory_store_size_limit")
        try:
            payload = json.loads(self.storage_path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise MemoryStoreError("memory_store_parse_failed") from exc

        if not isinstance(payload, dict) or set(payload) != _ENVELOPE_KEYS:
            raise MemoryStoreError("memory_store_envelope_invalid")
        schema_version = payload.get("schema_version")
        if isinstance(schema_version, bool) or schema_version != SCHEMA_VERSION:
            raise MemoryStoreError("memory_store_schema_unsupported")
        if _parse_datetime(payload.get("updated_at")) is None:
            raise MemoryStoreError("memory_store_timestamp_invalid")
        records = payload.get("records")
        if not isinstance(records, dict) or len(records) > MAX_RECORDS:
            raise MemoryStoreError("memory_store_records_invalid")

        validated: Dict[str, Dict[str, Any]] = {}
        for key, record in records.items():
            if not isinstance(key, str) or not self._valid_record(record):
                raise MemoryStoreError("memory_store_record_invalid")
            if record.get("memory_id") != key:
                raise MemoryStoreError("memory_store_record_key_mismatch")
            validated[key] = deepcopy(record)
        self._records = validated
        self._loaded = True

    def _write_atomic(self) -> None:
        payload = {
            "schema_version": SCHEMA_VERSION,
            "updated_at": _now_iso(),
            "records": self._records,
        }
        encoded = json.dumps(
            payload, ensure_ascii=False, indent=2, allow_nan=False
        ) + "\n"
        encoded_bytes = encoded.encode("utf-8")
        if len(encoded_bytes) > MAX_STORE_BYTES:
            raise MemoryStoreError("memory_store_size_limit")

        temporary_path: Optional[Path] = None
        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=str(self.storage_path.parent),
                prefix=".vyom-memory-",
                suffix=".tmp",
                delete=False,
            ) as handle:
                temporary_path = Path(handle.name)
                handle.write(encoded)
                handle.flush()
                os.fsync(handle.fileno())
            try:
                os.chmod(temporary_path, 0o600)
            except OSError:
                # Windows ACLs, not chmod bits, define the actual access boundary.
                pass
            os.replace(temporary_path, self.storage_path)
            temporary_path = None
        except Exception as exc:
            raise MemoryStoreError("memory_store_write_failed") from exc
        finally:
            if temporary_path is not None:
                try:
                    temporary_path.unlink(missing_ok=True)
                except OSError:
                    pass

    def save_approved(self, record: Any) -> Dict[str, Any]:
        """Persist only an unchanged active record approved during current consent."""
        if not self.consent_manager.can_write(record):
            return {"success": False, "reason": "consent_or_record_approval_required"}
        if not self._valid_record(record):
            return {"success": False, "reason": "record_schema_invalid"}
        try:
            self._load()
        except MemoryStoreError as exc:
            return {"success": False, "reason": str(exc)}

        memory_id = record["memory_id"]
        existing = self._records.get(memory_id)
        if existing is not None:
            if existing == record:
                return {"success": True, "memory_id": memory_id, "duplicate": True}
            return {"success": False, "reason": "memory_id_already_exists"}
        if len(self._records) >= MAX_RECORDS:
            return {"success": False, "reason": "memory_record_limit"}

        self._records[memory_id] = deepcopy(record)
        try:
            self._write_atomic()
        except MemoryStoreError as exc:
            self._records.pop(memory_id, None)
            return {"success": False, "reason": str(exc)}
        return {"success": True, "memory_id": memory_id, "duplicate": False}

    def load_usable(self, *, required_scope: Optional[str] = None) -> List[Dict[str, Any]]:
        """Return only active/unexpired approved records while current consent is ON."""
        if self.consent_manager.status().get("enabled") is not True:
            return []
        if required_scope is not None and required_scope not in _SCOPES:
            return []
        self._load()
        now = datetime.now(timezone.utc)
        usable: List[Dict[str, Any]] = []
        for record in self._records.values():
            if not self._valid_record(record):
                raise MemoryStoreError("memory_store_record_invalid")
            if record.get("lifecycle") != "active":
                continue
            approval = record["approval"]
            if (
                approval.get("status") != "approved"
                or approval.get("actor") != "user"
                or approval.get("consent_version") != CONSENT_VERSION
            ):
                continue
            if required_scope is not None and record["scope"] != required_scope:
                continue
            if record.get("expires_at") is not None:
                expiry = _parse_datetime(record["expires_at"])
                if expiry is None or expiry <= now:
                    continue
            usable.append(deepcopy(record))
        return usable

    def count_usable(self) -> int:
        return len(self.load_usable())
