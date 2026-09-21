import unittest

from ai_core.reasoning_engine import ReasoningEngine


class FakeGoalCompiler:
    def _split_compound(self, goal):
        return [part.strip() for part in goal.split(" and ") if part.strip()]

    def _compile_single_intent(self, text):
        value = text.strip()
        if value.lower().startswith("open "):
            return {"intent": "open", "target": value[5:].strip()}
        return None

    def compile(self, goal, intent=None, context=None):
        parts = self._split_compound(goal)
        suggestions = []
        for part in parts:
            candidate = self._compile_single_intent(part)
            if candidate:
                suggestions.append(candidate)
        if len(suggestions) != len(parts):
            suggestions = []
        return {
            "success": True,
            "understood": True,
            "objective": goal,
            "complexity": "simple",
            "suggested_intents": suggestions,
            "sub_goals": [],
            "reason": "test",
        }


class ReasoningEngineStep2BTests(unittest.TestCase):
    def setUp(self):
        self.context = {
            "current_app": "Current Application",
            "current_target": "Current Application",
            "conversation_history": [],
        }

    def test_type_follow_up_routes_to_windows_capability(self):
        engine = ReasoningEngine(goal_compiler=FakeGoalCompiler())
        engine.capability_registry.register(
            "windows_ui", "Windows UI", ["type_text"], enabled=True
        )
        result = engine.reason("type Hello", context=self.context)
        self.assertTrue(result["success"])
        self.assertEqual(result["route"]["route"], "capability")
        self.assertEqual(result["plan"][0]["action"], "type_text")

    def test_open_and_type_routes_to_ordered_mission(self):
        engine = ReasoningEngine(goal_compiler=FakeGoalCompiler())
        engine.capability_registry.register(
            "windows_ui", "Windows UI", ["type_text"], enabled=True
        )
        result = engine.reason("open Current App and type Hello", context=self.context)
        self.assertTrue(result["success"])
        self.assertEqual(result["route"]["route"], "mission")
        self.assertEqual(
            [step["type"] for step in result["plan"]],
            ["execute_existing_intent", "action"],
        )


if __name__ == "__main__":
    unittest.main()

