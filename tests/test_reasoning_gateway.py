"""Offline tests for the AI Reasoning Gateway v1.0."""

import unittest

from ai_core.reasoning_gateway import AIReasoningGateway


class FakeModelGateway:
    def __init__(self, payload):
        self.payload = payload
        self.calls = 0

    def is_available(self):
        return True

    def complete(self, **kwargs):
        self.calls += 1
        return {
            "success": True,
            "available": True,
            "data": self.payload,
        }


class ReasoningGatewayTests(unittest.TestCase):

    def valid_payload(self):
        return {
            "understood": True,
            "goal": "Open notepad and calculator",
            "language": "english",
            "complexity": "medium",
            "analysis": "Two independent application launches.",
            "route": "mission",
            "capability": "",
            "plan": [
                {
                    "step": 1,
                    "type": "execute_existing_intent",
                    "intent": {"intent": "open", "target": "notepad"},
                },
                {
                    "step": 2,
                    "type": "execute_existing_intent",
                    "intent": {"intent": "open", "target": "calculator"},
                },
            ],
            "needs_confirmation": False,
            "reason": "Known applications can be handled by existing tools.",
        }

    def test_valid_model_output_is_accepted(self):
        fake = FakeModelGateway(self.valid_payload())
        gateway = AIReasoningGateway(fake)
        result = gateway.reason("Open notepad and calculator")
        self.assertTrue(result["success"])
        self.assertEqual(result["source"], "ai_reasoning_gateway")
        self.assertEqual(len(result["data"]["plan"]), 2)
        self.assertEqual(fake.calls, 1)

    def test_missing_required_field_is_rejected(self):
        payload = self.valid_payload()
        del payload["plan"]
        gateway = AIReasoningGateway(FakeModelGateway(payload))
        result = gateway.reason("complex task")
        self.assertFalse(result["success"])
        self.assertEqual(result["stage"], "reasoning_validation_error")

    def test_unknown_route_is_rejected(self):
        payload = self.valid_payload()
        payload["route"] = "execute_windows"
        gateway = AIReasoningGateway(FakeModelGateway(payload))
        result = gateway.reason("complex task")
        self.assertFalse(result["success"])

    def test_invalid_intent_shape_is_rejected(self):
        payload = self.valid_payload()
        payload["plan"][0]["intent"] = "open notepad"
        gateway = AIReasoningGateway(FakeModelGateway(payload))
        result = gateway.reason("complex task")
        self.assertFalse(result["success"])


if __name__ == "__main__":
    unittest.main()
