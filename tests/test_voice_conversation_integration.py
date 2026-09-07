"""Dependency-light Phase 0/1 boundary characterization tests."""

from ai_core.conversation_manager import ConversationManager
from ai_core.conversation_result import ConversationStatus
from command_engine.intent import IntentEngine
from command_engine import executor
from memory.session_memory import SessionMemory
from voice.voice_controller import VoiceController


class FakeSpeechToText:
    error_message = ""

    def is_available(self):
        return True


class FakeTextToSpeech:
    error_message = ""

    def __init__(self):
        self.spoken = []

    def is_available(self):
        return True

    def speak(self, text):
        self.spoken.append(text)
        return {"success": True}

    def stop(self):
        return None


class FakeConversationManager:
    def __init__(self):
        self.voice_messages = []

    def process_voice(self, text):
        self.voice_messages.append(text)
        return {"success": True, "response": "Done", "status": "success"}


class ScriptedSpeechToText(FakeSpeechToText):
    """Hardware-free persistent-STT boundary used by voice lifecycle tests."""

    def __init__(self, events):
        self.events = list(events)
        self.started = 0
        self.stopped = 0
        self.recoveries = 0
        self.listen_calls = []

    def start_session(self):
        self.started += 1
        return True

    def stop_session(self):
        self.stopped += 1

    def recover_session(self):
        self.recoveries += 1
        return self.start_session()

    def listen(self, **kwargs):
        self.listen_calls.append(kwargs)
        event = self.events.pop(0) if self.events else {"status": "silence"}
        if isinstance(event, str):
            return {"success": True, "status": "recognized", "text": event}
        return {"success": False, "text": "", **event}


def run_voice(events):
    manager = FakeConversationManager()
    stt = ScriptedSpeechToText(events)
    tts = FakeTextToSpeech()
    controller = VoiceController(stt, tts, manager)
    assert controller.run() is True
    return controller, stt, tts, manager


def test_conversation_turn_is_bounded_and_structured():
    manager = ConversationManager(max_history=1, executor=lambda text: {"success": True, "message": text})
    result = manager.process_voice("नोटपैड open करो")
    manager.process_text("hello")

    assert result["status"] == ConversationStatus.SUCCESS.value
    turn = manager.snapshot()["history"][0]
    assert set(("timestamp", "source", "input_text", "language", "response_text", "status", "duration_ms")) <= set(turn)
    assert turn["source"] == "text"


def test_conversation_outcomes_use_executor_structure_not_response_wording():
    manager = ConversationManager(executor=lambda text: {"success": False, "status": "needs_selection", "message": "choose"})
    result = manager.process_voice("open file")
    assert result["status"] == ConversationStatus.NEEDS_SELECTION.value
    assert result["success"] is False


def test_voice_controller_injection_routes_through_conversation_manager():
    manager = FakeConversationManager()
    tts = FakeTextToSpeech()
    controller = VoiceController(FakeSpeechToText(), tts, manager)

    result = controller._execute_voice_command("Vyom, open Notepad")

    assert manager.voice_messages == ["Vyom, open Notepad"]
    assert result["message"] == "Done"
    assert tts.spoken == ["Done"]


def test_wake_only_activates_with_tts_then_starts_command_listener():
    manager = FakeConversationManager()
    stt = ScriptedSpeechToText(["Vyom", "open Notepad"])
    tts = FakeTextToSpeech()
    controller = VoiceController(stt, tts, manager)
    controller.running = True

    activation = controller._wait_for_activation()
    controller._speak_activation_response()
    command = controller._listen_active_command()

    assert activation["activated"] is True
    assert controller.activated is True
    assert controller.state == "listening"
    assert "हाँ, बताइए।" in tts.spoken
    assert command == "open Notepad"
    assert len(stt.listen_calls) == 2


def test_wake_plus_command_strips_wake_and_keeps_session_active():
    controller, _, _, manager = run_voice(["Vyom open Notepad", "exit"])

    assert manager.voice_messages == ["open Notepad"]
    assert controller.activated is False


def test_continuous_commands_do_not_require_another_wake_word():
    _, _, _, manager = run_voice([
        "Vyom", "open Notepad", "close Notepad", "open Excel", "exit"
    ])

    assert manager.voice_messages == ["open Notepad", "close Notepad", "open Excel"]


def test_silence_keeps_active_session_listening():
    _, stt, _, manager = run_voice(["Vyom", {"status": "silence"}, "open Notepad", "exit"])

    assert manager.voice_messages == ["open Notepad"]
    assert len(stt.listen_calls) == 4


def test_device_error_recovers_microphone_and_resumes_active_session():
    _, stt, _, manager = run_voice([
        "Vyom", {"status": "device_error"}, "open Notepad", "exit"
    ])

    assert stt.recoveries == 1
    assert stt.started == 2
    assert manager.voice_messages == ["open Notepad"]


def test_exit_stops_voice_only_after_prior_command_executes():
    controller, stt, tts, manager = run_voice(["Vyom", "open Notepad", "exit"])

    assert manager.voice_messages == ["open Notepad"]
    assert controller.running is False
    assert stt.stopped >= 1
    assert "ठीक है। मैं सुनना बंद कर रहा हूँ।" in tts.spoken


def test_intent_engine_characterizes_english_hindi_hinglish_and_close():
    engine = IntentEngine()
    assert engine.detect("open Notepad")["intent"] == "open"
    assert engine.detect("नोटपैड खोल दो")["intent"] == "open"
    assert engine.detect("notepad kholo")["intent"] == "open"
    assert engine.detect("close Notepad")["intent"] == "close_app"


def test_session_memory_records_context_and_selection():
    memory = SessionMemory()
    memory.start_task("open report")
    memory.set_current_file("report.pdf")
    memory.set_pending_selection("report", ["a", "b"])

    assert memory.current_file == "report.pdf"
    assert memory.pending_selection is True
    assert memory.selection_options == ["a", "b"]


def test_executor_fast_paths_route_real_intents_to_tool_manager(monkeypatch):
    calls = []

    class ToolBoundary:
        selection_manager = None

        def execute(self, intent):
            calls.append(intent)
            return {"success": True, "message": "handled"}

    monkeypatch.setattr(executor, "tool_manager", ToolBoundary())
    executor.autonomous_agent.context.clear_task()
    executor.execute("open Notepad")
    executor.execute("search file report")
    executor.execute("close Notepad")

    assert [call["intent"] for call in calls] == ["open", "search_file", "close_app"]


def test_executor_unknown_goal_uses_existing_autonomous_agent(monkeypatch):
    calls = []

    class AgentBoundary:
        def run(self, goal, intent):
            calls.append((goal, intent))
            return {"message": "planned", "success": True}

    monkeypatch.setattr(executor, "autonomous_agent", AgentBoundary())
    monkeypatch.setattr(executor.intent_engine, "detect", lambda text: {"intent": "unknown", "target": text})

    executor.execute("prepare my monthly report")

    assert calls == [("prepare my monthly report", {"intent": "unknown", "target": "prepare my monthly report"})]
