"""M9.2 tests for explicit opt-in, separate record approval, and fail-closed write authorization."""

from datetime import datetime, timedelta, timezone

from ai_core.memory_consent import MemoryConsentManager, handle_memory_command


def _candidate(manager, *, expires_at=None):
    return manager.propose(
        memory_type="correction",
        value={
            "surface_form": "calcuator",
            "preferred_form": "calculator",
            "language": "en",
        },
        scope="global",
        provenance_kind="explicit_correction",
        source_ref="turn:test-001",
        confidence=0.91,
        expires_at=expires_at,
    )


def test_m9_2_consent_is_default_off_and_never_writes_to_disk(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    manager = MemoryConsentManager()

    assert manager.status()["enabled"] is False
    assert manager.status()["mode"] == "session_only"
    assert _candidate(manager)["reason"] == "consent_disabled"
    assert list(tmp_path.iterdir()) == []


def test_m9_2_opt_in_requires_an_explicit_user_action_and_cli_is_visible():
    manager = MemoryConsentManager()

    assert manager.opt_in(explicit_user_action="yes")["success"] is False
    response = handle_memory_command("memory consent on", manager)
    assert "ON for this running session only" in response
    assert manager.status()["enabled"] is True
    assert handle_memory_command("memory consent status", manager).find("ON") >= 0
    assert manager.status()["persistent_memory_storage"] == "not_implemented"


def test_m9_2_each_record_needs_separate_explicit_approval_before_write_authorization():
    manager = MemoryConsentManager()
    manager.opt_in(explicit_user_action=True)
    candidate = _candidate(manager)
    assert candidate["success"] is True
    candidate_id = candidate["candidate"]["candidate_id"]

    assert manager.can_write({"memory_id": candidate_id}) is False
    assert manager.approve_record(candidate_id)["success"] is False
    approved = manager.approve_record(candidate_id, explicit_user_action=True)
    assert approved["success"] is True
    record = approved["record"]

    assert record["approval"]["actor"] == "user"
    assert record["approval"]["status"] == "approved"
    assert approved["persistence"] == "not_written"
    assert manager.can_write(record) is True
    assert manager.can_write(record, required_scope="application") is False
    assert list(manager._pending) == []


def test_m9_2_write_gate_rejects_tampering_and_unapproved_or_expired_records():
    manager = MemoryConsentManager()
    manager.opt_in(explicit_user_action=True)

    candidate = _candidate(manager)
    record = manager.approve_record(
        candidate["candidate"]["candidate_id"],
        explicit_user_action=True,
    )["record"]
    tampered = dict(record)
    tampered["value"] = dict(record["value"], preferred_form="run unexpected command")

    assert manager.can_write(tampered) is False
    assert manager.can_write(record) is True

    expiry = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
    expired = _candidate(manager, expires_at=expiry)
    assert expired["success"] is False
    assert expired["reason"] == "invalid_or_expired_expiry"


def test_m9_2_withdrawal_clears_approvals_and_future_writes():
    manager = MemoryConsentManager()
    manager.opt_in(explicit_user_action=True)
    candidate = _candidate(manager)["candidate"]
    record = manager.approve_record(candidate["candidate_id"], explicit_user_action=True)["record"]
    assert manager.can_write(record) is True

    withdrawal = handle_memory_command("memory consent off", manager)
    assert "Consent is OFF" in withdrawal
    assert manager.status()["enabled"] is False
    assert manager.status()["pending_count"] == 0
    assert manager.status()["approved_count"] == 0
    assert manager.can_write(record) is False


def test_m9_2_new_process_has_no_inherited_consent_or_approval():
    first = MemoryConsentManager()
    first.opt_in(explicit_user_action=True)
    candidate = _candidate(first)["candidate"]
    record = first.approve_record(candidate["candidate_id"], explicit_user_action=True)["record"]

    restarted = MemoryConsentManager()
    assert restarted.status()["enabled"] is False
    assert restarted.can_write(record) is False


def test_m9_2_rejects_unbounded_unknown_fields_invalid_scope_and_non_opaque_provenance():
    manager = MemoryConsentManager()
    manager.opt_in(explicit_user_action=True)

    bad_value = _candidate(manager)
    assert bad_value["success"] is True
    assert manager.propose(
        memory_type="correction",
        value={"surface_form": "a", "preferred_form": "b", "raw_transcript": "leak"},
        scope="global",
        provenance_kind="explicit_correction",
        source_ref="turn:test-002",
        confidence=0.5,
    )["reason"] == "invalid_or_unsafe_value"
    assert manager.propose(
        memory_type="correction",
        value={"surface_form": "a", "preferred_form": "b"},
        scope="whole-world",
        provenance_kind="explicit_correction",
        source_ref="turn:test-003",
        confidence=0.5,
    )["reason"] == "invalid_scope"
    assert manager.propose(
        memory_type="correction",
        value={"surface_form": "a", "preferred_form": "b"},
        scope="global",
        provenance_kind="explicit_correction",
        source_ref="raw utterance is not an opaque ref",
        confidence=0.5,
    )["reason"] == "invalid_opaque_source_ref"
    assert manager.propose(
        memory_type="preference",
        value={"key": "theme", "value_text": "password=definitely-not-safe"},
        scope="global",
        provenance_kind="explicit_preference",
        source_ref="turn:test-004",
        confidence=0.5,
    )["reason"] == "invalid_or_unsafe_value"


def test_m9_2_pending_review_and_explicit_record_approval_cli():
    manager = MemoryConsentManager()
    manager.opt_in(explicit_user_action=True)
    candidate = _candidate(manager)["candidate"]

    listing = handle_memory_command("memory pending", manager)
    assert candidate["candidate_id"] in listing
    assert "not saved" in listing

    approval = handle_memory_command("memory approve " + candidate["candidate_id"], manager)
    assert "approved for this session only" in approval
    assert manager.status()["approved_count"] == 1


def test_m9_2_normal_commands_are_not_intercepted():
    manager = MemoryConsentManager()
    assert handle_memory_command("open calculator", manager) is None
    assert handle_memory_command("what is memory consent?", manager) is None
