import time
import unittest

from ai_core.context_action_compiler import ContextActionCompiler


class FakeGoalCompiler:
    def _split_compound(self, goal):
        return [part.strip() for part in goal.split(" and ") if part.strip()]

    def _compile_single_intent(self, text):
        value = text.strip()
        if value.lower().startswith("open "):
            return {"intent": "open", "target": value[5:].strip()}
        return None


class ContextActionCompilerTests(unittest.TestCase):
    def setUp(self):
        self.compiler = ContextActionCompiler(FakeGoalCompiler())
        self.context = {
            "current_app": "Current Application",
            "current_target": "Current Application",
            "conversation_history": [
                {"role": "user", "text": "My name is Shambhu Lal", "metadata": {}}
            ],
        }

    def test_follow_up_type_becomes_generic_action(self):
        result = self.compiler.compile("type Hello World", self.context)
        self.assertTrue(result["complete"])
        self.assertTrue(result["continuation"])
        self.assertEqual(result["plan"][0]["type"], "action")
        self.assertEqual(result["plan"][0]["action"], "type_text")
        self.assertEqual(result["plan"][0]["args"]["text"], "Hello World")
        self.assertEqual(result["plan"][0]["capability"], "windows_ui")

    def test_explicit_session_fact_can_resolve_my_name(self):
        result = self.compiler.compile("type my name", self.context)
        self.assertTrue(result["complete"])
        self.assertEqual(result["plan"][0]["args"]["text"], "Shambhu Lal")

    def test_missing_reference_does_not_execute_partial_goal(self):
        result = self.compiler.compile(
            "open Some App and type my name",
            {"current_app": "Current Application", "conversation_history": []},
        )
        self.assertFalse(result["complete"])
        self.assertEqual(result["plan"], [])
        self.assertTrue(result["clarification"])

    def test_mixed_goal_preserves_existing_and_generic_steps(self):
        result = self.compiler.compile("open Some App and type Hello", self.context)
        self.assertTrue(result["complete"])
        self.assertEqual(
            [step["type"] for step in result["plan"]],
            ["execute_existing_intent", "action"],
        )
        self.assertEqual(result["plan"][0]["intent"]["intent"], "open")
        self.assertEqual(result["plan"][1]["action"], "type_text")
        self.assertEqual(result["plan"][1]["depends_on"], ["context_1"])

    def test_new_target_does_not_depend_on_previous_app_name(self):
        result = self.compiler.compile("open Another Application", self.context)
        self.assertTrue(result["complete"])
        self.assertEqual(result["plan"][0]["intent"]["target"], "Another Application")

    @staticmethod
    def _runtime_context(timestamp=None, ui_available=True, focused=True):
        focus = {
            "exists": bool(focused),
            "name": "Editor input",
            "control_type": "Edit",
            "visible": True,
            "enabled": True,
        }
        return {
            "timestamp": time.time() if timestamp is None else timestamp,
            "current_app": "Stale application",
            "current_target": "Stale application",
            "current_window": {"exists": True, "name": "Current window"},
            "focused_control": focus,
            "ui": {
                "available": bool(ui_available),
                "active_window": {"exists": True, "name": "Current window"},
                "focused_element": focus,
            },
            "conversation_history": [
                {"role": "user", "text": "My name is Shambhu Lal", "metadata": {}}
            ],
        }

    def test_runtime_follow_up_uses_fresh_observed_focus(self):
        result = self.compiler.compile("type Hello World", self._runtime_context())
        self.assertTrue(result["complete"])
        self.assertEqual(result["plan"][0]["action"], "type_text")
        self.assertEqual(result["plan"][0]["args"]["text"], "Hello World")

    def test_runtime_follow_up_rejects_stale_focus_and_old_session_target(self):
        stale = self._runtime_context(timestamp=time.time() - 60)
        result = self.compiler.compile("type Hello World", stale)
        self.assertFalse(result["complete"])
        self.assertEqual(result["plan"], [])
        self.assertTrue(result["clarification"])

    def test_runtime_follow_up_rejects_unavailable_ui_even_when_session_has_old_app(self):
        unavailable = self._runtime_context(ui_available=False, focused=False)
        result = self.compiler.compile("type Hello World", unavailable)
        self.assertFalse(result["complete"])
        self.assertEqual(result["plan"], [])
        self.assertTrue(result["clarification"])

    def test_click_it_resolves_matching_live_focus_and_selection(self):
        context = self._runtime_context()
        target = {
            "exists": True,
            "name": "Search",
            "control_type": "Button",
            "visible": True,
            "enabled": True,
        }
        context["focused_control"] = dict(target)
        context["selected_control"] = dict(target)
        context["ui"]["focused_element"] = dict(target)
        context["ui"]["selected_element"] = dict(target)

        result = self.compiler.compile("click it", context)
        self.assertTrue(result["complete"])
        self.assertEqual(result["plan"][0]["action"], "click_ui_element")
        self.assertEqual(result["plan"][0]["target"], "Search")

    def test_click_it_clarifies_when_focus_and_selection_disagree(self):
        context = self._runtime_context()
        context["focused_control"] = {
            "exists": True, "name": "Editor input", "control_type": "Edit"
        }
        context["selected_control"] = {
            "exists": True, "name": "Search", "control_type": "Button"
        }
        context["ui"]["focused_element"] = dict(context["focused_control"])
        context["ui"]["selected_element"] = dict(context["selected_control"])

        result = self.compiler.compile("click it", context)
        self.assertFalse(result["complete"])
        self.assertEqual(result["plan"], [])
        self.assertIn("Focus", result["clarification"])

    def test_focus_that_window_resolves_to_fresh_active_window(self):
        context = self._runtime_context()
        result = self.compiler.compile("focus that window", context)
        self.assertTrue(result["complete"])
        self.assertEqual(result["plan"][0]["action"], "focus_window")
        self.assertEqual(result["plan"][0]["target"], "Current window")

    def test_open_same_file_requires_filename_match_in_active_window(self):
        context = self._runtime_context()
        context["current_file"] = r"C:\Docs\notes.txt"
        context["current_window"] = {
            "exists": True, "name": "notes.txt - Notepad"
        }
        context["ui"]["active_window"] = dict(context["current_window"])

        result = self.compiler.compile("open same file", context)
        self.assertTrue(result["complete"])
        self.assertEqual(result["plan"][0]["intent"]["intent"], "open_file")
        self.assertEqual(result["plan"][0]["intent"]["target"], r"C:\Docs\notes.txt")

    def test_nested_ui_timestamp_rejects_stale_observation(self):
        context = self._runtime_context()
        context["ui"]["timestamp"] = time.time() - 60

        result = self.compiler.compile("click it", context)

        self.assertFalse(result["complete"])
        self.assertEqual(result["plan"], [])
        self.assertTrue(result["clarification"])

    def test_click_it_prefers_coherent_fresh_ui_focus_and_selection(self):
        context = self._runtime_context()
        fresh_target = {
            "exists": True,
            "name": "Search",
            "control_type": "Button",
            "visible": True,
            "enabled": True,
        }
        context["focused_control"] = {
            "exists": True, "name": "Old Editor", "control_type": "Edit"
        }
        context["selected_control"] = {
            "exists": True, "name": "Old Selection", "control_type": "ListItem"
        }
        context["ui"]["focused_element"] = dict(fresh_target)
        context["ui"]["selected_element"] = dict(fresh_target)

        result = self.compiler.compile("click it", context)

        self.assertTrue(result["complete"])
        self.assertEqual(result["plan"][0]["target"], "Search")

    def test_click_it_does_not_fallback_to_stale_mirror_when_ui_has_no_focus(self):
        context = self._runtime_context()
        context["focused_control"] = {
            "exists": True, "name": "Old Editor", "control_type": "Edit"
        }
        context["selected_control"] = {
            "exists": True, "name": "Old Selection", "control_type": "ListItem"
        }
        context["ui"]["focused_element"] = {"exists": False}
        context["ui"]["selected_element"] = {"exists": False}

        result = self.compiler.compile("click it", context)

        self.assertFalse(result["complete"])
        self.assertEqual(result["plan"], [])
        self.assertTrue(result["clarification"])

    def test_focus_that_window_prefers_fresh_ui_active_window(self):
        context = self._runtime_context()
        context["current_window"] = {"exists": True, "name": "Old Window"}
        context["ui"]["active_window"] = {"exists": True, "name": "New Window"}

        result = self.compiler.compile("focus that window", context)

        self.assertTrue(result["complete"])
        self.assertEqual(result["plan"][0]["target"], "New Window")

    def test_click_it_does_not_use_a_stale_observation(self):
        context = self._runtime_context(timestamp=time.time() - 60)
        result = self.compiler.compile("click it", context)
        self.assertFalse(result["complete"])
        self.assertEqual(result["plan"], [])
        self.assertTrue(result["clarification"])


if __name__ == "__main__":
    unittest.main()

