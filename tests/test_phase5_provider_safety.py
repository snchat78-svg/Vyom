import unittest

from ai_core.model_gateway import ModelGateway


class Phase5ProviderSafetyTests(unittest.TestCase):
    def test_gateway_can_be_disabled_without_removing_local_agent(self):
        gateway = ModelGateway(
            api_url="http://localhost:1/v1/chat/completions",
            model="test",
        )
        gateway.enabled = False
        self.assertFalse(gateway.is_available())

    def test_no_secret_is_embedded_in_gateway_source_contract(self):
        gateway = ModelGateway(
            api_url="http://localhost:1/v1/chat/completions",
            model="test",
        )
        self.assertFalse(hasattr(gateway, "hard_coded_api_key"))


if __name__ == "__main__":
    unittest.main()
