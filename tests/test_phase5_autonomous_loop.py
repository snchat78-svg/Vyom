import unittest

from ai_core.autonomous_agent import AutonomousAgent
from ai_core.mission_runtime import MissionRuntime


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
        self.assertFalse(
            any(
                item.get("stage") == "observation"
                for item in agent.task_history
                if isinstance(item, dict)
            )
        )
        self.assertTrue(agent.world_state.observation_history)
        self.assertEqual(
            agent.world_state.observation_history[-1]["phase"],
            "test",
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


    def test_replan_reuses_verified_logical_step_with_new_id(self):
        runtime = MissionRuntime(max_retries=1, max_steps=5)
        runtime.start(
            goal="open and type",
            plan=[
                {
                    "step": 1,
                    "id": "old_open",
                    "type": "action",
                    "action": "open_application",
                    "capability": "windows_ui",
                    "target": "Notepad",
                    "args": {},
                    "depends_on": [],
                    "status": "pending",
                },
                {
                    "step": 2,
                    "id": "old_type",
                    "type": "action",
                    "action": "type_text",
                    "capability": "windows_ui",
                    "target": "Hello",
                    "args": {"text": "Hello"},
                    "depends_on": ["old_open"],
                    "status": "pending",
                },
            ],
        )
        runtime.get_next_step()
        runtime.mark_completed(
            "old_open",
            result={"success": True},
            verification={"verified": True},
        )

        self.assertTrue(
            runtime.apply_replan([
                {
                    "step": 10,
                    "id": "new_open",
                    "type": "action",
                    "action": "open_application",
                    "capability": "windows_ui",
                    "target": "Notepad",
                    "args": {},
                    "depends_on": [],
                },
                {
                    "step": 11,
                    "id": "new_type",
                    "type": "action",
                    "action": "type_text",
                    "capability": "windows_ui",
                    "target": "Hello",
                    "args": {"text": "Hello"},
                    "depends_on": ["new_open"],
                },
            ])
        )

        self.assertEqual(runtime.plan[0]["status"], "completed")
        self.assertEqual(runtime.plan[0]["reused_verified_step_id"], "old_open")
        self.assertEqual(runtime.get_next_step()["id"], "new_type")


if __name__ == "__main__":
    unittest.main()
