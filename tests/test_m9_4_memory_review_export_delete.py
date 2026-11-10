"""M9.4 regression tests for review, export and durable deletion."""

from datetime import datetime, timedelta, timezone
import json

import pytest

from ai_core.memory_consent import MemoryConsentManager, handle_memory_command
from ai_core.user_memory_store import MemoryStoreError, UserMemoryStore


def _saved_store(tmp_path, *, count=2):
    manager = MemoryConsentManager()
    store = UserMemoryStore(manager, tmp_path / "memory.json")
    manager.opt_in(explicit_user_action=True)
    ids = []
    for i in range(count):
        proposal = manager.propose(
            memory_type="correction",
            value={"surface_form": f"calcuator{i}", "preferred_form": f"calculator{i}", "language": "en"},
            scope="global", provenance_kind="explicit_correction",
            source_ref=f"turn:m9.4.{i}", confidence=0.9,
        )
        assert proposal["success"] is True
        approved = manager.approve_record(proposal["candidate"]["candidate_id"], explicit_user_action=True)
        assert approved["success"] is True
        assert store.save_approved(approved["record"])["success"] is True
        ids.append(approved["record"]["memory_id"])
    return manager, store, ids


def test_m9_4_review_requires_consent_and_lists_only_validated_saved_records(tmp_path):
    manager, store, ids = _saved_store(tmp_path)
    assert len(store.review_records()) == 2
    manager.opt_out(explicit_user_action=True)
    with pytest.raises(MemoryStoreError, match="memory_consent_required"):
        store.review_records()
    manager.opt_in(explicit_user_action=True)
    reviewed = store.review_records()
    assert {record["memory_id"] for record in reviewed} == set(ids)
    assert all("raw_transcript" not in record for record in reviewed)


def test_m9_4_export_requires_consent_safe_new_json_path_and_round_trips(tmp_path):
    manager, store, ids = _saved_store(tmp_path)
    folder = tmp_path / "exports"
    folder.mkdir()
    destination = folder / "approved-memory.json"
    assert store.export_to(destination)["success"] is True
    exported = json.loads(destination.read_text(encoding="utf-8"))
    assert exported["schema_version"] == 1
    assert {r["memory_id"] for r in exported["records"]} == set(ids)
    assert all("raw_transcript" not in r and "execution_plan" not in r for r in exported["records"])
    assert store.export_to(destination)["reason"] == "export_destination_exists"
    assert store.export_to(store.storage_path)["reason"] == "export_path_is_memory_store"
    assert store.export_to(tmp_path / "bad.txt")["reason"] == "export_extension_invalid"
    assert store.export_to("relative-export.json")["reason"] == "export_path_must_be_absolute"
    manager.opt_out(explicit_user_action=True)
    blocked = folder / "blocked.json"
    assert store.export_to(blocked)["reason"] == "memory_consent_required"
    assert not blocked.exists()


def test_m9_4_export_rejects_symlink_destination_and_does_not_overwrite(tmp_path):
    _, store, _ = _saved_store(tmp_path)
    target = tmp_path / "target.json"
    target.write_text("keep", encoding="utf-8")
    link = tmp_path / "link.json"
    try:
        link.symlink_to(target)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation is unavailable on this platform")
    assert store.export_to(link)["reason"] == "export_destination_exists"
    assert target.read_text(encoding="utf-8") == "keep"


def test_m9_4_delete_one_persists_and_reload_confirms_removal(tmp_path):
    manager, store, ids = _saved_store(tmp_path)
    assert store.delete_one(ids[0]) == {"success": True, "deleted_count": 1}
    reloaded = UserMemoryStore(manager, store.storage_path)
    assert {r["memory_id"] for r in reloaded.review_records()} == {ids[1]}
    assert store.delete_one(ids[0]) == {"success": False, "reason": "memory_record_not_found"}


def test_m9_4_delete_all_works_with_consent_off_and_verifies_file_absence(tmp_path):
    manager, store, _ = _saved_store(tmp_path)
    manager.opt_out(explicit_user_action=True)
    assert store.delete_all() == {"success": True, "deleted_count": 2}
    assert not store.storage_path.exists()
    assert store.delete_all() == {"success": True, "deleted_count": 0}
    manager.opt_in(explicit_user_action=True)
    assert UserMemoryStore(manager, store.storage_path).review_records() == []


def test_m9_4_corrupt_store_is_never_overwritten_by_review_export_or_delete(tmp_path):
    manager = MemoryConsentManager()
    manager.opt_in(explicit_user_action=True)
    path = tmp_path / "memory.json"
    path.write_text("{broken", encoding="utf-8")
    store = UserMemoryStore(manager, path)
    with pytest.raises(MemoryStoreError, match="memory_store_parse_failed"):
        store.review_records()
    assert store.export_to(tmp_path / "export.json")["reason"] == "memory_store_parse_failed"
    assert store.delete_one("missing")["reason"] == "memory_store_parse_failed"
    assert path.read_text(encoding="utf-8") == "{broken"
    assert store.delete_all()["reason"] == "memory_store_parse_failed"
    assert path.read_text(encoding="utf-8") == "{broken"


def test_m9_4_cli_lists_inspects_exports_and_deletes_explicitly(tmp_path):
    manager, store, ids = _saved_store(tmp_path)
    listing = handle_memory_command("memory list", manager, store)
    assert ids[0] in listing and ids[1] in listing
    inspected = handle_memory_command("memory inspect " + ids[0], manager, store)
    assert ids[0] in inspected and "confidence=0.9" in inspected
    export_path = tmp_path / "cli-export.json"
    response = handle_memory_command('memory export "' + str(export_path) + '"', manager, store)
    assert "Exported" in response
    assert export_path.exists()
    assert "deleted" in handle_memory_command("memory delete " + ids[0], manager, store).lower()
    manager.opt_out(explicit_user_action=True)
    assert "consent" in handle_memory_command("memory list", manager, store).lower()
    assert "deleted" in handle_memory_command("memory delete all", manager, store).lower()
    assert not store.storage_path.exists()


def test_m9_4_expired_records_are_reviewable_but_not_usable_or_exported(tmp_path):
    manager, store, ids = _saved_store(tmp_path, count=1)
    payload = json.loads(store.storage_path.read_text(encoding="utf-8"))
    payload["records"][ids[0]]["expires_at"] = (
        datetime.now(timezone.utc) - timedelta(seconds=1)
    ).isoformat()
    store.storage_path.write_text(json.dumps(payload), encoding="utf-8")
    reloaded = UserMemoryStore(manager, store.storage_path)
    assert len(reloaded.review_records()) == 1
    assert reloaded.load_usable() == []
    export_path = tmp_path / "expired.json"
    assert reloaded.export_to(export_path)["success"] is True
    assert json.loads(export_path.read_text(encoding="utf-8"))["records"] == []
