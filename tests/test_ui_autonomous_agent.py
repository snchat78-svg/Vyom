import types
import unittest

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
        if provider is None:
            return {
                "success": False,
                "stage": "capability_runtime_missing",
                "message": "Test provider was not registered.",
            }
        return provider.execute(action)


class UIAutonomousAgentTests(unittest.TestCase):
    def make_agent(self):
        # Use the real AutonomousAgent base. Only the provider/executor and
        # validator used by this unit test are substituted. This keeps the
        # test isolated without modifying sys.modules for other tests.
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
