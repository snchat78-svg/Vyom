import types

from command_engine import executor
from ai_core.deep_reasoner import DeepReasoner
from ai_core.reasoning_engine import ReasoningEngine
from ai_core.context_action_compiler import ContextActionCompiler


def test_semantic_failure_is_not_relabelled_as_success(monkeypatch):
    class AgentBoundary:
        context = types.SimpleNamespace(snapshot=lambda: {})

        def run(self, goal, intent):
            return {
                "success": False,
                "stage": "skill_planned",
                "message": "capability preparation only",
            }

    monkeypatch.setattr(executor, "autonomous_agent", AgentBoundary())
    monkeypatch.setattr(
        executor.intent_engine,
        "detect",
        lambda text: {"intent": "unknown", "target": text},
    )

    result = executor.execute("bharat ki rajadhani kya hai")
    assert isinstance(result, dict)
    assert result["success"] is False
    assert result["stage"] == "skill_planned"


def test_number_is_not_selection_without_pending_context(monkeypatch):
    calls = []

    class AgentBoundary:
        context = types.SimpleNamespace(snapshot=lambda: {})

        def run(self, goal, intent):
            calls.append((goal, intent))
            return {
                "success": True,
                "stage": "conversation",
                "message": "semantic path",
            }

    monkeypatch.setattr(executor, "autonomous_agent", AgentBoundary())

    original_detect = executor.intent_engine.detect
    def detect(text):
        return {
            "intent": "selection",
            "target": "1",
            "selection": "1",
            "voice": {},
        }

    monkeypatch.setattr(executor.intent_engine, "detect", detect)
    monkeypatch.setattr(executor, "_has_pending_selection", lambda: False)

    result = executor.execute("number 1 open karo")

    assert calls == [(
        "number 1 open karo",
        {
            "intent": "unknown",
            "target": "number 1 open karo",
            "voice": {},
        },
    )]
    assert result["success"] is True

    monkeypatch.setattr(executor.intent_engine, "detect", original_detect)


def test_context_compiler_handles_stt_locative_form():
    result = ContextActionCompiler().compile(
        "isamen shanbhu lal type",
        context={"current_app": "Notepad", "current_target": "Notepad"},
    )
    assert result["complete"] is True
    assert result["plan"][0]["action"] == "type_text"
    assert result["plan"][0]["args"]["text"] == "shanbhu lal"


def test_offline_information_question_does_not_request_a_new_skill():
    engine = ReasoningEngine()
    result = engine.reason("bharat ki rajadhani kya hai")
    assert result["route"]["route"] == "conversation"


def test_deep_reasoner_question_classifier_is_language_only():
    reasoner = DeepReasoner()
    assert reasoner._looks_like_information_question("what is this")
    assert reasoner._looks_like_information_question("bharat ki rajadhani kya hai")
    assert reasoner._looks_like_information_question("tumhara naam kya hai")
    assert not reasoner._looks_like_information_question("number 1 open karo")
