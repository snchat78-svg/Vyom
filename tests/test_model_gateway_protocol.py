import unittest

from ai_core.model_gateway import ModelGateway


class ModelGatewayProtocolTests(unittest.TestCase):

    def test_prompt_describes_generic_action_protocol(self):
        gateway = ModelGateway(api_url="http://localhost:1234/v1/chat/completions", model="test")
        prompt = gateway._system_prompt()
        self.assertIn('"action": "generic_operation_name"', prompt)
        self.assertIn("Never return Python", prompt)
        self.assertIn("generic action protocol", prompt.lower())
        self.assertIn("Interpret natural paraphrases", prompt)

    def test_request_keeps_capabilities_as_data(self):
        gateway = ModelGateway(
            api_url="http://localhost:1234/v1/chat/completions",
            model="test",
        )
        request = gateway._build_request(
            "do something",
            capabilities=[{"name": "windows_ui", "actions": ["click_control"]}],
        )
        self.assertEqual(request["model"], "test")
        self.assertEqual(request["messages"][1]["role"], "user")

    def test_gemini_request_uses_low_reasoning_effort(self):
        gateway = ModelGateway(
            api_url="https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
            model="gemini-3.6-flash",
            api_key="test-key",
        )
        request = gateway._build_request("make a plan")
        self.assertEqual(request["reasoning_effort"], "low")

    def test_json_parser_accepts_provider_preamble(self):
        gateway = ModelGateway(
            api_url="http://localhost:1234/v1/chat/completions",
            model="test",
        )
        parsed = gateway._parse_json(
            'Here is the plan:\\n{"understood":true,"route":"conversation","plan":[]}'
        )
        self.assertIsInstance(parsed, dict)
        self.assertEqual(parsed["route"], "conversation")


if __name__ == "__main__":
    unittest.main()
