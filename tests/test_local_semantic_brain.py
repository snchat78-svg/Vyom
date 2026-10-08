from ai_core.deep_reasoner import DeepReasoner
from ai_core.semantic_brain import LocalSemanticBrain


class _Gateway:
    def __init__(self, available=True):
        self.available = available
        self.calls = 0

    def is_available(self):
        return self.available

    def reason(self, **_kwargs):
        self.calls += 1
        return {
            "success": True,
            "available": True,
            "data": {
                "route": "conversation",
                "plan": [],
            },
        }

    def reset(self):
        self.calls = 0


def test_local_brain_understands_roman_hindi_search_without_site_aliases():
    brain = LocalSemanticBrain()
    result = brain.reason(
        "isamen yutyub sarch karo",
        context={
            "current_window": {
                "title": "New Tab",
                "class_name": "Chrome_WidgetWin_1",
            },
            "current_app": "gugal krom",
        },
    )

    assert result["route"] == "mission"
    assert [step["action"] for step in result["plan"]] == [
        "hotkey",
        "type_text",
        "keypress",
    ]
    assert result["plan"][1]["args"]["text"] == "yutyub"


def test_local_brain_preserves_devanagari_text_as_user_data():
    brain = LocalSemanticBrain()
    result = brain.reason(
        "इसमें शंभू लाल लिखो",
        context={
            "current_app": "text editor",
            "current_target": "text editor",
        },
    )

    assert result["route"] == "capability"
    step = result["plan"][0]
    assert step["action"] == "type_text"
    assert step["args"]["text"] == "शंभू लाल"


def test_local_brain_keeps_compound_goal_order():
    brain = LocalSemanticBrain()
    result = brain.reason(
        "open my text editor and type Shambhu Lal",
        context={},
    )

    assert result["route"] == "mission"
    assert [step["type"] for step in result["plan"]] == [
        "execute_existing_intent",
        "action",
    ]
    assert result["plan"][1]["action"] == "type_text"
    assert result["plan"][1]["args"]["text"] == "Shambhu Lal"
    assert result["plan"][1]["depends_on"] == [result["plan"][0]["id"]]


def test_local_brain_resolves_follow_up_reference_from_context():
    brain = LocalSemanticBrain()
    result = brain.reason(
        "ye wala kholo",
        context={
            "current_target": "Current Document",
            "current_app": "",
            "current_file": "",
        },
    )

    assert result["route"] == "capability"
    assert result["plan"][0]["action"] == "open_application"
    assert result["plan"][0]["target"] == "Current Document"


def test_local_brain_does_not_guess_numbered_instance():
    brain = LocalSemanticBrain()
    result = brain.reason(
        "notapaid number 1",
        context={
            "current_app": "notapaid",
            "current_target": "notapaid",
        },
    )

    assert result["route"] == "clarification"
    assert result["plan"] == []
    assert result["unresolved_parts"] == ["notapaid number 1"]


def test_deep_reasoner_prefers_local_semantic_brain_before_model():
    gateway = _Gateway(available=True)
    reasoner = DeepReasoner(
        model_gateway=gateway,
        reasoning_gateway=gateway,
    )

    result = reasoner.reason(
        "isamen yutyub sarch karo",
        context={
            "current_window": {
                "title": "New Tab",
                "class_name": "Chrome_WidgetWin_1",
            },
        },
    )

    assert result["success"] is True
    assert result["source"] == "local_semantic_brain"
    assert result["data"]["source"] == "local_semantic_brain"
    assert gateway.calls == 0


def test_deep_reasoner_local_brain_works_with_no_model():
    gateway = _Gateway(available=False)
    reasoner = DeepReasoner(
        model_gateway=gateway,
        reasoning_gateway=gateway,
    )

    result = reasoner.reason(
        "open my text editor and type नमस्ते",
        context={},
    )

    assert result["success"] is True
    assert result["source"] == "local_semantic_brain"
    assert result["data"]["route"] == "mission"
    assert gateway.calls == 0


def test_local_brain_understands_natural_typing_without_context():
    brain = LocalSemanticBrain()
    result = brain.reason(
        "shambhu lal likho",
        context={},
    )

    assert result["route"] == "capability"
    assert result["plan"][0]["action"] == "type_text"
    assert result["plan"][0]["args"]["text"] == "shambhu lal"


def test_local_brain_understands_natural_ui_click():
    brain = LocalSemanticBrain()
    result = brain.reason(
        "search box click karo",
        context={},
    )

    assert result["route"] == "capability"
    assert result["plan"][0]["action"] == "click_ui_element"
    assert result["plan"][0]["target"] == "search box"


def test_local_brain_understands_window_controls():
    brain = LocalSemanticBrain()
    result = brain.reason(
        "window maximize karo",
        context={},
    )

    assert result["route"] == "capability"
    assert result["plan"][0]["action"] == "hotkey"
    assert result["plan"][0]["args"]["keys"] == ["win", "up"]


def test_local_brain_resolves_pending_selection_number():
    brain = LocalSemanticBrain()
    result = brain.reason(
        "number 1",
        context={
            "pending_selection": True,
            "selection_options": [
                {"name": "Example Application", "path": "Example Application"},
                {"name": "Other Application", "path": "Other Application"},
            ],
        },
    )

    assert result["route"] == "capability"
    assert result["plan"][0]["action"] == "open_application"
    assert result["plan"][0]["target"] == "Example Application"
