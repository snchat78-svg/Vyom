import unittest

from ai_core.model_gateway import ModelGateway


class ModelGatewayContextTests(unittest.TestCase):
    def test_prompt_mentions_live_context_and_mixed_missions(self):
        prompt = ModelGateway(
            api_url="http://localhost:1234/v1/chat/completions",
            model="test",
        )._system_prompt()
        self.assertIn("live working state", prompt)
        self.assertIn("legacy existing-tool steps and generic action steps", prompt)
        self.assertIn("Preserve their exact order and dependencies", prompt)

    def test_prompt_forbids_executable_code(self):
        prompt = ModelGateway(
            api_url="http://localhost:1234/v1/chat/completions",
            model="test",
        )._system_prompt()
        self.assertIn("Never return Python", prompt)


if __name__ == "__main__":
    unittest.main()

