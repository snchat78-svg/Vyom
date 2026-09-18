"""Tests for the central reasoning integration.

No network, microphone, or Windows application is required.
"""

import unittest

from ai_core.goal_compiler import GoalCompiler
from ai_core.reasoning_engine import ReasoningEngine


class FakeDeepReasoner:
    def __init__(self):
        self.calls = 0

    def is_available(self):
        return True

    def reason(self, goal, context=None, capabilities=None, previous_result=None, intent=None):
        self.calls += 1
        return {
            "success": True,
            "available": True,
            "data": {
                "understood": True,
                "goal": goal,
                "language": "english",
                "complexity": "medium",
                "analysis": "two executable actions",
                "route": "mission",
                "plan": [
                    {"step": 1, "intent": {"intent": "open", "target": "notepad"}},
                    {"step": 2, "intent": {"intent": "open", "target": "calculator"}},
                ],
            },
        }

    def reset(self):
        self.calls = 0


class ReasoningCoreWiringTests(unittest.TestCase):

    def test_deep_reasoner_is_connected_for_non_trivial_goal(self):
        compiler = GoalCompiler()
        deep = FakeDeepReasoner()
        engine = ReasoningEngine(
            goal_compiler=compiler,
            deep_reasoner=deep,
        )

        result = engine.reason("open notepad and open calculator")

        self.assertTrue(result["success"])
        self.assertEqual(result["route"]["route"], "mission")
        self.assertEqual(len(result["plan"]), 2)
        self.assertEqual(deep.calls, 1)
        self.assertEqual(result["plan"][0]["intent"]["intent"], "open")

    def test_simple_action_keeps_deterministic_path(self):
        compiler = GoalCompiler()
        deep = FakeDeepReasoner()
        engine = ReasoningEngine(
            goal_compiler=compiler,
            deep_reasoner=deep,
        )

        result = engine.reason("open calculator")

        self.assertTrue(result["success"])
        self.assertEqual(result["route"]["route"], "existing_tools")
        self.assertEqual(result["plan"][0]["intent"]["target"].lower(), "calculator")
        self.assertEqual(deep.calls, 0)

    def test_model_output_is_restricted_to_known_tool_intents(self):
        compiler = GoalCompiler()

        class UnsafeDeep(FakeDeepReasoner):
            def reason(self, *args, **kwargs):
                self.calls += 1
                return {
                    "success": True,
                    "data": {
                        "route": "mission",
                        "plan": [
                            {"intent": {"intent": "run_arbitrary_code", "target": "bad"}}
                        ],
                    },
                }

        deep = UnsafeDeep()
        engine = ReasoningEngine(
            goal_compiler=compiler,
            deep_reasoner=deep,
        )

        result = engine.reason("do a complex task")

        self.assertTrue(result["success"])
        self.assertEqual(deep.calls, 1)
        self.assertNotEqual(result["route"]["route"], "mission")
        self.assertEqual(result["route"]["route"], "missing_capability")


if __name__ == "__main__":
    unittest.main()
