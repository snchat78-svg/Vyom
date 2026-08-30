"""
Vyom AI - Goal Intelligence Tests

Dependency-free tests for the new goal compiler/planner layer.
They do not launch applications or touch the microphone.
"""

import unittest

from ai_core.goal_compiler import GoalCompiler
from ai_core.mission_planner import MissionPlanner
from ai_core.world_state import WorldStateModel
from ai_core.reasoning_engine import ReasoningEngine


class GoalIntelligenceTests(unittest.TestCase):

    def setUp(self):
        self.compiler = GoalCompiler()

    def test_open_command(self):
        result = self.compiler.compile("Please open Notepad")
        self.assertTrue(result["suggested_intents"])
        self.assertEqual(
            result["suggested_intents"][0]["intent"],
            "open"
        )
        self.assertEqual(
            result["suggested_intents"][0]["target"].lower(),
            "notepad"
        )

    def test_hindi_open_command(self):
        result = self.compiler.compile("नोटपैड खोल दो")
        self.assertTrue(result["suggested_intents"])
        self.assertEqual(
            result["suggested_intents"][0]["intent"],
            "open"
        )

    def test_compound_goal(self):
        result = self.compiler.compile(
            "open notepad and open calculator"
        )
        self.assertEqual(len(result["suggested_intents"]), 2)

        planner = MissionPlanner(max_steps=10)
        plan = planner.plan(
            goal=result["goal"],
            compiled_goal=result,
            analysis={},
            route={"route": "existing_tools"},
        )
        self.assertEqual(len(plan), 2)

    def test_contextual_open(self):
        result = self.compiler.compile(
            "open it",
            context={"current_target": "notepad"}
        )
        self.assertEqual(
            result["suggested_intents"][0]["target"],
            "notepad"
        )

    def test_reasoning_without_api(self):
        engine = ReasoningEngine()
        result = engine.reason("open calculator")
        self.assertEqual(
            result["route"]["route"],
            "existing_tools"
        )
        self.assertTrue(result["plan"])
        self.assertEqual(
            result["plan"][0]["intent"]["intent"],
            "open"
        )

    def test_world_state(self):
        state = WorldStateModel(max_processes=5).snapshot(
            {"current_app": "notepad"}
        )
        self.assertEqual(state["current_app"], "notepad")
        self.assertIn("running_processes", state)


if __name__ == "__main__":
    unittest.main()
