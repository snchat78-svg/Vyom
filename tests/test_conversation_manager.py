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

