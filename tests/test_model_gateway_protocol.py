import unittest

from ai_core.model_gateway import ModelGateway


class ModelGatewayProtocolTests(unittest.TestCase):

    def test_prompt_describes_generic_action_protocol(self):
        gateway = ModelGateway(api_url="http://localhost:1234/v1/chat/completions", model="test")
        prompt = gateway._system_prompt()
        self.assertIn('"action": "generic_operation_name"', prompt)
        self.assertIn("Never return Python", prompt)
        self.assertIn("generic action protocol", prompt.lower())

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


if __name__ == "__main__":
    unittest.main()
