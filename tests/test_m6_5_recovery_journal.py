"""M6.5 tests for durable, payload-free uncertain-action recovery markers."""
import json

from ai_core.autonomous_agent import AutonomousAgent
from ai_core.mission_runtime import MissionRuntime


def _mark_uncertain(runtime, journal_path):
    runtime.configure_recovery_journal(journal_path)
    runtime.start("send a message", [{
        "id": "send_once",
        "step": 1,
        "type": "action",
        "action": "invoke_ui_element",
        "capability": "windows_ui",
        "target": "Send",
        "args": {"text": "private message body"},
        "depends_on": [],
    }])
    step = runtime.get_next_step()
    completed = runtime.mark_failed(
        step["id"],
        result={"success": False, "stage": "verification_failed"},
        reason="post-action verification unavailable",
        failure_policy={"category": "outcome_uncertain"},
        stop_mission=True,
    )
    assert completed is False
    assert runtime.snapshot()["replay_lock"]["active"] is True
    return runtime


def test_journal_persists_minimal_marker_without_action_payload(tmp_path):
    path = tmp_path / "nested" / "recovery_state.json"
    runtime = _mark_uncertain(MissionRuntime(), path)

    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["schema_version"] == 1
    assert saved["active"] is True
    assert saved["category"] == "outcome_uncertain"
    assert len(saved["fingerprint_sha256"]) == 64
    encoded = path.read_text(encoding="utf-8")
    for forbidden in ("private message body", "Send", "invoke_ui_element", '"args"', "send a message"):
        assert forbidden not in encoded
    assert runtime.snapshot()["recovery_journal_status"] == "active"


def test_restart_restores_blocker_but_never_restores_runnable_plan(tmp_path):
    path = tmp_path / "recovery_state.json"
    _mark_uncertain(MissionRuntime(), path)

    restarted = MissionRuntime()
    assert restarted.configure_recovery_journal(path) == "active"
    state = restarted.snapshot()
    assert state["recovery_restored_after_restart"] is True
    assert state["replay_lock"]["active"] is True
    assert state["replay_lock"]["runtime_record_available"] is False
    assert state["plan"] == []

    rejected = restarted.start("open calculator", [{
        "id": "new_task",
        "step": 1,
        "type": "action",
        "action": "open_application",
        "capability": "windows_app",
        "target": "Calculator",
        "args": {},
        "depends_on": [],
    }])
    assert rejected["mission_state"] == "blocked"
    assert restarted.unblock(allow_replay_after_confirmation=True) is False
    assert restarted.snapshot()["replay_lock"]["active"] is True


def test_restart_retry_is_not_attempted_and_cancel_clears_marker(tmp_path):
    path = tmp_path / "recovery_state.json"
    _mark_uncertain(MissionRuntime(), path)

    agent = AutonomousAgent(max_steps=5)
    agent.mission_runtime.configure_recovery_journal(path)
    agent._observe_cycle = lambda **kwargs: (_ for _ in ()).throw(
        AssertionError("restarted recovery must not observe/retry an unavailable plan")
    )

    retry = agent.handle_recovery_confirmation("nahi hua, dobara karo")
    assert retry["kind"] == "restart_retry_unavailable"
    assert retry["stage"] == "recovery_confirmation_required"
    assert retry["success"] is False

    cancelled = agent.handle_recovery_confirmation("cancel recovery")
    assert cancelled["kind"] == "cancelled"
    assert agent.mission_runtime.snapshot()["replay_lock"] is None
    assert not path.exists()


def test_inaccessible_journal_path_fails_closed_not_missing(monkeypatch, tmp_path):
    from pathlib import Path

    path = tmp_path / "restricted" / "recovery_state.json"
    original_stat = Path.stat

    def denied_stat(self, *args, **kwargs):
        if self == path:
            raise PermissionError("simulated inaccessible journal")
        return original_stat(self, *args, **kwargs)

    monkeypatch.setattr(Path, "stat", denied_stat)
    runtime = MissionRuntime()

    assert runtime.configure_recovery_journal(path) == "read_failed"
    lock = runtime.snapshot()["replay_lock"]
    assert lock["active"] is True
    assert lock["category"] == "recovery_journal_unreadable"
    assert runtime.snapshot()["recovery_journal_status"] == "read_failed"

    result = runtime.start("open calculator", [{
        "id": "new_task",
        "step": 1,
        "type": "action",
        "action": "open_application",
        "capability": "windows_app",
        "target": "Calculator",
        "args": {},
        "depends_on": [],
    }])
    assert result["mission_state"] == "blocked"
    assert runtime.snapshot()["plan"] == []


def test_corrupt_journal_fails_closed_until_explicit_cancel(tmp_path):
    path = tmp_path / "recovery_state.json"
    path.write_text("{not json", encoding="utf-8")

    runtime = MissionRuntime()
    runtime.configure_recovery_journal(path)
    lock = runtime.snapshot()["replay_lock"]
    assert lock["active"] is True
    assert lock["category"] == "recovery_journal_unreadable"
    assert lock["runtime_record_available"] is False
    assert runtime.start("open calculator", [])["mission_state"] == "blocked"
    assert runtime.resolve_uncertain_outcome("cancelled") is True
    assert runtime.snapshot()["replay_lock"] is None
    assert not path.exists()
