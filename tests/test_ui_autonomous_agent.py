import sys
import types
import unittest


# Keep this unit test independent from the full Windows/tool stack. The real
# integration is exercised by command_engine.executor and PyInstaller; this
# test verifies that the Step 2 subclass preserves the base execution
# contract while intercepting only generic action steps.
base_module = types.ModuleType("ai_core.autonomous_agent")


class FakeBaseAutonomousAgent:
    def __init__(self, tool_manager=None, brain=None, reasoning_engine=None, max_steps=10):
        class Context:
            def record_action(self, item):
                self.action = item

            def record_result(self, result, success):
                self.result = result
                self.success = success

        self.context = Context()
        self.reasoning_engine = reasoning_engine or types.SimpleNamespace(
            action_validator=None,
            capability_registry=None,
        )
        self.max_steps = max(1, int(max_steps))
        self.step_count = 0
        self.task_history = []

    def _execute_step(self, step):
        return {"success": False, "stage": "invalid_intent", "step": step}


base_module.AutonomousAgent = FakeBaseAutonomousAgent
sys.modules["ai_core.autonomous_agent"] = base_module

from ai_core.ui_autonomous_agent import UIAutonomousAgent


class FakeProvider:
    name = "windows_ui"
    description = "Test provider"

    def supported_actions(self):
        return ["click"]

    def execute(self, action):
        return {
            "success": True,
            "stage": "mouse_clicked",
            "result": {"ok": True},
            "verification": {"verified": True, "verification_level": "dispatch"},
        }


class FakeExecutor:
    def __init__(self):
        self.providers = {}

    def register(self, provider, enabled=True, priority=100):
        self.providers[provider.name] = provider
        return True

    def unregister(self, name):
        self.providers.pop(name, None)

    def execute(self, action):
        provider = self.providers.get(action["capability"])
        return provider.execute(action)


class UIAutonomousAgentTests(unittest.TestCase):
    def make_agent(self):
        agent = UIAutonomousAgent(max_steps=3)
        agent.capability_executor = FakeExecutor()
        agent.action_validator = types.SimpleNamespace(
            validate_action=lambda action, index=1: {"valid": True, "action": dict(action)}
        )
        agent.capability_executor.register(FakeProvider())
        return agent

    def test_generic_action_execution_path_exists(self):
        agent = self.make_agent()

        result = agent._execute_step({
            "type": "action",
            "id": "a1",
            "action": "click",
            "capability": "windows_ui",
            "target": "",
            "args": {},
        })

        self.assertTrue(result["success"])
        self.assertEqual(result["stage"], "verified")
        self.assertEqual(agent.step_count, 1)
        self.assertEqual(agent.task_history[-1]["type"], "action")

    def test_legacy_steps_are_delegated_to_base(self):
        agent = self.make_agent()
        result = agent._execute_step({"type": "execute_existing_intent"})
        self.assertFalse(result["success"])
        self.assertEqual(result["stage"], "invalid_intent")


if __name__ == "__main__":
    unittest.main()
