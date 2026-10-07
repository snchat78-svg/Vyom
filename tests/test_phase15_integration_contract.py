import os
import tempfile
import unittest

from ai_core.context_action_compiler import ContextActionCompiler
from ai_core.model_gateway import ModelGateway


class Phase15IntegrationContractTests(unittest.TestCase):
    def test_offline_compound_goal_keeps_all_steps(self):
        compiler = ContextActionCompiler()
        result = compiler.compile(
            "open Notepad and type Shambhu Lal",
            {"current_app": "", "current_target": ""},
        )
        self.assertTrue(result["complete"])
        self.assertEqual(
            [step["type"] for step in result["plan"]],
            ["execute_existing_intent", "action"],
        )
        self.assertEqual(result["plan"][0]["intent"]["intent"], "open")
        self.assertEqual(result["plan"][1]["action"], "type_text")
        self.assertEqual(result["plan"][1]["args"]["text"], "Shambhu Lal")
        self.assertEqual(result["plan"][1]["depends_on"], [result["plan"][0]["id"]])

    def test_runtime_env_can_supply_ai_configuration(self):
        old_values = {
            key: os.environ.get(key)
            for key in ("VYOM_ENV_FILE", "GEMINI_API_KEY", "GEMINI_MODEL")
        }
        try:
            with tempfile.TemporaryDirectory() as directory:
                path = os.path.join(directory, "vyom.env")
                with open(path, "w", encoding="utf-8") as handle:
                    handle.write("GEMINI_API_KEY=test-key\n")
                    handle.write("GEMINI_MODEL=test-model\n")
                for key in old_values:
                    os.environ.pop(key, None)
                os.environ["VYOM_ENV_FILE"] = path
                gateway = ModelGateway(api_url="http://localhost:1234/v1/chat/completions")
                self.assertEqual(gateway.api_key, "test-key")
                self.assertEqual(gateway.model, "test-model")
                self.assertTrue(gateway.is_available())
        finally:
            for key, value in old_values.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value


if __name__ == "__main__":
    unittest.main()
