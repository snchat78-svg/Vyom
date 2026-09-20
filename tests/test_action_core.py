import unittest

from ai_core.action_schema import ActionSchema, ActionSchemaError
from ai_core.action_validator import ActionValidator
from ai_core.capability_registry import CapabilityRegistry
from ai_core.capability_resolver import CapabilityResolver
from ai_core.mission_planner import MissionPlanner
from ai_core.reasoning_gateway import AIReasoningGateway


class FakeModelGateway:
    def __init__(self, payload):
        self.payload = payload

    def is_available(self):
        return True

    def complete(self, **kwargs):
        return {"success": True, "available": True, "data": self.payload}


class ActionCoreTests(unittest.TestCase):

    def test_action_schema_accepts_generic_identifier(self):
        action = ActionSchema(
            action="click_control",
            capability="windows_ui",
            target="Submit button",
            args={"x": 12, "y": 34},
            postconditions=["button is activated"],
        )
        self.assertEqual(action.action, "click_control")
        self.assertEqual(action.capability, "windows_ui")


    def test_future_action_name_is_not_hard_coded_in_schema(self):
        action = ActionSchema(
            action="future_operation_xyz",
            capability="future_provider",
        )
        self.assertEqual(action.action, "future_operation_xyz")

    def test_action_schema_rejects_non_identifier_action(self):
        with self.assertRaises(ActionSchemaError):
            ActionSchema(action="Run Python!", capability="windows_ui")

    def test_validator_rejects_executable_payload(self):
        validator = ActionValidator(max_steps=5)
        result = validator.validate_action({
            "action": "click_control",
            "capability": "windows_ui",
            "args": {"python": "print('unsafe')"},
        })
        self.assertFalse(result["valid"])
        self.assertIn("forbidden", result["error"])

    def test_validator_rejects_nested_executable_payload(self):
        validator = ActionValidator(max_steps=5)
        result = validator.validate_action({
            "action": "click_control",
            "capability": "windows_ui",
            "args": {"options": {"code": "print('unsafe')"}},
        })
        self.assertFalse(result["valid"])
        self.assertIn("forbidden", result["error"])

    def test_validator_detects_dependency_cycle(self):
        validator = ActionValidator(max_steps=5)
        result = validator.validate_plan([
            {"id": "a", "action": "first", "capability": "cap", "depends_on": ["b"]},
            {"id": "b", "action": "second", "capability": "cap", "depends_on": ["a"]},
        ])
        self.assertFalse(result["valid"])
        self.assertIn("dependency cycle", result["error"])

    def test_capability_registry_is_dynamic(self):
        registry = CapabilityRegistry()
        self.assertTrue(registry.register(
            "custom_device",
            "A custom provider",
            actions=["press_symbol"],
        ))
        resolver = CapabilityResolver(registry)
        result = resolver.resolve({
            "action": "press_symbol",
            "capability": "custom_device",
            "target": "A",
        })
        self.assertTrue(result["resolved"])
        self.assertEqual(result["capability"], "custom_device")

    def test_gateway_accepts_generic_action_without_fixed_intent_allowlist(self):
        payload = {
            "understood": True,
            "goal": "Click the save control",
            "language": "english",
            "complexity": "simple",
            "analysis": "A generic UI action is required.",
            "route": "capability",
            "capability": "windows_ui",
            "plan": [{
                "step": 1,
                "type": "action",
                "id": "action_1",
                "action": "click_control",
                "capability": "windows_ui",
                "target": "Save",
                "args": {"button": "left"},
                "preconditions": ["window is focused"],
                "postconditions": ["save operation is triggered"],
                "depends_on": [],
            }],
        }
        result = AIReasoningGateway(FakeModelGateway(payload)).reason(payload["goal"])
        self.assertTrue(result["success"])
        step = result["data"]["plan"][0]
        self.assertEqual(step["action"], "click_control")
        self.assertEqual(step["capability"], "windows_ui")

    def test_gateway_keeps_legacy_intent_format_for_compatibility(self):
        payload = {
            "understood": True,
            "goal": "open notepad",
            "language": "english",
            "complexity": "simple",
            "route": "existing_tools",
            "capability": "",
            "plan": [{
                "type": "execute_existing_intent",
                "intent": {"intent": "open", "target": "notepad"},
            }],
        }
        result = AIReasoningGateway(FakeModelGateway(payload)).reason(payload["goal"])
        self.assertTrue(result["success"])
        self.assertEqual(result["data"]["plan"][0]["intent"]["intent"], "open")

    def test_mission_planner_normalizes_generic_action(self):
        planner = MissionPlanner(max_steps=5)
        plan = planner.plan(
            "click save",
            analysis={"plan": [{
                "type": "action",
                "id": "save_1",
                "action": "click_control",
                "capability": "windows_ui",
                "target": "Save",
                "args": {"button": "left"},
            }]},
        )
        self.assertEqual(len(plan), 1)
        self.assertEqual(plan[0]["type"], "action")
        self.assertEqual(plan[0]["action"], "click_control")


if __name__ == "__main__":
    unittest.main()
