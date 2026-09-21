import unittest

from ai_core.deep_reasoner import DeepReasoner


class FakeCompiler:
    def __init__(self):
        self.last_compilation = None

    def compile(self, goal, intent=None, context=None):
        self.last_compilation = {"objective": goal, "complexity": "simple", "reason": "fallback"}
        return {
            "objective": goal,
            "complexity": "simple",
            "reason": "fallback",
            "suggested_intents": [],
        }


class FakeGateway:
    def __init__(self, result):
        self.result = result
        self.calls = 0

    def is_available(self):
        return True

    def reason(self, **kwargs):
        self.calls += 1
        return self.result

    def reset(self):
        pass


class DeepReasonerGatewayTests(unittest.TestCase):
    def test_real_model_result_passes_through_gateway(self):
        gateway = FakeGateway({
            "success": True,
            "available": True,
            "source": "ai_reasoning_gateway",
            "data": {
                "understood": True,
                "goal": "open notepad and calculator",
                "language": "english",
                "complexity": "medium",
                "route": "mission",
                "plan": [
                    {"step": 1, "type": "execute_existing_intent", "intent": {"intent": "open", "target": "notepad"}},
                    {"step": 2, "type": "execute_existing_intent", "intent": {"intent": "open", "target": "calculator"}},
                ],
            },
        })
        reasoner = DeepReasoner(reasoning_gateway=gateway, goal_compiler=FakeCompiler())
        result = reasoner.reason("open notepad and calculator")
        self.assertTrue(result["success"])
        self.assertEqual(result["source"], "ai_reasoning_gateway")
        self.assertEqual(gateway.calls, 1)

    def test_invalid_gateway_result_falls_back_without_execution(self):
        gateway = FakeGateway({
            "success": False,
            "available": True,
            "stage": "reasoning_validation_error",
            "error": "bad output",
        })
        reasoner = DeepReasoner(reasoning_gateway=gateway, goal_compiler=FakeCompiler())
        result = reasoner.reason("some complex task")
        self.assertTrue(result["success"])
        self.assertEqual(result["source"], "local_reasoner")
        self.assertEqual(gateway.calls, 1)


if __name__ == "__main__":
    unittest.main()
