import unittest

from ai_core.action_risk_policy import ActionRiskPolicy
from ai_core.action_schema import ActionSchema, ActionSchemaError
from ai_core.action_validator import ActionValidator
from ai_core.autonomous_agent import AutonomousAgent


def _risky_plan():
    return [{
        "step": 1,
        "id": "delete_report",
        "type": "action",
        "action": "delete_file",
        "capability": "file_manager",
        "target": "report.csv",
        "args": {},
        "depends_on": [],
    }]


class ActionRiskPolicyTests(unittest.TestCase):
    def test_common_destructive_and_external_side_effects_require_confirmation(self):
        steps = [
            {"id": "delete", "type": "action", "action": "delete_file", "target": "report.csv"},
            {"id": "send", "type": "action", "action": "send_email", "target": "client"},
            {"id": "click", "type": "action", "action": "click_ui_element", "target": "Delete"},
            {"id": "submit", "type": "action", "action": "click_ui_element", "target": "Submit"},
            {"id": "transfer", "type": "action", "action": "transfer_funds", "target": "account"},
        ]

        result = ActionRiskPolicy.assess_plan(steps)

        self.assertTrue(result["requires_confirmation"])
        self.assertEqual(result["risk_level"], "high")
        self.assertEqual(result["step_ids"], ["delete", "send", "click", "submit", "transfer"])
        self.assertIn("delete_file", result["summary"])
        self.assertNotIn("args", result["summary"])

    def test_typed_payload_is_not_mistaken_for_an_action(self):
        result = ActionRiskPolicy.assess_plan([{
            "id": "type_text",
            "type": "action",
            "action": "type_text",
            "target": "focused_element",
            "args": {"text": "Please delete the old draft tomorrow."},
        }])
        self.assertFalse(result["requires_confirmation"])
        self.assertEqual(result["findings"], [])

    def test_explicit_confirmation_metadata_survives_schema_and_validator(self):
        raw = {
            "id": "external_effect",
            "action": "future_operation",
            "capability": "custom_provider",
            "target": "account",
            "risk_level": "critical",
            "requires_confirmation": True,
            "confirmation_reason": "An external side effect may occur.",
            "reversible": False,
            "args": {},
        }

        validated = ActionValidator().validate_action(raw)

        self.assertTrue(validated["valid"])
        action = validated["action"]
        self.assertEqual(action["risk_level"], "critical")
        self.assertTrue(action["requires_confirmation"])
        self.assertFalse(action["reversible"])
        self.assertTrue(ActionRiskPolicy.assess_plan([action])["requires_confirmation"])

    def test_schema_rejects_malformed_risk_contracts(self):
        with self.assertRaises(ActionSchemaError):
            ActionSchema(action="delete_file", capability="file_manager", risk_level="unknown")
        with self.assertRaises(ActionSchemaError):
            ActionSchema(action="delete_file", capability="file_manager", requires_confirmation="false")
        with self.assertRaises(ActionSchemaError):
            ActionSchema(action="delete_file", capability="file_manager", reversible="no")

    def test_high_impact_plan_is_held_before_mission_runtime_start(self):
        agent = AutonomousAgent(max_steps=3)
        starts = []
        agent.mission_runtime.start = lambda *args, **kwargs: starts.append((args, kwargs))
        response = agent._run_mission(
            goal="delete report.csv",
            plan=_risky_plan(),
            intent=None,
            analysis={"goal": "delete report.csv"},
            compilation={},
            route={"route": "mission"},
        )

        self.assertEqual(response["stage"], "action_confirmation_required")
        self.assertEqual(response["status"], "needs_confirmation")
        self.assertTrue(response["requires_user_input"])
        self.assertIn("confirm action", response["message"])
        self.assertEqual(starts, [])
        self.assertIsInstance(agent.pending_action_confirmation, dict)
        self.assertFalse(agent.active)

    def test_pending_plan_cannot_be_bypassed_and_explicit_confirmation_reuses_it(self):
        agent = AutonomousAgent(max_steps=3)
        original_plan = _risky_plan()
        agent._run_mission(
            goal="delete report.csv",
            plan=original_plan,
            intent=None,
            analysis={"goal": "delete report.csv"},
            compilation={},
            route={"route": "mission"},
        )
        calls = []

        def fake_run_mission(**kwargs):
            calls.append(kwargs)
            return {"success": True, "stage": "test_resumed"}

        agent._run_mission = fake_run_mission
        unrelated = agent.run("open Calculator")
        self.assertEqual(unrelated["stage"], "action_confirmation_required")
        self.assertEqual(calls, [])
        self.assertIsNotNone(agent.pending_action_confirmation)

        result = agent.run("confirm action")
        self.assertEqual(result["stage"], "test_resumed")
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["goal"], "delete report.csv")
        self.assertEqual(calls[0]["plan"], original_plan)
        self.assertTrue(calls[0]["pre_dispatch_confirmed"])
        self.assertIsNone(agent.pending_action_confirmation)

    def test_cancel_discards_pending_plan_without_execution(self):
        agent = AutonomousAgent(max_steps=3)
        starts = []
        agent.mission_runtime.start = lambda *args, **kwargs: starts.append((args, kwargs))
        agent._run_mission(
            goal="delete report.csv",
            plan=_risky_plan(),
            intent=None,
            analysis={},
            compilation={},
            route={"route": "mission"},
        )

        result = agent.run("cancel action")

        self.assertTrue(result["success"])
        self.assertEqual(result["stage"], "action_confirmation_cancelled")
        self.assertIsNone(agent.pending_action_confirmation)
        self.assertEqual(starts, [])


if __name__ == "__main__":
    unittest.main()
