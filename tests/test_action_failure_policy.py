import unittest

from ai_core.action_failure_policy import ActionFailurePolicy


class ActionFailurePolicyTests(unittest.TestCase):
    def test_known_pre_dispatch_mismatch_allows_bounded_retry(self):
        policy = ActionFailurePolicy.classify({
            "success": False,
            "stage": "execution_failed",
            "result": {
                "success": False,
                "stage": "ui_target_context_mismatch",
                "message": "The active target changed.",
            },
        })
        self.assertEqual(policy["category"], "pre_dispatch_failure")
        self.assertTrue(policy["retry_same_action"])
        self.assertFalse(policy["stop_mission"])
        self.assertTrue(policy["reobserve_before_retry"])

    def test_ambiguous_target_stops_and_requests_clarification(self):
        policy = ActionFailurePolicy.classify({
            "success": False,
            "stage": "execution_failed",
            "result": {
                "success": False,
                "stage": "ui_target_ambiguous",
                "message": "I found multiple plausible buttons.",
            },
        })
        self.assertEqual(policy["category"], "target_ambiguous")
        self.assertTrue(policy["requires_user_input"])
        self.assertFalse(policy["retry_same_action"])
        self.assertTrue(policy["stop_mission"])
        self.assertIn("multiple plausible", policy["user_message"])

    def test_unsupported_operation_stops_without_repeating(self):
        policy = ActionFailurePolicy.classify({
            "success": False,
            "stage": "execution_failed",
            "result": {
                "success": False,
                "stage": "ui_pattern_unsupported",
                "message": "This control has no Invoke pattern.",
            },
        })
        self.assertEqual(policy["category"], "unsupported_operation")
        self.assertFalse(policy["retry_same_action"])
        self.assertTrue(policy["stop_mission"])

    def test_post_dispatch_verification_failure_never_retries_same_action(self):
        policy = ActionFailurePolicy.classify({
            "success": False,
            "stage": "verification_failed",
            "result": {
                "success": False,
                "stage": "verification_failed",
                "verification": {
                    "verified": False,
                    "verification_level": "post_action_observation_unavailable",
                    "reason": "observer unavailable",
                },
            },
            "verification": {"verified": False},
        })
        self.assertEqual(policy["category"], "outcome_uncertain")
        self.assertFalse(policy["retry_same_action"])
        self.assertTrue(policy["stop_mission"])
        self.assertIn("without repeating", policy["user_message"])

    def test_unknown_failure_is_conservatively_classified_as_uncertain(self):
        policy = ActionFailurePolicy.classify({
            "success": False,
            "stage": "executor_returned_unexpected_error",
            "message": "unknown",
        })
        self.assertEqual(policy["category"], "unknown_outcome")
        self.assertFalse(policy["retry_same_action"])
        self.assertTrue(policy["stop_mission"])


if __name__ == "__main__":
    unittest.main()
