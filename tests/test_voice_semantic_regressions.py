"""Regression tests for slow knowledge turns and natural voice goals."""

import time

from ai_core.response_engine import ResponseEngine
from ai_core.semantic_brain import LocalSemanticBrain
from ai_core.web_knowledge import WebKnowledge
from command_engine.intent import IntentEngine


def test_truncated_location_question_prompts_for_clarification():
    intent = IntentEngine().detect("rajasthan men")

    assert intent["intent"] == "conversation"
    assert intent["conversation_type"] == "clarification"


def test_roman_hindi_district_and_animal_terms_normalize_for_search():
    district = WebKnowledge._query_variants("rajasthan men kitane jile hain")
    animal = WebKnowledge._query_variants("rajasthan ka rajy pashu kaun sa hai")

    assert district[0] == "राजस्थान में कितने जिले हैं"
    assert animal[0] == "राजस्थान का राज्य पशु कौन सा है"


def test_expired_web_lookup_deadline_does_not_start_another_request():
    calls = []

    def opener(*_args, **_kwargs):
        calls.append(True)
        raise AssertionError("No request should start after the deadline.")

    client = WebKnowledge(opener=opener)
    client._deadline = time.monotonic() - 1
    try:
        client._read_url("https://example.com")
        assert False, "Expected a deadline timeout."
    except TimeoutError:
        pass

    assert calls == []


def test_information_question_uses_web_lookup_without_remote_chat_model():
    class Knowledge:
        def __init__(self):
            self.calls = []

        def answer(self, question, preferred_language="hi"):
            self.calls.append((question, preferred_language))
            return {
                "success": True,
                "answer": "वेबसाइट से मिला उत्तर।\\nस्रोत: परीक्षण स्रोत",
                "source": {
                    "title": "परीक्षण स्रोत",
                    "url": "https://example.com/source",
                    "site": "test",
                },
            }

    knowledge = Knowledge()
    response = ResponseEngine(knowledge_lookup=knowledge)
    answer = response.format(
        command="rajasthan men kitane jile hain",
        result={"success": True, "stage": "conversation"},
        intent={"intent": "unknown"},
    )

    assert "वेबसाइट से मिला उत्तर" in answer
    assert knowledge.calls == [("rajasthan men kitane jile hain", "hi")]


def test_calculator_compound_request_becomes_ordered_ui_mission():
    brain = LocalSemanticBrain()
    result = brain.reason(
        "kailakuletar open karo aur 25 aur 25 joro",
        context={},
    )

    assert result["route"] == "mission"
    steps = result["plan"]
    assert [step["action"] for step in steps] == [
        "open_application",
        "wait",
        "type_text",
        "keypress",
    ]
    assert steps[0]["target"] == "kailakuletar"
    assert steps[2]["args"]["text"] == "25+25"
    assert steps[3]["args"]["key"] == "enter"
    assert steps[1]["depends_on"] == [steps[0]["id"]]
    assert steps[2]["depends_on"] == [steps[1]["id"]]
    assert steps[3]["depends_on"] == [steps[2]["id"]]


def test_incomplete_calculator_expression_is_not_executed_as_a_guess():
    brain = LocalSemanticBrain()
    result = brain.reason(
        "kailakuletar open karo aur 25 + 25 +",
        context={},
    )

    assert not (
        result.get("route") == "mission"
        and any(step.get("action") == "keypress" for step in result.get("plan", []))
    )

def test_opening_a_button_routes_to_generic_ui_automation():
    intent = IntentEngine().detect("pavar batan kholo")
    assert intent["intent"] == "unknown"
    assert intent["semantic_handoff_reason"] == "ui_control_target"

    result = LocalSemanticBrain().reason("pavar batan kholo", context={})
    assert result["route"] == "capability"
    assert result["plan"][0]["action"] == "invoke_ui_element"
    assert result["plan"][0]["target"] == "power button"


def test_existing_application_open_fast_path_is_preserved():
    intent = IntentEngine().detect("notepad kholo")
    assert intent["intent"] == "open"
    assert intent["target"] == "notepad"
