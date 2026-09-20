import sys
import types
import unittest


def install_stubs():
    goal_compiler = types.ModuleType("ai_core.goal_compiler")

    class GoalCompiler:
        def compile(self, goal, intent=None, context=None):
            text = str(goal).lower()
            if "calculator" in text and "and" not in text:
                return {
                    "success": True,
                    "understood": True,
                    "objective": goal,
                    "complexity": "simple",
                    "suggested_intents": [{"intent": "open", "target": "calculator"}],
                    "sub_goals": [{"step": 1, "goal": goal}],
                    "reason": "deterministic",
                }
            return {
                "success": True,
                "understood": True,
                "objective": goal,
                "complexity": "complex",
                "suggested_intents": [],
                "sub_goals": [{"step": 1, "goal": goal}, {"step": 2, "goal": "follow up"}],
                "reason": "delegated",
            }

    goal_compiler.GoalCompiler = GoalCompiler
    sys.modules["ai_core.goal_compiler"] = goal_compiler

    capability_manager = types.ModuleType("ai_core.capability_manager")

    class CapabilityManager:
        def match(self, goal):
            return []

    capability_manager.CapabilityManager = CapabilityManager
    sys.modules["ai_core.capability_manager"] = capability_manager

    deep_reasoner = types.ModuleType("ai_core.deep_reasoner")

    class DeepReasoner:
        def is_available(self):
            return False

        def reset(self):
            pass

    deep_reasoner.DeepReasoner = DeepReasoner
    sys.modules["ai_core.deep_reasoner"] = deep_reasoner


install_stubs()

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
        self.assertEqual(result["plan"][0]["type"], "use_capability")

    def test_mixed_legacy_and_generic_plan_never_partially_executes(self):
        deep = FakeDeepReasoner({
            "understood": True,
            "goal": "open app then click",
            "language": "english",
            "complexity": "complex",
            "route": "mission",
            "plan": [
                {
                    "type": "execute_existing_intent",
                    "intent": {"intent": "open", "target": "notepad"},
                },
                {
                    "type": "action",
                    "id": "a2",
                    "action": "click_control",
                    "capability": "windows_ui",
                    "target": "Save",
                },
            ],
        })
        engine = ReasoningEngine(deep_reasoner=deep)
        result = engine.reason("open notepad then click save")

        self.assertTrue(result["success"])
        self.assertNotEqual(result["route"]["route"], "mission")
        self.assertEqual(result["route"]["route"], "missing_capability")
        self.assertEqual(result["plan"][0]["type"], "request_new_capability")

    def test_legacy_fast_path_remains_unchanged(self):
        deep = FakeDeepReasoner({"should": "not be called"})
        engine = ReasoningEngine(deep_reasoner=deep)
        result = engine.reason("calculator")

        self.assertTrue(result["success"])
        self.assertEqual(result["route"]["route"], "existing_tools")
        self.assertEqual(deep.calls, 0)
        self.assertEqual(result["plan"][0]["intent"]["intent"], "open")


if __name__ == "__main__":
    unittest.main()
