"""Regression contracts for Phase 1-5 semantic/voice/UI integration."""

from ai_core.reasoning_gateway import AIReasoningGateway
from command_engine import executor
from command_engine.intent import IntentEngine
from voice.command_normalizer import VoiceCommandNormalizer
from voice.speech_to_text import SpeechToText


def test_romanized_hindi_one_is_a_selection_value():
    engine = IntentEngine()
    result = engine.detect("ek")
    assert result["intent"] == "selection"
    assert result["selection"] == "1"


def test_pending_selection_is_handled_before_semantic_goal_routing(monkeypatch):
    calls = []

    class SelectionManager:
        results = ["first.pdf", "second.pdf"]

        def has_results(self):
            return True

    class ToolBoundary:
        selection_manager = SelectionManager()

        def execute(self, intent):
            calls.append(intent)
            return {"success": True, "stage": "opened", "message": "Opened second.pdf"}

    class Context:
        def __init__(self):
            self.current_target = None
            self.current_app = None
            self.selection_target = "report"

        def snapshot(self):
            return {
                "current_app": self.current_app,
                "current_target": self.current_target,
            }

        def clear_pending_selection(self):
            return None

    class AgentBoundary:
        def __init__(self):
            self.context = Context()

    monkeypatch.setattr(executor, "tool_manager", ToolBoundary())
    monkeypatch.setattr(executor, "autonomous_agent", AgentBoundary())
    monkeypatch.setattr(
        executor.intent_engine,
        "detect",
        lambda text: {
            "intent": "selection",
            "target": "1",
            "selection": "1",
            "voice": {},
        },
    )
    monkeypatch.setattr(
        executor.goal_router,
        "route",
        lambda command, intent=None: {
            "route": "goal",
            "reason": "forced regression guard",
        },
    )
    monkeypatch.setattr(executor, "_has_pending_selection", lambda: True)
    monkeypatch.setattr(executor.response_engine, "format", lambda **kwargs: "चुना गया")

    result = executor.execute("ek")

    assert calls == [{
        "intent": "unknown",
        "target": "1",
        "voice": {},
    }]
    assert result["success"] is True


def test_close_current_prefers_live_window_over_stale_app_context(monkeypatch):
    calls = []

    class Context:
        current_app = None
        current_file = "report.pdf"
        current_target = "report.pdf"

        def snapshot(self):
            return {
                "current_app": self.current_app,
                "current_file": self.current_file,
                "current_target": self.current_target,
            }

    class MissionRuntime:
        def snapshot(self):
            return {}

    class CapabilityExecutor:
        def execute(self, action):
            calls.append(action)
            return {
                "success": True,
                "stage": "closed",
                "message": "Closed active window",
                "verification": {"verified": True},
            }

    class AgentBoundary:
        context = Context()
        mission_runtime = MissionRuntime()
        capability_executor = CapabilityExecutor()

        class World:
            def snapshot(self, *args, **kwargs):
                return {
                    "current_window": {
                        "hwnd": 321,
                        "title": "Report.pdf - Viewer",
                    }
                }

        world_state = World()

    monkeypatch.setattr(executor, "autonomous_agent", AgentBoundary())
    monkeypatch.setattr(
        executor.intent_engine,
        "detect",
        lambda text: {
            "intent": "close_current",
            "target": "",
            "voice": {},
        },
    )
    monkeypatch.setattr(executor.response_engine, "format", lambda **kwargs: "बंद कर दिया")

    result = executor.execute("close")

    assert result["success"] is True
    assert calls[0]["action"] == "close_application"
    assert calls[0]["target"] == "Report.pdf - Viewer"
    assert calls[0]["args"]["hwnd"] == 321


def test_capability_descriptions_preserve_generic_action_surface():
    gateway = AIReasoningGateway(model_gateway=object())
    result = gateway._capability_descriptions([
        {
            "name": "windows_ui",
            "description": "Generic Windows UI interaction provider.",
            "actions": ["focus_window", "hotkey", "type_text", "keypress"],
            "enabled": True,
        }
    ])
    assert result[0]["actions"] == [
        "focus_window",
        "hotkey",
        "type_text",
        "keypress",
    ]


def test_stt_command_boundary_preserves_original_hindi_transcript():
    stt = SpeechToText.__new__(SpeechToText)
    stt.preferred_language = "hi-IN"
    stt.fallback_language = "en-IN"
    stt.debug = False
    stt.command_normalizer = VoiceCommandNormalizer()
    stt._recognize_error_count = 0
    stt._last_text = ""
    stt._last_raw_text = ""
    stt._last_language = ""
    stt._last_status = ""

    def fake_recognize_one(audio, language, label="STT", show_all=False):
        return {
            "success": True,
            "text": "bharat ki rajadhani kya hai",
            "raw_text": "भारत की राजधानी क्या है",
            "alternatives": ["bharat ki rajadhani kya hai"],
            "language": language,
            "status": "recognized",
        }

    stt._recognize_one = fake_recognize_one
    result = SpeechToText._recognize_command(stt, object())

    assert result["text"] == "bharat ki rajadhani kya hai"
    assert result["raw_text"] == "भारत की राजधानी क्या है"
    assert result["language"] == "hi-IN"


def test_gemini_prompt_contains_generic_ui_continuation_guidance():
    class DummyModel:
        pass

    gateway = AIReasoningGateway(model_gateway=DummyModel())
    # The gateway itself is transport-only; inspect the model gateway prompt
    # contract through the real class without calling the network.
    from ai_core.model_gateway import ModelGateway
    prompt = ModelGateway._system_prompt(ModelGateway.__new__(ModelGateway))
    assert "generic Windows UI" in prompt
    assert "Do not stop after the opening step" in prompt
