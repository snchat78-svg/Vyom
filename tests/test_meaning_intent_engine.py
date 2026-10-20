"""M2 acceptance tests for the structured meaning frame."""

from ai_core.meaning_intent_engine import MeaningIntentEngine


def test_generic_ui_target_is_preserved_separately_from_payload_and_constraints():
    result = {
        "route": "mission",
        "confidence": 0.91,
        "plan": [
            {
                "type": "action",
                "action": "click",
                "target": "Save",
                "args": {},
                "preconditions": ["the dialog is visible"],
                "postconditions": ["the dialog closes"],
                "metadata": {
                    "verification": {
                        "checks": [{
                            "kind": "window_change",
                            "source": "uia",
                            "field": "active_window",
                            "operator": "changed",
                            "value": True,
                        }]
                    }
                },
            },
            {
                "type": "action",
                "action": "type_text",
                "target": "focused_element",
                "args": {"text": "Quarterly report"},
                "preconditions": ["the destination field is focused"],
                "postconditions": ["the requested text appears"],
            },
        ],
    }

    frame = MeaningIntentEngine().analyze(
        "click Save, then type Quarterly report in it",
        result,
    )

    assert frame["schema_version"] == "m2.1"
    assert frame["intent"]["kind"] == "computer_action"
    assert frame["intent"]["operations"] == ["click", "type_text"]
    assert frame["entities"]["targets"] == ["Save"]
    assert frame["payloads"] == [{
        "kind": "text",
        "value": "Quarterly report",
        "step": 2,
    }]
    assert frame["constraints"]["preconditions"] == [
        "the dialog is visible",
        "the destination field is focused",
    ]
    assert frame["constraints"]["postconditions"] == [
        "the dialog closes",
        "the requested text appears",
    ]
    assert frame["constraints"]["verification_checks"] == [{
        "kind": "window_change",
        "source": "uia",
        "field": "active_window",
        "operator": "changed",
        "value": True,
    }]
    assert frame["references"] == ["in it"]
    assert "verification checks" in frame["desired_result"]


def test_competing_runtime_targets_are_exposed_as_alternatives_not_selected_entities():
    result = {
        "route": "clarification",
        "confidence": 0.42,
        "plan": [],
    }
    recovery = {
        "ambiguities": [{
            "kind": "runtime_target",
            "operation": "open",
            "observed": "calclulator",
            "candidates": [
                {"value": "Calculator", "confidence": 0.91},
                {"value": "Calculater", "confidence": 0.89},
            ],
        }],
    }

    frame = MeaningIntentEngine().analyze(
        "open calclulator",
        result,
        recovery=recovery,
    )

    assert frame["requires_clarification"] is True
    assert frame["intent"]["kind"] == "clarification"
    assert frame["entities"]["targets"] == []
    assert [item["target"] for item in frame["entities"]["target_candidates"]] == [
        "Calculator", "Calculater",
    ]
    assert [item["status"] for item in frame["hypotheses"]] == [
        "competing_target", "competing_target",
    ]
    assert "before dispatching" in frame["desired_result"]


def test_surface_paraphrases_with_the_same_plan_produce_the_same_structured_goal():
    plan = [{
        "type": "action",
        "action": "open_application",
        "target": "Calculator",
        "args": {},
        "preconditions": ["application is available"],
        "postconditions": ["calculator window is visible"],
    }]
    engine = MeaningIntentEngine()
    first = engine.analyze(
        "open Calculator",
        {"route": "capability", "confidence": 0.88, "plan": plan},
    )
    second = engine.analyze(
        "launch Calculator",
        {"route": "capability", "confidence": 0.88, "plan": plan},
    )

    for field in (
        "intent", "entities", "payloads", "constraints",
        "desired_result", "hypotheses", "requires_clarification",
    ):
        assert first[field] == second[field]
