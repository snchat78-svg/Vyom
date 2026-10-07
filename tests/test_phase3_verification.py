import unittest

from windows_agent.ui_state_observer import UIStateObserver
from windows_agent.ui_verifier import UIVerificationEngine


class Phase3VerificationTests(unittest.TestCase):
    def setUp(self):
        self.verifier = UIVerificationEngine(
            observer=UIStateObserver(),
            default_timeout=0,
        )

    def test_text_entry_requires_observable_value_change(self):
        action = {
            "action": "type_text",
            "capability": "windows_ui",
            "target": "Hello",
            "args": {"text": "Hello"},
        }
        before = {
            "focused_element": {
                "exists": True,
                "value": "",
            }
        }
        after = {
            "focused_element": {
                "exists": True,
                "value": "Hello",
            }
        }
        result = self.verifier.verify(
            action,
            before,
            after,
            {"success": True},
        )
        self.assertTrue(result["verified"])
        self.assertEqual(result["verification_level"], "state")

    def test_text_entry_does_not_report_success_without_postcondition(self):
        action = {
            "action": "type_text",
            "capability": "windows_ui",
            "target": "Hello",
            "args": {"text": "Hello"},
        }
        state = {"focused_element": {"exists": True, "value": ""}}
        result = self.verifier.verify(
            action,
            state,
            state,
            {"success": True},
        )
        self.assertFalse(result["verified"])

    def test_custom_postcondition_is_generic(self):
        action = {
            "action": "click_ui_element",
            "capability": "windows_ui",
            "target": "Search",
            "metadata": {
                "verification": {
                    "mode": "all",
                    "checks": [
                        {
                            "kind": "property",
                            "source": "target_element",
                            "field": "enabled",
                            "operator": "equals",
                            "value": True,
                        },
                        {
                            "kind": "property",
                            "source": "target_element",
                            "field": "name",
                            "operator": "equals",
                            "value": "Search",
                        },
                    ],
                }
            },
        }
        state = {
            "target_element": {
                "exists": True,
                "enabled": True,
                "name": "Search",
            }
        }
        result = self.verifier.verify(
            action,
            state,
            state,
            {"success": True},
        )
        self.assertTrue(result["verified"])

    def test_execution_failure_can_never_be_verified(self):
        action = {
            "action": "click_ui_element",
            "capability": "windows_ui",
            "target": "Search",
        }
        result = self.verifier.verify(
            action,
            {},
            {},
            {"success": False},
        )
        self.assertFalse(result["verified"])
        self.assertEqual(result["verification_level"], "execution_failed")


if __name__ == "__main__":
    unittest.main()
