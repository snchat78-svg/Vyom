import unittest
import types

from ai_core.goal_compiler import GoalCompiler
from ai_core.reasoning_engine import ReasoningEngine
from ai_core.ui_autonomous_agent import UIAutonomousAgent
from ai_core.result_schema import normalize_result


class FakeReasoningEngine:
    def __init__(self):
        self.goal_compiler = GoalCompiler()
        self.capability_registry = types.SimpleNamespace()
        self.action_validator = types.SimpleNamespace(
            validate_action=lambda action, index=1: {
                "valid": True,
                "action": dict(action),
            }
        )

    def reason(self, *args, **kwargs):
        return {
            "success": True,
            "analysis": {"goal": str(args[0]) if args else ""},
            "route": {
                "route": "capability",
                "capability": "windows_ui",
            },
            "plan": [{
                "step": 1,
                "id": "a1",
                "type": "action",
                "action": "click",
                "capability": "windows_ui",
                "target": "Save",
                "args": {},
                "depends_on": [],
                "status": "pending",
            }],
        }

    def reset(self):
        return None


class FakeCapabilityExecutor:
    def execute(self, action):
        return {
            "success": True,
            "stage": "clicked",
            "message": "clicked",
            "verification": {
                "verified": True,
                "verification_level": "test",
            },
        }


class Phase1ContractTests(unittest.TestCase):

    def test_autonomous_agent_reuses_reasoning_engine_goal_compiler(self):
        from ai_core.autonomous_agent import AutonomousAgent

        engine = ReasoningEngine()
        agent = AutonomousAgent(reasoning_engine=engine)

        self.assertIs(agent.goal_compiler, engine.goal_compiler)

    def test_ui_agent_uses_reasoning_engine_capability_registry(self):
        engine = ReasoningEngine()
        agent = UIAutonomousAgent(reasoning_engine=engine)

        self.assertIs(agent.capability_executor.registry, engine.capability_registry)
        self.assertIs(agent.capability_executor.resolver.registry, engine.capability_registry)

    def test_resolved_capability_route_reaches_generic_action_executor(self):
        engine = FakeReasoningEngine()
        agent = UIAutonomousAgent(reasoning_engine=engine, max_steps=3)
        agent.capability_executor = FakeCapabilityExecutor()

        result = agent.run("click Save")

        self.assertTrue(result["success"])
        self.assertEqual(result["stage"], "verified")
        self.assertEqual(result["history"][0]["type"], "action")
        self.assertTrue(result["history"][0]["verified"])

    def test_canonical_result_schema_preserves_existing_fields(self):
        result = normalize_result({
            "success": True,
            "stage": "verified",
            "message": "Done",
            "custom_field": "preserved",
        })

        self.assertTrue(result["success"])
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["stage"], "verified")
        self.assertEqual(result["custom_field"], "preserved")
        self.assertIn("error", result)
        self.assertIn("error_category", result)


if __name__ == "__main__":
    unittest.main()
