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

    def test_resolver_corrects_unique_provider_for_mismatched_capability(self):
        registry = CapabilityRegistry()
        registry.register(
            name="windows_ui",
            description="Generic Windows UI provider.",
            actions=["open_application", "type_text"],
            enabled=True,
            priority=50,
        )
        resolver = CapabilityResolver(registry)
        result = resolver.resolve({
            "action": "open_application",
            "capability": "application_control",
            "target": "Notepad",
        })
        assert result["resolved"] is True
        assert result["capability"] == "windows_ui"
        assert result["stage"] == "capability_resolved_with_correction"


    def test_mission_planner_rejects_partial_plan_when_one_step_is_invalid(self):
        planner = MissionPlanner(max_steps=5)
        plan = planner.plan("open workspace and continue task", analysis={"plan": [
            {"type": "action", "id": "open_1", "action": "open_application", "capability": "windows_ui", "target": "workspace", "args": {}, "depends_on": []},
            {"type": "action", "id": "invalid_2", "capability": "windows_ui", "target": "missing-action-name", "args": {}, "depends_on": ["open_1"]},
        ]})
        self.assertEqual(plan, [])
        self.assertIn("partial plan", planner.last_error)
        self.assertEqual(planner.last_plan, [])

    def test_mission_planner_rejects_over_limit_instead_of_truncating(self):
        planner = MissionPlanner(max_steps=2)
        plan = planner.plan("perform three dependent operations", analysis={"plan": [
            {"type": "action", "id": "a", "action": "first", "capability": "cap"},
            {"type": "action", "id": "b", "action": "second", "capability": "cap"},
            {"type": "action", "id": "c", "action": "third", "capability": "cap"},
        ]})
        self.assertEqual(plan, [])
        self.assertIn("safety limit", planner.last_error)

    def test_mission_planner_rejects_unknown_dependency_before_execution(self):
        planner = MissionPlanner(max_steps=3)
        plan = planner.plan("perform a dependent task", analysis={"plan": [{
            "type": "action", "id": "write", "action": "type_text", "capability": "windows_ui",
            "target": "focused_element", "args": {"text": "hello"}, "depends_on": ["missing_step"],
        }]})
        self.assertEqual(plan, [])
        self.assertIn("unknown id", planner.last_error)

    def test_mission_planner_keeps_valid_dependency_chain_and_contracts(self):
        planner = MissionPlanner(max_steps=3)
        plan = planner.plan("open a target then type text", analysis={"plan": [
            {
                "type": "action", "id": "open_1", "action": "open_application", "capability": "windows_ui",
                "target": "runtime target", "args": {}, "preconditions": ["target is available"],
                "postconditions": ["target window is observed"], "depends_on": [],
            },
            {
                "type": "action", "id": "type_2", "action": "type_text", "capability": "windows_ui",
                "target": "focused_element", "args": {"text": "hello"}, "preconditions": ["target window is observed"],
                "postconditions": ["hello is visible"], "depends_on": ["open_1"],
            },
        ]})
        self.assertEqual([step["id"] for step in plan], ["open_1", "type_2"])
        self.assertEqual(plan[1]["depends_on"], ["open_1"])
        self.assertEqual(plan[0]["preconditions"], ["target is available"])
        self.assertEqual(plan[1]["postconditions"], ["hello is visible"])
        self.assertEqual(planner.last_error, "")


if __name__ == "__main__":
    unittest.main()
