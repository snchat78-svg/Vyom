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


if __name__ == "__main__":
    unittest.main()

