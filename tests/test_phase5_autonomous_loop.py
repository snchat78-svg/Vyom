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


    def test_runtime_rejects_malformed_start_plan_without_dropping_steps(self):
        runtime = MissionRuntime(max_steps=4)
        snapshot = runtime.start("open then type", [
            {"id": "open", "type": "action", "action": "open_application", "capability": "windows_ui", "target": "editor", "depends_on": []},
            None,
            {"id": "type", "type": "action", "action": "type_text", "capability": "windows_ui", "target": "focused_element", "args": {"text": "hello"}, "depends_on": ["open"]},
        ])
        self.assertEqual(snapshot["mission_state"], "blocked")
        self.assertEqual(snapshot["plan"], [])
        self.assertIn("not an object", snapshot["last_error"])
        self.assertIsNone(runtime.get_next_step())

    def test_runtime_never_trusts_precompleted_status_on_fresh_start(self):
        runtime = MissionRuntime(max_steps=3)
        runtime.start("one task", [{
            "id": "claimed_done",
            "type": "action",
            "action": "type_text",
            "capability": "windows_ui",
            "target": "focused_element",
            "args": {"text": "hello"},
            "depends_on": [],
            "status": "completed",
            "result": {"success": True},
            "verification": {"verified": True},
        }])
        self.assertEqual(runtime.plan[0]["status"], "pending")
        self.assertIsNone(runtime.plan[0].get("verification"))
        self.assertEqual(runtime.get_next_step()["id"], "claimed_done")

    def test_unverified_step_completion_cannot_unlock_dependent_step(self):
        runtime = MissionRuntime(max_retries=0, max_steps=3)
        runtime.start("open then type", [
            {"id": "open", "type": "action", "action": "open_application", "capability": "windows_ui", "target": "editor", "depends_on": []},
            {"id": "type", "type": "action", "action": "type_text", "capability": "windows_ui", "target": "focused_element", "args": {"text": "hello"}, "depends_on": ["open"]},
        ])
        self.assertEqual(runtime.get_next_step()["id"], "open")
        self.assertFalse(runtime.mark_completed("open", result={"success": True}, verification={"verified": False}))
        self.assertNotEqual(runtime.plan[0]["status"], "completed")
        self.assertTrue(runtime.needs_replan())
        self.assertIsNone(runtime.get_next_step())
        self.assertEqual(runtime.plan[1]["status"], "pending")

    def test_replan_rejects_unknown_dependency_atomically(self):
        runtime = MissionRuntime(max_retries=0, max_steps=4)
        runtime.start("open and type", [
            {"id": "open", "type": "action", "action": "open_application", "capability": "windows_ui", "target": "editor", "depends_on": []},
        ])
        original = [dict(item) for item in runtime.plan]
        self.assertFalse(runtime.apply_replan([
            {"id": "type", "type": "action", "action": "type_text", "capability": "windows_ui", "target": "focused_element", "args": {"text": "hello"}, "depends_on": ["unknown"]},
        ]))
        self.assertEqual(runtime.plan, original)
        self.assertEqual(runtime.mission_state, "blocked")
        self.assertIn("unknown id", runtime.last_error)

    def test_replan_does_not_trust_reasoner_supplied_completed_status(self):
        runtime = MissionRuntime(max_retries=0, max_steps=3)
        runtime.start("write greeting", [
            {"id": "old", "type": "action", "action": "type_text", "capability": "windows_ui", "target": "focused_element", "args": {"text": "hello"}, "depends_on": []},
        ])
        self.assertTrue(runtime.apply_replan([
            {"id": "new", "type": "action", "action": "type_text", "capability": "windows_ui", "target": "different_element", "args": {"text": "hello"}, "depends_on": [], "status": "completed", "verification": {"verified": True}},
        ]))
        self.assertEqual(runtime.plan[0]["status"], "pending")
        self.assertIsNone(runtime.plan[0].get("verification"))

    def test_mission_guard_rejects_dependency_cycles(self):
        from ai_core.mission_plan_guard import MissionPlanGuard
        error = MissionPlanGuard.validate([
            {"id": "first", "depends_on": ["second"]},
            {"id": "second", "depends_on": ["first"]},
        ], max_steps=3)
        self.assertIn("dependency cycle", error)



if __name__ == "__main__":
    unittest.main()
