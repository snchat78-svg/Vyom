"""M9.3 tests for schema-validated, consent-gated local memory storage."""

from datetime import datetime, timedelta, timezone
import json
import re

import pytest

from ai_core.memory_consent import MemoryConsentManager
from ai_core.user_memory_store import MAX_STORE_BYTES, MemoryStoreError, UserMemoryStore


def _approved(manager, *, value=None, expires_at=None):
    manager.opt_in(explicit_user_action=True)
    candidate = manager.propose(
        memory_type="correction",
        value=value or {
            "surface_form": "calcuator",
            "preferred_form": "calculator",
            "language": "en",
        },
        scope="global",
        provenance_kind="explicit_correction",
        source_ref="turn:m9.3.test",
        confidence=0.91,
        expires_at=expires_at,
    )
    assert candidate["success"] is True
    approval = manager.approve_record(
        candidate["candidate"]["candidate_id"],
        explicit_user_action=True,
    )
    assert approval["success"] is True
    return approval["record"]


def test_m9_3_constructor_and_default_path_do_not_touch_repository(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    manager = MemoryConsentManager()
    store = UserMemoryStore(manager)
    assert store.storage_path.is_absolute()
    assert store.storage_path.name == "user_memory.v1.json"
    assert list(tmp_path.iterdir()) == []


def test_m9_3_save_requires_current_consent_and_record_approval(tmp_path):
    manager = MemoryConsentManager()
    store = UserMemoryStore(manager, tmp_path / "memory.json")
    record = _approved(manager)
    manager.opt_out(explicit_user_action=True)
    assert store.save_approved(record) == {
        "success": False,
        "reason": "consent_or_record_approval_required",
    }
    assert not (tmp_path / "memory.json").exists()


def test_m9_3_round_trip_preserves_provenance_scope_confidence_and_expiry(tmp_path):
    manager = MemoryConsentManager()
    store = UserMemoryStore(manager, tmp_path / "memory.json")
    expiry = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
    record = _approved(manager, expires_at=expiry)
    assert store.save_approved(record)["success"] is True
    assert store.save_approved(record)["duplicate"] is True

    payload = json.loads((tmp_path / "memory.json").read_text(encoding="utf-8"))
    stored = payload["records"][record["memory_id"]]
    assert payload["schema_version"] == 1
    assert stored["schema_version"] == 1
    assert stored["provenance"] == record["provenance"]
    assert stored["scope"] == "global"
    assert stored["confidence"] == 0.91
    assert stored["expires_at"] is not None

    reloaded = UserMemoryStore(manager, tmp_path / "memory.json")
    assert [item["memory_id"] for item in reloaded.load_usable()] == [record["memory_id"]]


def test_m9_3_read_requires_current_global_consent_even_after_restart(tmp_path):
    manager = MemoryConsentManager()
    store = UserMemoryStore(manager, tmp_path / "memory.json")
    record = _approved(manager)
    assert store.save_approved(record)["success"] is True

    restarted = MemoryConsentManager()
    restarted_store = UserMemoryStore(restarted, tmp_path / "memory.json")
    assert restarted_store.load_usable() == []
    restarted.opt_in(explicit_user_action=True)
    assert len(restarted_store.load_usable()) == 1
    restarted.opt_out(explicit_user_action=True)
    assert restarted_store.load_usable() == []


def test_m9_3_scope_expiry_and_lifecycle_filter_before_use(tmp_path):
    manager = MemoryConsentManager()
    store = UserMemoryStore(manager, tmp_path / "memory.json")
    record = _approved(manager)
    assert store.save_approved(record)["success"] is True
    assert store.load_usable(required_scope="application") == []
    assert len(store.load_usable(required_scope="global")) == 1

    path = tmp_path / "memory.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["records"][record["memory_id"]]["expires_at"] = (
        datetime.now(timezone.utc) - timedelta(seconds=5)
    ).isoformat()
    path.write_text(json.dumps(payload), encoding="utf-8")
    assert UserMemoryStore(manager, path).load_usable() == []


def test_m9_3_revoked_record_is_never_returned(tmp_path):
    manager = MemoryConsentManager()
    store = UserMemoryStore(manager, tmp_path / "memory.json")
    record = _approved(manager)
    assert store.save_approved(record)["success"] is True
    path = tmp_path / "memory.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["records"][record["memory_id"]]["lifecycle"] = "revoked"
    path.write_text(json.dumps(payload), encoding="utf-8")
    assert UserMemoryStore(manager, path).load_usable() == []


def test_m9_3_corrupt_or_unsupported_store_fails_closed_and_is_not_overwritten(tmp_path):
    manager = MemoryConsentManager()
    manager.opt_in(explicit_user_action=True)
    path = tmp_path / "memory.json"
    path.write_text("{broken", encoding="utf-8")
    with pytest.raises(MemoryStoreError, match="memory_store_parse_failed"):
        UserMemoryStore(manager, path).load_usable()
    assert path.read_text(encoding="utf-8") == "{broken"

    path.write_text(json.dumps({
        "schema_version": 77,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "records": {},
    }), encoding="utf-8")
    with pytest.raises(MemoryStoreError, match="memory_store_schema_unsupported"):
        UserMemoryStore(manager, path).load_usable()
    assert json.loads(path.read_text(encoding="utf-8"))["schema_version"] == 77


def test_m9_3_oversized_store_is_rejected_without_replacement(tmp_path):
    manager = MemoryConsentManager()
    manager.opt_in(explicit_user_action=True)
    path = tmp_path / "memory.json"
    path.write_text(" " * (MAX_STORE_BYTES + 1), encoding="utf-8")
    with pytest.raises(MemoryStoreError, match="memory_store_size_limit"):
        UserMemoryStore(manager, path).load_usable()
    assert path.stat().st_size == MAX_STORE_BYTES + 1


def test_m9_3_structurally_tampered_record_is_rejected_on_save(tmp_path):
    manager = MemoryConsentManager()
    store = UserMemoryStore(manager, tmp_path / "memory.json")
    record = _approved(manager)
    tampered = dict(record)
    tampered["value"] = dict(record["value"], unsupported_field="unexpected")
    assert store.save_approved(tampered) == {
        "success": False,
        "reason": "consent_or_record_approval_required",
    }
    assert store.save_approved(record)["success"] is True


def test_m9_3_explicit_cli_round_trip_requires_separate_approval_and_save(tmp_path):
    from ai_core.memory_consent import handle_memory_command

    manager = MemoryConsentManager()
    store = UserMemoryStore(manager, tmp_path / "memory.json")
    assert "ON for this running session only" in handle_memory_command(
        "memory consent on", manager, store
    )
    proposal = handle_memory_command(
        "memory propose correction calcuator => calculator", manager, store
    )
    assert "Candidate created" in proposal
    listing = handle_memory_command("memory pending", manager, store)
    match = re.search(r"([0-9a-f-]{36})", listing)
    assert match
    candidate_id = match.group(1)
    assert "save denied" in handle_memory_command(
        "memory save " + candidate_id, manager, store
    ).lower()
    assert not (tmp_path / "memory.json").exists()
    assert "approved for this session only" in handle_memory_command(
        "memory approve " + candidate_id, manager, store
    )
    assert "saved locally" in handle_memory_command(
        "memory save " + candidate_id, manager, store
    ).lower()
    assert len(store.load_usable()) == 1


def test_m9_3_atomic_write_failure_rolls_back_in_memory_state(tmp_path, monkeypatch):
    manager = MemoryConsentManager()
    store = UserMemoryStore(manager, tmp_path / "memory.json")
    record = _approved(manager)

    def fail_replace(source, destination):
        raise OSError("simulated atomic replacement failure")

    monkeypatch.setattr("ai_core.user_memory_store.os.replace", fail_replace)
    result = store.save_approved(record)
    assert result == {"success": False, "reason": "memory_store_write_failed"}
    assert not (tmp_path / "memory.json").exists()
    assert store._records == {}
