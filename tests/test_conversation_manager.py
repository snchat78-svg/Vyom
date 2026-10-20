"""
Project : Vyom AI
Module  : Conversation Manager Test

Purpose:
    Import and basic contract test only.
"""

from ai_core.conversation_manager import ConversationManager
from ai_core.conversation_result import ConversationResult, ConversationStatus


def test_conversation_manager_import():
    manager = ConversationManager()

    assert manager.active is True
    assert manager.turn_count == 0
    assert manager.get_history() == []

def test_voice_trace_preserves_raw_text_confidence_corrections_and_verification():
    calls = []

    def executor(command, metadata=None):
        calls.append((command, metadata))
        return {
            "success": True,
            "status": "success",
            "stage": "action_verified",
            "message": "The action completed.",
            "verification": {"success": True},
        }

    manager = ConversationManager(executor=executor)
    metadata = {
        "voice": {
            "raw_text": "Open calcuator",
            "recognized_language": "en-IN",
            "roman_text": "open calculator",
            "stt_status": "recognized",
            "command_confidence": 0.91,
            "command_corrections": [{
                "from": "calcuator",
                "to": "calculator",
                "score": 0.91,
                "position": 1,
            }],
        }
    }

    result = manager.process_voice("open calculator", metadata=metadata)
    trace = result["trace"]

    assert calls[0][0] == "open calculator"
    assert calls[0][1] == metadata
    assert trace["raw_transcript"] == "Open calcuator"
    assert trace["normalized_input"] == "open calculator"
    assert trace["input_confidence"] == 0.91
    assert trace["input_confidence_source"] == "command_normalizer"
    assert trace["corrections"][0]["to"] == "calculator"
    assert trace["execution"]["stage"] == "action_verified"
    assert trace["execution"]["verification_status"] == "verified"
    assert manager.get_history()[-1]["trace"] == trace


def test_voice_controller_forwards_current_utterance_metadata():
    from voice.voice_controller import VoiceController

    class CaptureConversationManager:
        def __init__(self):
            self.call = None

        def process_voice(self, command, metadata=None):
            self.call = (command, metadata)
            return {
                "success": True,
                "status": "success",
                "stage": "test",
                "message": "captured",
            }

    controller = VoiceController.__new__(VoiceController)
    controller.state = "listening"
    controller.last_raw_text = "Open calcuator"
    controller.last_voice_language = "en-IN"
    controller.last_voice_metadata = {
        "raw_text": "Open calcuator",
        "recognized_language": "en-IN",
        "roman_text": "open calculator",
        "command_confidence": 0.91,
        "command_corrections": [{"from": "calcuator", "to": "calculator", "score": 0.91, "position": 1}],
    }
    controller.conversation_manager = CaptureConversationManager()
    controller._log = lambda message: None

    result = controller.process_text("open calculator")

    command, metadata = controller.conversation_manager.call
    assert result["success"] is True
    assert command == "open calculator"
    assert metadata["voice"]["raw_text"] == "Open calcuator"
    assert metadata["voice"]["command_confidence"] == 0.91
    assert metadata["voice"]["command_corrections"][0]["to"] == "calculator"


def test_executor_emits_compact_intent_and_route_into_trace_sink(monkeypatch):
    import command_engine.executor as executor_module

    monkeypatch.setattr(
        executor_module.intent_engine,
        "detect",
        lambda command, metadata=None: {
            "intent": "conversation",
            "target": "conversation",
            "conversation_type": "conversation",
            "hypotheses": [{"intent": "conversation"}, {"intent": "unknown"}],
        },
    )
    monkeypatch.setattr(
        executor_module.goal_router,
        "route",
        lambda command, intent=None: {"route": "command", "reason": "test_path", "goal": False},
    )
    monkeypatch.setattr(executor_module.response_engine, "format", lambda **kwargs: "Hello.")
    sink = {"trace_id": "trace-test-1"}

    executor_module.execute("hello", trace_sink=sink)

    assert sink["intent"]["type"] == "conversation"
    assert sink["intent"]["target_present"] is True
    assert sink["intent"]["hypothesis_count"] == 2
    assert sink["route"]["name"] == "command"
    assert sink["routing_path"] == "conversation"


def test_pipeline_trace_has_mission_and_goal_summaries_without_plan_payloads():
    manager = ConversationManager(executor=lambda command: {
        "success": False,
        "status": "failed",
        "stage": "mission_blocked",
        "message": "Blocked.",
        "goal_compilation": {
            "success": True,
            "understood": True,
            "complexity": "compound",
            "goal": "private original task text",
            "sub_goals": [{"goal": "private subgoal"}],
            "suggested_intents": [{"intent": "open", "target": "private app"}],
        },
        "mission": {
            "mission_state": "blocked",
            "plan": [{
                "id": "private-step-id",
                "type": "execute_existing_intent",
                "status": "pending",
                "action": "send private content",
                "args": {"text": "private payload"},
                "depends_on": ["private-parent-step"],
                "precondition": {"window": "private precondition content"},
                "postcondition": {"state": "private postcondition content"},
            }],
            "progress": {"total": 1, "pending": 1, "completed": 0, "failed": 0, "executing": 0},
            "replay_lock": {"active": True},
            "recovery_journal_status": "active",
        },
        "context": {
            "current_app": "private-app-name",
            "current_file": "/private/path",
            "current_target": "private-target",
            "pending_selection": False,
            "awaiting_confirmation": True,
            "task_state": "private state",
        },
    })

    result = manager.process_text("run complex task")
    trace = result["trace"]
    encoded = str(trace)

    assert trace["mission"]["available"] is True
    assert trace["mission"]["state"] == "blocked"
    assert trace["mission"]["step_status_counts"]["pending"] == 1
    assert trace["mission"]["plan_steps"] == [{
        "position": 1,
        "type": "execute_existing_intent",
        "status": "pending",
        "dependency_count": 1,
        "precondition_present": True,
        "postcondition_present": True,
    }]
    assert trace["mission"]["plan_steps_truncated"] is False
    assert trace["mission"]["replay_lock_active"] is True
    assert trace["goal_compilation"]["sub_goal_count"] == 1
    assert trace["goal_compilation"]["suggested_intent_types"] == ["open"]
    assert trace["context"]["current_app_present"] is True
    assert trace["context"]["awaiting_confirmation"] is True
    for secret in ("private original task text", "private subgoal", "private payload",
                   "send private content", "private-step-id", "private-parent-step",
                   "private precondition content", "private postcondition content",
                   "private-app-name", "/private/path", "private-target", "private state"):
        assert secret not in encoded


def test_executor_correlates_only_current_turn_observations_without_payloads(monkeypatch):
    import time
    import command_engine.executor as executor_module

    world = executor_module.autonomous_agent.world_state
    now = time.time()
    monkeypatch.setattr(world, "observation_history", [{
        "timestamp": now - 10,
        "phase": "old_turn",
        "result": {"success": True, "stage": "verified"},
        "verification": {"verified": True},
        "world_state": {"timestamp": now - 10, "current_window": {"title": "stale private window"}},
    }])

    def fake_internal(command, metadata=None, trace_sink=None):
        timestamp = time.time()
        world.observation_history.append({
            "timestamp": timestamp,
            "phase": "after_action",
            "step_id": "private-step-id",
            "step_type": "action",
            "result": {
                "success": True,
                "status": "success",
                "stage": "verified",
                "private_result_payload": "do not leak",
            },
            "verification": {
                "verified": True,
                "state": "observed",
                "verification_level": "state",
                "target": "private target name",
                "reason": "private observation detail",
            },
            "world_state": {
                "timestamp": timestamp,
                "current_window": {"title": "private window title"},
                "focused_control": {"name": "private control"},
            },
        })
        return {
            "success": True,
            "status": "success",
            "stage": "verified",
            "message": "completed",
            "verification": {"verified": True, "state": "observed"},
        }

    monkeypatch.setattr(executor_module, "_execute_internal", fake_internal)
    manager = ConversationManager(executor=executor_module.execute)
    result = manager.process_text("do the test action")

    trace = result["trace"]
    evidence = trace["pipeline"]["observation_evidence"]
    assert evidence["trace_id"] == trace["trace_id"]
    assert evidence["status"] == "captured"
    assert evidence["event_count"] == 1
    assert len(evidence["events"]) == 1
    event = evidence["events"][0]
    assert event["phase"] == "after_action"
    assert event["verification_status"] == "verified"
    assert event["verification_level"] == "state"

    encoded = str(trace)
    for private_value in (
        "private-step-id", "do not leak", "private target name",
        "private observation detail", "private window title",
        "private control", "stale private window",
    ):
        assert private_value not in encoded


def test_executor_trace_marks_missing_observations_explicitly(monkeypatch):
    import command_engine.executor as executor_module

    world = executor_module.autonomous_agent.world_state
    monkeypatch.setattr(world, "observation_history", [])
    monkeypatch.setattr(
        executor_module,
        "_execute_internal",
        lambda command, metadata=None, trace_sink=None: {
            "success": True, "status": "success", "stage": "legacy_completed", "message": "done"
        },
    )
    manager = ConversationManager(executor=executor_module.execute)
    result = manager.process_text("simple response without observation")

    evidence = result["trace"]["pipeline"]["observation_evidence"]
    assert evidence["available"] is True
    assert evidence["status"] == "no_new_observations"
    assert evidence["event_count"] == 0
    assert evidence["events"] == []




def test_mission_plan_summary_is_bounded_and_never_copies_step_payloads():
    plan = [
        {
            "id": "secret-step-id-" + str(index),
            "type": "action",
            "status": "pending",
            "depends_on": ["secret-dependency"] if index else [],
            "args": {"text": "private payload"},
            "target": "private target",
            "precondition": {"control": "private condition"},
            "postcondition": {"value": "private state"},
        }
        for index in range(24)
    ]

    summary = ConversationManager._mission_summary({
        "mission": {"mission_state": "running", "plan": plan}
    })

    assert summary["step_count"] == 24
    assert len(summary["plan_steps"]) == 16
    assert summary["plan_steps_truncated"] is True
    assert summary["plan_steps"][0]["dependency_count"] == 0
    assert summary["plan_steps"][1]["dependency_count"] == 1
    encoded = str(summary)
    for private_value in (
        "secret-step-id", "secret-dependency", "private payload",
        "private target", "private condition", "private state",
    ):
        assert private_value not in encoded


def test_success_without_explicit_verification_is_not_reported_verified():
    manager = ConversationManager(executor=lambda command: {
        "success": True,
        "status": "success",
        "stage": "legacy_completed",
        "message": "Done.",
    })

    result = manager.process_text("hello")
    trace = result["trace"]

    assert trace["raw_transcript"] is None
    assert trace["raw_input"] == "hello"
    assert trace["normalized_input"] == "hello"
    assert trace["input_confidence"] is None
    assert trace["execution"]["success"] is True
    assert trace["execution"]["verification_status"] == "not_reported"


def test_empty_input_returns_trace_without_calling_executor():
    calls = []
    manager = ConversationManager(executor=lambda command: calls.append(command))

    result = manager.process_text("")

    assert result["status"] == "needs_clarification"
    assert result["trace"]["trace_id"]
    assert result["trace"]["execution"]["status"] == "needs_clarification"
    assert result["trace"]["pipeline"] == {"trace_id": result["trace"]["trace_id"]}
    assert "intent" not in result["trace"]["pipeline"]
    assert "route" not in result["trace"]["pipeline"]
    assert calls == []


def test_input_trace_history_stays_bounded():
    manager = ConversationManager(max_history=1, executor=lambda command: {
        "success": False, "status": "failed", "stage": "test_failure", "message": "No."
    })
    manager.process_text("first request")
    latest = manager.process_text("second request")
    history = manager.get_history()

    assert len(history) == 1
    assert history[0]["trace"]["raw_input"] == "second request"
    assert history[0]["trace"]["execution"]["verification_status"] == "not_reported"
    assert latest["trace"]["execution"]["stage"] == "test_failure"


def test_needs_confirmation_is_a_distinct_conversation_status():
    result = ConversationResult.from_executor_result({
        "success": False,
        "status": "needs_confirmation",
        "stage": "recovery_confirmation_required",
        "message": "Check the current window and confirm.",
        "requires_user_input": True,
    })
    assert result.status == ConversationStatus.NEEDS_CONFIRMATION
    assert result.response_text == "Check the current window and confirm."


if __name__ == "__main__":
    manager = ConversationManager()

    print("ConversationManager import: PASS")
    print(manager.snapshot())

