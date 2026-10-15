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
            "running_windows": [
                {"name": "Test Window", "control_type": "Window", "visible": True}
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

    def capture(self):
        return {
            "success": True,
            "stage": "screen_captured",
            "path": "C:/temp/test.bmp",
            "width": 1920,
            "height": 1080,
            "verification": {"verified": True},
        }


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
        self.assertEqual(state["running_windows"][0]["name"], "Test Window")
        self.assertEqual(state["clipboard"]["text"], "copied text")
        self.assertEqual(state["screen"]["size"]["width"], 1920)
        self.assertTrue(state["screen"]["snapshot"]["available"])
        self.assertFalse(state["screen"]["snapshot"]["captured"])

        captured = world.snapshot(
            {"current_app": "Test App"},
            include_screen_snapshot=True,
        )
        self.assertTrue(captured["screen"]["snapshot"]["captured"])
        self.assertEqual(captured["screen"]["snapshot"]["path"], "C:/temp/test.bmp")
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

    def test_observation_history_is_timestamped_and_bounded(self):
        world = WorldStateModel()
        world.max_observation_history = 2
        source = {"phase": "first"}

        world.record_observation(source)
        world.record_observation({"phase": "second", "timestamp": 123.0})
        world.record_observation({"phase": "third"})

        self.assertNotIn("timestamp", source)
        self.assertGreater(world.observation_history[0]["timestamp"], 0)
        self.assertEqual(
            [item["phase"] for item in world.observation_history],
            ["second", "third"],
        )
        self.assertEqual(world.observation_history[0]["timestamp"], 123.0)

    def test_clipboard_is_not_read_when_not_requested(self):
        class TrackingClipboard(FakeClipboard):
            def __init__(self):
                self.reads = 0

            def get_text(self):
                self.reads += 1
                return super().get_text()

        clipboard = TrackingClipboard()
        world = WorldStateModel(clipboard_manager=clipboard)
        state = world.snapshot(include_clipboard=False)
        self.assertEqual(clipboard.reads, 0)
        self.assertTrue(state["clipboard"]["skipped"])

        world.snapshot(include_clipboard=True)
        self.assertEqual(clipboard.reads, 1)

    def test_observation_history_is_compact_and_not_recursive(self):
        world = WorldStateModel()
        source = {
            "timestamp": 111.0,
            "phase": "after_action",
            "step_id": "open_app",
            "step_type": "execute_existing_intent",
            "result": {"success": True, "stage": "opened", "debug_blob": "not for history"},
            "verification": {"verified": True, "state": "observed", "details": "large payload"},
            "world_state": {
                "timestamp": 110.0,
                "current_window": {"exists": True, "name": "Editor", "value": "sensitive typed input"},
                "focused_control": {"exists": True, "name": "Search box", "value": "secret query"},
                "selected_control": {"exists": True, "name": "Search", "control_type": "Button"},
                "observation_history": [{"phase": "previous", "world_state": {"observation_history": ["deep"]}}],
                "mission_state": {"mission_state": "running", "current_step": "open_app", "debug": "drop"},
            },
        }

        world.record_observation(source)
        saved = world.observation_history[-1]

        self.assertEqual(saved["timestamp"], 111.0)
        self.assertEqual(saved["phase"], "after_action")
        self.assertEqual(saved["world_state"]["current_window"]["name"], "Editor")
        self.assertNotIn("observation_history", saved["world_state"])
        self.assertNotIn("value", saved["world_state"]["focused_control"])
        self.assertNotIn("debug_blob", saved["result"])
        self.assertNotIn("details", saved["verification"])
        self.assertEqual(saved["world_state"]["mission_state"]["mission_state"], "running")

    def test_legacy_snapshot_signature_remains_usable(self):
        world = WorldStateModel()
        state = world.snapshot({"current_target": "example"})
        self.assertEqual(state["current_target"], "example")
        self.assertIn("running_processes", state)
        self.assertIn("screen", state)


if __name__ == "__main__":
    unittest.main()
