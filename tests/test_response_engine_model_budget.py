import unittest

from ai_core.response_engine import ResponseEngine


class FakeModelGateway:
    def __init__(self):
        self.chat_calls = 0

    def is_available(self):
        return True

    def chat(self, *args, **kwargs):
        self.chat_calls += 1
        return {
            "success": True,
            "text": "model response",
        }


class ResponseEngineModelBudgetTests(unittest.TestCase):
    def test_execution_result_does_not_trigger_duplicate_model_call(self):
        gateway = FakeModelGateway()
        engine = ResponseEngine(model_gateway=gateway)

        result = engine.format(
            command="gugal krom open",
            result={
                "success": True,
                "stage": "verified",
                "message": "opened successfully",
            },
            intent={"intent": "open", "target": "Google Chrome"},
        )

        self.assertTrue(result)
        self.assertEqual(gateway.chat_calls, 0)

    def test_conversation_result_uses_model_for_natural_answer(self):
        gateway = FakeModelGateway()
        engine = ResponseEngine(model_gateway=gateway)

        result = engine.format(
            command="bharat ki rajadhani kya hai",
            result={
                "success": True,
                "stage": "conversation",
            },
            intent={"intent": "unknown", "target": "bharat ki rajadhani kya hai"},
        )

        self.assertEqual(result, "model response")
        self.assertEqual(gateway.chat_calls, 1)


if __name__ == "__main__":
    unittest.main()
