"""M9.1 baseline tests; no long-term personal-memory runtime is activated here."""

import json
from pathlib import Path

from ai_core.skill_registry import SkillRegistry
from memory.session_memory import SessionMemory

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_m9_1_session_memory_is_transient_bounded_and_resettable(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    memory = SessionMemory()
    assert not hasattr(memory, "storage_path")

    memory.start_task("synthetic goal for M9.1 test", preserve_context=False)
    for index in range(105):
        memory.add_message("user", f"synthetic-message-{index}")
        memory.record_result({"synthetic_index": index}, success=True)

    assert len(memory.conversation_history) == 100
    assert memory.conversation_history[0]["text"] == "synthetic-message-5"
    assert len(memory.task_history) == 100
    assert list(tmp_path.iterdir()) == []

    memory.reset()
    snapshot = memory.snapshot()
    assert snapshot["current_goal"] == ""
    assert snapshot["conversation_history"] == []
    assert snapshot["task_history"] == []


def test_m9_1_skill_registry_persists_proposals_but_not_as_enabled_skills(tmp_path):
    path = tmp_path / "registry.json"
    registry = SkillRegistry(storage_path=str(path))
    result = registry.register(
        name="m9_inventory_demo",
        description="Synthetic proposal used only by a test.",
        goal="synthetic goal, not a real user memory",
        requirements=["test_only"],
        plan=[{"step": 1, "action": "synthetic_action"}],
    )

    assert result["success"] is True
    saved = json.loads(path.read_text(encoding="utf-8"))["m9_inventory_demo"]
    assert saved["goal"] == "synthetic goal, not a real user memory"
    assert saved["enabled"] is False
    assert saved["approved"] is False
    assert saved["validated"] is False
    assert saved["executable"] is False
    assert registry.enable("m9_inventory_demo") is False
    assert registry.approve("m9_inventory_demo") is True
    assert registry.enable("m9_inventory_demo") is False
    assert registry.validate("m9_inventory_demo") is True
    assert registry.enable("m9_inventory_demo") is True


def test_m9_1_runtime_skill_registry_is_gitignored():
    ignore_file = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "/skills/registry.json" in ignore_file.splitlines()
    assert "/skills/registry.json.tmp" in ignore_file.splitlines()


def test_m9_1_proposed_schema_is_versioned_bounded_and_consent_gated():
    schema_path = REPO_ROOT / "docs" / "schemas" / "vyom_user_memory.v1.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["properties"]["schema_version"]["const"] == 1
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) >= {
        "schema_version", "memory_id", "memory_type", "value", "scope",
        "provenance", "confidence", "created_at", "updated_at", "expires_at",
        "approval", "lifecycle",
    }
    assert schema["properties"]["memory_type"]["enum"] == [
        "correction", "preference", "verified_workflow"
    ]
    assert schema["properties"]["confidence"]["minimum"] == 0
    assert schema["properties"]["confidence"]["maximum"] == 1
    assert schema["properties"]["approval"]["properties"]["status"]["const"] == "approved"
    assert schema["properties"]["approval"]["properties"]["actor"]["const"] == "user"
    assert schema["properties"]["value"]["additionalProperties"] is False
    assert len(schema["allOf"]) == 3
