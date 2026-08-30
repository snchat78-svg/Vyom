"""
Project : Vyom AI
Version : 1.0
Module  : Reasoning Engine

Purpose:
    Hybrid goal-centric reasoning and planning layer.

    Existing IntentEngine/ToolManager behaviour remains intact.
    Unknown natural-language goals are first compiled locally.
    A configured AI model may then provide deeper reasoning.
"""

from ai_core.capability_manager import CapabilityManager
from ai_core.deep_reasoner import DeepReasoner
from ai_core.goal_compiler import GoalCompiler
from ai_core.mission_planner import MissionPlanner


class ReasoningEngine:

    def __init__(
        self,
        capability_manager=None,
        deep_reasoner=None,
        goal_compiler=None,
        mission_planner=None,
    ):
        self.capability_manager = (
            capability_manager
            if capability_manager is not None
            else CapabilityManager()
        )
        self.goal_compiler = (
            goal_compiler
            if goal_compiler is not None
            else GoalCompiler()
        )
        self.deep_reasoner = (
            deep_reasoner
            if deep_reasoner is not None
            else DeepReasoner(
                goal_compiler=self.goal_compiler
            )
        )
        self.mission_planner = (
            mission_planner
            if mission_planner is not None
            else MissionPlanner()
        )

        self.last_goal = ""
        self.last_analysis = None
        self.last_plan = []
        self.last_capabilities = []
        self.last_compilation = None

    def _normalize(self, text):
        return str(text or "").strip()

    def _capabilities(self):
        return self.capability_manager.list_capabilities(
            enabled_only=True
        )

    def _fallback_analysis(self, goal, intent=None, compiled=None):
        compiled = compiled or self.goal_compiler.compile(
            goal, intent=intent
        )
        capabilities = self.capability_manager.match(goal)

        suggested = compiled.get("suggested_intents", [])
        if suggested:
            route = "existing_tools"
        elif capabilities:
            route = "capability"
        else:
            route = "missing_capability"

        return {
            "understood": True,
            "goal": goal,
            "objective": compiled.get("objective", goal),
            "type": "known_command" if suggested else "unknown_goal",
            "complexity": compiled.get("complexity", "simple"),
            "intent": suggested[0] if suggested else intent,
            "capabilities": capabilities,
            "route": route,
            "plan": [],
            "goal_compilation": compiled,
            "reason": compiled.get("reason", "Local fallback reasoning was used."),
        }

    def analyze_goal(
        self,
        goal,
        intent=None,
        context=None,
        previous_result=None
    ):
        goal = self._normalize(goal)
        self.last_goal = goal

        if not goal:
            analysis = {
                "understood": False,
                "goal": "",
                "type": "empty",
                "complexity": "none",
                "intent": intent,
                "reason": "Empty goal.",
            }
            self.last_analysis = analysis
            return analysis

        compiled = self.goal_compiler.compile(
            goal=goal,
            intent=intent,
            context=context,
        )
        self.last_compilation = compiled

        capabilities = self._capabilities()
        self.last_capabilities = capabilities

        # DeepReasoner is now allowed to run even for an already-known
        # intent. It can enrich the plan while still falling back locally.
        ai_result = self.deep_reasoner.reason(
            goal=goal,
            context=context,
            capabilities=capabilities,
            previous_result=previous_result,
            intent=intent,
        )

        if isinstance(ai_result, dict) and ai_result.get("success", False):
            data = ai_result.get("data", {})
            if isinstance(data, dict):
                data.setdefault("goal", goal)
                data.setdefault("intent", intent)
                data.setdefault("capabilities", capabilities)
                data.setdefault("goal_compilation", compiled)
                self.last_analysis = data
                return data

        analysis = self._fallback_analysis(
            goal,
            intent,
            compiled=compiled
        )
        self.last_analysis = analysis
        return analysis

    def decide_route(self, analysis):
        if not isinstance(analysis, dict):
            return {"route": "stop", "reason": "Invalid analysis."}

        if not analysis.get("understood", False):
            return {
                "route": "stop",
                "reason": analysis.get("reason", "Goal not understood."),
            }

        requested_route = str(
            analysis.get("route", "")
        ).strip().lower()

        valid_routes = {
            "existing_tools",
            "capability",
            "missing_capability",
            "conversation",
        }

        if requested_route in valid_routes:
            route = {
                "route": requested_route,
                "reason": analysis.get(
                    "reason",
                    "Reasoning selected this route."
                ),
            }
            if analysis.get("capability"):
                route["capability"] = analysis.get("capability")
            return route

        compiled = analysis.get("goal_compilation", {})
        if (
            isinstance(compiled, dict)
            and compiled.get("suggested_intents")
        ):
            return {
                "route": "existing_tools",
                "reason": "Goal compiler mapped the goal to existing tools.",
            }

        if analysis.get("type") == "known_command":
            return {
                "route": "existing_tools",
                "reason": "Existing ToolManager can execute this command.",
            }

        capabilities = analysis.get("capabilities", [])
        if capabilities:
            return {
                "route": "capability",
                "reason": "A matching capability was found.",
                "capability": capabilities[0],
            }

        return {
            "route": "missing_capability",
            "reason": "No executable capability is currently available.",
        }

    def create_plan(self, analysis, route):
        if not isinstance(analysis, dict):
            self.last_plan = []
            return []

        goal = analysis.get("goal", "")
        compiled = analysis.get("goal_compilation", {})

        plan = self.mission_planner.plan(
            goal=goal,
            analysis=analysis,
            compiled_goal=compiled,
            route=route,
        )

        self.last_plan = plan
        return plan

    def reason(
        self,
        goal,
        intent=None,
        context=None,
        previous_result=None
    ):
        analysis = self.analyze_goal(
            goal,
            intent,
            context=context,
            previous_result=previous_result,
        )
        route = self.decide_route(analysis)
        plan = self.create_plan(analysis, route)

        return {
            "analysis": analysis,
            "route": route,
            "plan": plan,
        }

    def reset(self):
        self.last_goal = ""
        self.last_analysis = None
        self.last_plan = []
        self.last_capabilities = []
        self.last_compilation = None

        try:
            self.deep_reasoner.reset()
        except Exception:
            pass

        try:
            self.mission_planner.reset()
        except Exception:
            pass
