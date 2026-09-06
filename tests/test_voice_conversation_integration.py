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
