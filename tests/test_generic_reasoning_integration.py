import unittest

from ai_core.reasoning_engine import ReasoningEngine


class FakeDeepReasoner:
    def __init__(self, payload):
        self.payload = payload
        self.calls = 0

    def is_available(self):
        return True

    def reason(self, **kwargs):
        self.calls += 1
        return {"success": True, "available": True, "data": self.payload}

    def reset(self):
        self.calls = 0


class GenericReasoningIntegrationTests(unittest.TestCase):

    def test_generic_action_remains_generic_and_is_not_converted_to_intent(self):
        deep = FakeDeepReasoner({
            "understood": True,
            "goal": "click save",
            "language": "english",
            "complexity": "complex",
            "route": "mission",
            "capability": "windows_ui",
            "plan": [{
                "type": "action",
                "id": "a1",
                "action": "click_control",
                "capability": "windows_ui",
                "target": "Save",
                "args": {"button": "left"},
            }],
        })
        engine = ReasoningEngine(deep_reasoner=deep)
        result = engine.reason("click save button")

        self.assertTrue(result["success"])
        self.assertEqual(result["route"]["route"], "missing_capability")
        self.assertEqual(result["analysis"]["generic_actions"][0]["action"], "click_control")
        self.assertNotIn("intent", result["analysis"]["generic_actions"][0])
        self.assertEqual(result["plan"][0]["type"], "request_new_capability")
        self.assertEqual(result["plan"][0]["required_actions"][0]["action"], "click_control")

    def test_registered_capability_resolves_generic_action(self):
        deep = FakeDeepReasoner({
            "understood": True,
            "goal": "click save",
            "language": "english",
            "complexity": "complex",
            "route": "mission",
            "capability": "windows_ui",
            "plan": [{
                "type": "action",
                "id": "a1",
                "action": "click_control",
                "capability": "windows_ui",
                "target": "Save",
            }],
        })
        engine = ReasoningEngine(deep_reasoner=deep)
        engine.capability_registry.register(
            name="windows_ui",
            description="Windows UI provider",
            actions=["click_control"],
            enabled=True,
        )

        result = engine.reason("click save button")

        self.assertTrue(result["success"])
        self.assertEqual(result["route"]["route"], "capability")
        self.assertEqual(result["route"]["capability"], "windows_ui")
        self.assertEqual(result["plan"][0]["type"], "action")
        self.assertEqual(result["plan"][0]["action"], "click_control")

    def test_mixed_legacy_and_generic_plan_preserves_order(self):
        deep = FakeDeepReasoner({
            "understood": True,
            "goal": "open app then click",
            "language": "english",
            "complexity": "complex",
            "route": "mission",
            "capability": "windows_ui",
            "plan": [
                {
                    "type": "execute_existing_intent",
                    "intent": {"intent": "open", "target": "some app"},
                },
                {
                    "type": "action",
                    "id": "a2",
                    "action": "click",
                    "capability": "windows_ui",
                    "target": "",
                    "args": {"x": 10, "y": 20},
                },
            ],
        })
        engine = ReasoningEngine(deep_reasoner=deep)
        engine.capability_registry.register(
            name="windows_ui",
            description="Windows UI provider",
            actions=["click"],
            enabled=True,
        )
        result = engine.reason("open some app then click at 10 20")

        self.assertTrue(result["success"])
        self.assertEqual(result["route"]["route"], "mission")
        self.assertEqual(
            [step["type"] for step in result["plan"]],
            ["execute_existing_intent", "action"],
        )

    def test_legacy_fast_path_remains_unchanged(self):
        deep = FakeDeepReasoner({"should": "not be called"})
        engine = ReasoningEngine(deep_reasoner=deep)
        result = engine.reason("open calculator")

        self.assertTrue(result["success"])
        self.assertEqual(result["route"]["route"], "existing_tools")
        self.assertEqual(deep.calls, 0)
        self.assertEqual(result["plan"][0]["intent"]["intent"], "open")


if __name__ == "__main__":
    unittest.main()
