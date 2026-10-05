import unittest

from ai_core.world_state import WorldStateModel


class FakeUIObserver:
    def snapshot(self, action=None):
        return {
            "available": True,
            "active_window": {"name": "Test Window"},
            "focused_element": {"name": "SearchBox", "control_type": "Edit"},
            "selected_element": {"name": "Search", "control_type": "ListItem"},
            "ui_tree_signature": [
                {"name": "Search", "control_type": "Button"}
            ],
        }


class FakeClipboard:
    def is_available(self):
        return True

    def get_text(self):
        return {"success": True, "text": "copied text"}


class FakeScreen:
    def is_available(self):
        return True

    def get_size(self):
        return {"width": 1920, "height": 1080}


class Phase4WorldStateTests(unittest.TestCase):
    def test_world_state_contains_canonical_computer_and_mission_state(self):
        world = WorldStateModel(
            ui_observer=FakeUIObserver(),
            clipboard_manager=FakeClipboard(),
            screen_observer=FakeScreen(),
        )
        world.record_execution(
            action={"type": "action", "action": "click_ui_element"},
            result={"success": True, "stage": "verified"},
            verification={"verified": True, "verification_level": "state"},
        )
        state = world.snapshot(
            {
                "current_app": "Test App",
                "current_file": "test.txt",
                "current_target": "Search",
                "task_state": "running",
                "last_success": True,
            },
            mission_state={"mission_state": "running", "current_step": "a1"},
        )

        self.assertEqual(state["current_app"], "Test App")
        self.assertEqual(state["current_file"], "test.txt")
        self.assertEqual(state["current_window"]["name"], "Test Window")
        self.assertEqual(state["focused_control"]["name"], "SearchBox")
        self.assertEqual(state["selected_control"]["name"], "Search")
        self.assertEqual(state["visible_ui_elements"][0]["name"], "Search")
        self.assertEqual(state["clipboard"]["text"], "copied text")
        self.assertEqual(state["screen"]["size"]["width"], 1920)
        self.assertEqual(state["mission_state"]["current_step"], "a1")
        self.assertTrue(state["last_verification"]["verified"])

    def test_observation_failures_are_isolated_from_legacy_state(self):
        class BrokenObserver:
            def snapshot(self, action=None):
                raise RuntimeError("UI unavailable")

        world = WorldStateModel(ui_observer=BrokenObserver())
        state = world.snapshot({"current_app": "Notepad"})

        self.assertEqual(state["current_app"], "Notepad")
        self.assertFalse(state["ui"]["available"])
        self.assertIn("error", state["ui"])

    def test_legacy_snapshot_signature_remains_usable(self):
        world = WorldStateModel()
        state = world.snapshot({"current_target": "example"})
        self.assertEqual(state["current_target"], "example")
        self.assertIn("running_processes", state)
        self.assertIn("screen", state)


if __name__ == "__main__":
    unittest.main()
