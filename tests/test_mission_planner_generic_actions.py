import unittest

from ai_core.mission_planner import MissionPlanner


class MissionPlannerGenericActionTests(unittest.TestCase):
    def test_capability_route_keeps_generic_actions_as_action_steps(self):
        planner = MissionPlanner(max_steps=5)
        plan = planner.plan(
            goal="click and type",
            analysis={
                "generic_actions": [
                    {
                        "id": "focus",
                        "action": "focus_window",
                        "capability": "windows_ui",
                        "target": "Test",
                        "args": {},
                        "depends_on": [],
                    },
                    {
                        "id": "write",
                        "action": "type_text",
                        "capability": "windows_ui",
                        "target": "hello",
                        "args": {},
                        "depends_on": ["focus"],
                    },
                ]
            },
            route={"route": "capability", "capability": "windows_ui"},
        )
        self.assertEqual(len(plan), 2)
        self.assertEqual(plan[0]["type"], "action")
        self.assertEqual(plan[0]["action"], "focus_window")
        self.assertEqual(plan[1]["action"], "type_text")
        self.assertEqual(plan[1]["depends_on"], ["focus"])

    def test_legacy_capability_fallback_is_preserved(self):
        planner = MissionPlanner(max_steps=5)
        plan = planner.plan(
            goal="some capability",
            analysis={},
            route={"route": "capability", "capability": "future_capability"},
        )
        self.assertEqual(len(plan), 1)
        self.assertEqual(plan[0]["type"], "use_capability")


if __name__ == "__main__":
    unittest.main()
