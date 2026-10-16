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
    def test_click_ui_element_requires_observable_effect(self):
        action = {
            "action": "click_ui_element",
            "capability": "windows_ui",
            "target": "Send",
        }
        before = {
            "target_element": {"exists": True, "name": "Send", "focused": False},
            "focused_element": {"exists": True, "name": "Input", "value": "hello"},
            "ui_tree_signature": [{"name": "Send"}],
            "active_window": {"name": "Chat", "hwnd": 10},
        }
        unchanged = {
            "target_element": {"exists": True, "name": "Send", "focused": False},
            "focused_element": {"exists": True, "name": "Input", "value": "hello"},
            "ui_tree_signature": [{"name": "Send"}],
            "active_window": {"name": "Chat", "hwnd": 10},
        }
        result = self.verifier.verify(action, before, unchanged, {"success": True})
        self.assertFalse(result["verified"])

    def test_click_ui_element_passes_when_target_state_changes(self):
        action = {
            "action": "click_ui_element",
            "capability": "windows_ui",
            "target": "Send",
        }
        before = {
            "target_element": {"exists": True, "name": "Send", "focused": False},
            "focused_element": {"exists": True, "name": "Input", "value": "hello"},
        }
        after = {
            "target_element": {"exists": True, "name": "Send", "focused": True},
            "focused_element": {"exists": True, "name": "Send"},
        }
        result = self.verifier.verify(action, before, after, {"success": True})
        self.assertTrue(result["verified"])

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


    def test_missing_negative_postcondition_evidence_does_not_pass(self):
        action = {
            "action": "click_ui_element",
            "target": "Send",
            "metadata": {
                "verification": {
                    "mode": "all",
                    "checks": [
                        {
                            "kind": "property",
                            "source": "target_element",
                            "field": "name",
                            "operator": "not_equals",
                            "value": "Send",
                        },
                        {"kind": "element_not_exists", "source": "target_element"},
                    ],
                }
            },
        }
        result = self.verifier.verify(action, {}, {}, {"success": True})
        self.assertFalse(result["verified"])

    def test_missing_execution_result_is_not_assumed_success(self):
        action = {"action": "click_ui_element", "target": "Search"}
        before = {
            "target_element": {"exists": True, "name": "Search"},
            "ui_tree_signature": [{"name": "Search"}],
        }
        after = {
            "target_element": {"exists": True, "name": "Search", "focused": True},
            "ui_tree_signature": [{"name": "Search", "focused": True}],
        }
        result = self.verifier.verify(action, before, after)
        self.assertFalse(result["verified"])
        self.assertEqual(result["verification_level"], "execution_failed")

    def test_empty_after_tree_is_not_evidence_of_ui_transition(self):
        action = {"action": "click", "target": ""}
        before = {
            "active_window": {"exists": True, "name": "Example", "hwnd": 7},
            "focused_element": {"exists": True, "name": "Editor"},
            "ui_tree_signature": [{"name": "Search"}],
        }
        after = {
            "active_window": {"exists": True, "name": "Example", "hwnd": 7},
            "focused_element": {"exists": True, "name": "Editor"},
            "ui_tree_signature": [],
        }
        result = self.verifier.verify(action, before, after, {"success": True})
        self.assertFalse(result["verified"])


if __name__ == "__main__":
    unittest.main()
