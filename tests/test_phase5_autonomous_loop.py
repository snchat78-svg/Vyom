import unittest

from ai_core.autonomous_agent import AutonomousAgent


class Phase5ObservationTests(unittest.TestCase):
    def test_observation_boundary_is_serializable_and_recorded(self):
        agent = AutonomousAgent(max_steps=3)
        observation = agent._observe_cycle(
            phase="test",
            step={"id": "a1", "type": "action"},
            result={"success": True},
            verification={"verified": True},
        )
        self.assertEqual(observation["phase"], "test")
        self.assertEqual(observation["step_id"], "a1")
        self.assertIn("world_state", observation)
        self.assertTrue(
            any(
                item.get("stage") == "observation"
                for item in agent.task_history
                if isinstance(item, dict)
            )
        )

    def test_observation_failure_does_not_execute_or_mutate_targets(self):
        agent = AutonomousAgent(max_steps=3)
        observation = agent._observe_cycle(
            phase="before_action",
            step={"id": "a1", "type": "action", "target": "Search"},
        )
        self.assertEqual(observation["step_id"], "a1")
        self.assertEqual(
            observation["world_state"]["current_target"],
            "",
        )


if __name__ == "__main__":
    unittest.main()
