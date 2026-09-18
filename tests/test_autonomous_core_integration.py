"""Vyom autonomous-core integration tests.

These tests validate module wiring without launching Windows applications,
using a microphone, or calling a remote AI provider.
"""

import unittest

from ai_core.autonomous_agent import AutonomousAgent
from ai_core.reasoning_engine import ReasoningEngine
from ai_core.deep_reasoner import DeepReasoner
from ai_core.goal_compiler import GoalCompiler
from ai_core.mission_planner import MissionPlanner


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
                "analysis": "test plan",
                "route": "mission",
                "plan": [
                    {
                        "step": 1,
                        "type": "action",
                        "intent": {
                            "intent": "open",
                            "target": "notepad"
                        }
                    },
                    {
                        "step": 2,
                        "type": "action",
                        "intent": {
                            "intent": "open",
                            "target": "calculator"
                        }
                    }
                ]
            }
        }

    def reset(self):
        self.calls = 0


class AutonomousCoreIntegrationTests(unittest.TestCase):

    def test_agent_shares_goal_compiler_with_reasoning_engine(self):
        agent = AutonomousAgent(max_steps=5)
        self.assertIs(
            agent.goal_compiler,
            agent.reasoning_engine.goal_compiler
        )

    def test_reasoning_engine_accepts_safe_deep_plan(self):
        compiler = GoalCompiler()
        deep = FakeDeepReasoner()
        engine = ReasoningEngine(
            goal_compiler=compiler,
            deep_reasoner=deep
        )

        result = engine.reason("open notepad and open calculator")

        self.assertTrue(result["success"])
        self.assertEqual(result["route"]["route"], "mission")
        self.assertEqual(len(result["plan"]), 2)
        self.assertEqual(deep.calls, 1)
        self.assertEqual(
            result["plan"][0]["intent"]["intent"],
            "open"
        )

    def test_mission_planner_normalizes_reasoning_plan(self):
        planner = MissionPlanner(max_steps=5)
        plan = planner.plan(
            goal="open notepad and open calculator",
            analysis={
                "plan": [
                    {
                        "step": 1,
                        "type": "execute_existing_intent",
                        "intent": {"intent": "open", "target": "notepad"}
                    },
                    {
                        "step": 2,
                        "type": "execute_existing_intent",
                        "intent": {"intent": "open", "target": "calculator"}
                    }
                ]
            },
            compiled_goal={},
            route={"route": "mission"}
        )

        self.assertEqual(len(plan), 2)
        self.assertEqual(plan[1]["depends_on"], [plan[0]["id"]])
        self.assertEqual(plan[0]["status"], "pending")


if __name__ == "__main__":
    unittest.main()
