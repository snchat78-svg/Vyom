import unittest

from ai_core.response_engine import ResponseEngine


class FakeModelGateway:
    def __init__(self):
        self.chat_calls = 0
        self.availability_calls = 0

    def is_available(self):
        self.availability_calls += 1
        return True

    def chat(self, *args, **kwargs):
        self.chat_calls += 1
        return {"success": True, "text": "model response"}


class FakeKnowledge:
    def __init__(self, answer=None):
        self.result = answer or {
            "success": True,
            "answer": "भारत की राजधानी नई दिल्ली है।\nस्रोत: विकिपीडिया (हिन्दी) — भारत",
            "sources": [{"title": "भारत", "site": "हिन्दी विकिपीडिया"}],
        }
        self.calls = []

    def answer(self, question, preferred_language="hi"):
        self.calls.append((question, preferred_language))
        return self.result


class ResponseEngineModelBudgetTests(unittest.TestCase):
    def test_execution_result_does_not_trigger_duplicate_model_call(self):
        gateway = FakeModelGateway()
        engine = ResponseEngine(model_gateway=gateway, knowledge_lookup=FakeKnowledge())

        result = engine.format(
            command="gugal krom open",
            result={"success": True, "stage": "verified", "message": "opened successfully"},
            intent={"intent": "open", "target": "Google Chrome"},
        )

        self.assertTrue(result)
        self.assertEqual(gateway.chat_calls, 0)

    def test_information_question_uses_web_knowledge_and_never_calls_model(self):
        gateway = FakeModelGateway()
        knowledge = FakeKnowledge()
        engine = ResponseEngine(model_gateway=gateway, knowledge_lookup=knowledge)

        result = engine.format(
            command="bharat ki rajadhani kya hai",
            result={"success": True, "stage": "conversation"},
            intent={"intent": "unknown", "target": "bharat ki rajadhani kya hai"},
        )

        self.assertIn("नई दिल्ली", result)
        self.assertIn("स्रोत:", result)
        self.assertEqual(knowledge.calls, [("bharat ki rajadhani kya hai", "hi")])
        self.assertEqual(gateway.chat_calls, 0)
        self.assertEqual(gateway.availability_calls, 0)

    def test_information_question_without_network_falls_back_in_hindi_without_model(self):
        gateway = FakeModelGateway()
        knowledge = FakeKnowledge({
            "success": False, "answer": "", "sources": [],
        })
        engine = ResponseEngine(model_gateway=gateway, knowledge_lookup=knowledge)

        result = engine.format(
            command="what is photosynthesis?",
            result={"success": True, "stage": "conversation"},
            intent={"intent": "unknown", "target": "what is photosynthesis?"},
        )

        self.assertIn("वेबसाइट", result)
        self.assertEqual(gateway.chat_calls, 0)
        self.assertEqual(gateway.availability_calls, 0)

    def test_romanized_hindi_is_detected_as_hindi(self):
        engine = ResponseEngine(model_gateway=FakeModelGateway(), knowledge_lookup=FakeKnowledge())
        self.assertEqual(engine.detect_language("namaste bhaiya kaise ho"), "hindi")


if __name__ == "__main__":
    unittest.main()
