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
