"""M0.4 regression: desktop text and voice front-ends share one conversation manager."""

import sys
from types import ModuleType


def test_main_routes_text_through_same_manager_injected_into_voice(monkeypatch):
    import command_engine.executor as command_executor
    import ai_core.main as main_module

    events = []

    class FakeParser:
        def parse(self, text):
            parsed = str(text).strip().lower()
            events.append(("parse", parsed))
            return parsed

    class FakeConversationManager:
        def __init__(self):
            self.calls = []
            events.append(("manager_created", self))

        def process_text(self, text):
            self.calls.append(("text", text))
            events.append(("text", text))
            return {"success": True, "message": "shared manager response", "trace": {"trace_id": "test-trace"}}

        def process_voice(self, text, metadata=None):
            self.calls.append(("voice", text, metadata))
            events.append(("voice", text, metadata))
            return {"success": True, "message": "shared voice response"}

    class FakeVoiceController:
        def __init__(self, conversation_manager=None, **kwargs):
            self.conversation_manager = conversation_manager
            events.append(("voice_manager", conversation_manager))

    parser_module = ModuleType("command_engine.parser")
    parser_module.CommandParser = FakeParser
    manager_module = ModuleType("ai_core.conversation_manager")
    manager_module.ConversationManager = FakeConversationManager
    voice_module = ModuleType("voice.voice_controller")
    voice_module.VoiceController = FakeVoiceController

    monkeypatch.setitem(sys.modules, "command_engine.parser", parser_module)
    monkeypatch.setitem(sys.modules, "ai_core.conversation_manager", manager_module)
    monkeypatch.setitem(sys.modules, "voice.voice_controller", voice_module)
    monkeypatch.setattr(main_module, "_configure_console", lambda: None)
    monkeypatch.setattr(main_module, "_safe_print", lambda *args, **kwargs: None)

    runtime = command_executor.autonomous_agent.mission_runtime
    monkeypatch.setattr(runtime, "configure_default_recovery_journal", lambda: "clear")
    monkeypatch.setattr(runtime, "snapshot", lambda: {"replay_lock": None})

    direct_executor_calls = []
    monkeypatch.setattr(command_executor, "execute", lambda *args, **kwargs: direct_executor_calls.append(args))
    commands = iter(["Open Calculator", "exit"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(commands))

    main_module.main()

    manager = next(event[1] for event in events if event[0] == "manager_created")
    assert manager.calls == [("text", "open calculator")]
    assert next(event[1] for event in events if event[0] == "voice_manager") is manager
    assert direct_executor_calls == []


def test_text_and_voice_turns_share_executor_and_verification_contract():
    from ai_core.conversation_manager import ConversationManager

    calls = []
    voice_metadata = {
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

    def shared_executor(command, metadata=None, trace_sink=None):
        calls.append((command, metadata))
        verified = command == "open calculator"
        if isinstance(trace_sink, dict):
            trace_sink["intent"] = {
                "type": "open", "target_present": True, "hypothesis_count": 1
            }
            trace_sink["route"] = {"name": "command"}
            trace_sink["observation_evidence"] = {
                "available": True,
                "status": "captured" if verified else "no_new_observations",
                "event_count": 1 if verified else 0,
                "events": ([{
                    "phase": "after_action",
                    "step_type": "execute_existing_intent",
                    "result_success": True,
                    "verification_status": "verified",
                    "verification_level": "state",
                }] if verified else []),
                "trace_id": trace_sink.get("trace_id"),
            }
        result = {
            "success": True,
            "status": "success",
            "stage": "action_verified" if verified else "legacy_completed",
            "message": "Completed.",
        }
        if verified:
            result["verification"] = {
                "verified": True, "state": "observed", "verification_level": "state"
            }
        return result

    manager = ConversationManager(executor=shared_executor)
    text_verified = manager.process_text("open calculator")
    voice_verified = manager.process_voice("open calculator", metadata=voice_metadata)
    text_unverified = manager.process_text("open without evidence")
    voice_unverified = manager.process_voice(
        "open without evidence",
        metadata={"voice": {"raw_text": "Open without evidence", "roman_text": "open without evidence"}},
    )

    assert len(calls) == 4
    assert calls[0] == ("open calculator", None)
    assert calls[1] == ("open calculator", voice_metadata)
    assert calls[2][0] == "open without evidence"
    assert calls[3][0] == "open without evidence"

    assert text_verified["trace"]["source"] == "text"
    assert voice_verified["trace"]["source"] == "voice"
    assert text_verified["trace"]["trace_id"] != voice_verified["trace"]["trace_id"]
    for result in (text_verified, voice_verified):
        trace = result["trace"]
        assert result["success"] is True
        assert trace["execution"]["verification_status"] == "verified"
        assert trace["pipeline"]["observation_evidence"]["status"] == "captured"
        assert trace["pipeline"]["intent"]["type"] == "open"
        assert trace["pipeline"]["route"]["name"] == "command"

    assert voice_verified["trace"]["raw_transcript"] == "Open calcuator"
    assert voice_verified["trace"]["normalized_input"] == "open calculator"
    assert voice_verified["trace"]["recognized_language"] == "en-IN"
    assert voice_verified["trace"]["input_confidence"] == 0.91
    assert voice_verified["trace"]["corrections"][0]["to"] == "calculator"

    for result in (text_unverified, voice_unverified):
        assert result["success"] is True
        assert result["trace"]["execution"]["verification_status"] == "not_reported"
        assert result["trace"]["pipeline"]["observation_evidence"]["status"] == "no_new_observations"

