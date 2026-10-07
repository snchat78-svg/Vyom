import io
import json
import os
import unittest
from unittest.mock import patch

import urllib.error

from ai_core.model_gateway import ModelGateway


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def read(self):
        return self._payload.encode("utf-8")


class LocalQwenProviderTests(unittest.TestCase):

    def _env(self, **updates):
        values = {
            "VYOM_AI_ENABLED": "true",
            "VYOM_AI_PROVIDER": "auto",
            "VYOM_AI_API_URL": "",
            "VYOM_AI_MODEL": "",
            "GEMINI_API_KEY": "",
            "GEMINI_MODEL": "gemini-3.6-flash",
            "QWEN_LOCAL_ENABLED": "true",
            "QWEN_LOCAL_API_URL": "http://127.0.0.1:11434/v1/chat/completions",
            "QWEN_LOCAL_MODEL": "qwen3.5:0.8b",
        }
        values.update(updates)
        return patch.dict(os.environ, values, clear=False)

    def test_auto_mode_exposes_gemini_then_local_qwen(self):
        with self._env(GEMINI_API_KEY="gem-key"):
            gateway = ModelGateway()
            candidates = gateway._provider_candidates()

        self.assertEqual(
            [item["provider"] for item in candidates],
            ["gemini", "local_qwen"],
        )
        self.assertEqual(candidates[1]["model"], "qwen3.5:0.8b")

    def test_explicit_gemini_endpoint_keeps_local_qwen_as_fallback(self):
        with self._env(
            GEMINI_API_KEY="gem-key",
            VYOM_AI_API_URL="https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
            VYOM_AI_MODEL="gemini-3.6-flash",
        ):
            gateway = ModelGateway()
            candidates = gateway._provider_candidates()

        self.assertEqual(
            [item["provider"] for item in candidates],
            ["gemini", "local_qwen"],
        )

    def test_forced_local_qwen_requires_no_real_api_key(self):
        with self._env(
            VYOM_AI_PROVIDER="local_qwen",
            GEMINI_API_KEY="",
        ):
            gateway = ModelGateway()

        self.assertTrue(gateway.is_available())
        status = gateway.provider_status()
        self.assertEqual(status["provider"], "local_qwen")
        self.assertEqual(status["model"], "qwen3.5:0.8b")
        self.assertEqual(status["fallbacks"], [])

    def test_complete_falls_back_from_gemini_429_to_local_qwen(self):
        model_payload = json.dumps({
            "choices": [{
                "message": {
                    "content": json.dumps({
                        "understood": True,
                        "goal": "hello",
                        "language": "english",
                        "complexity": "simple",
                        "route": "conversation",
                        "plan": [],
                    })
                }
            }]
        })
        calls = []

        def fake_urlopen(request, timeout):
            calls.append(request.full_url)
            if len(calls) == 1:
                raise urllib.error.HTTPError(
                    request.full_url,
                    429,
                    "Too Many Requests",
                    {},
                    io.BytesIO(b'{"error":"quota"}'),
                )
            return _FakeResponse(model_payload)

        with self._env(GEMINI_API_KEY="gem-key"):
            gateway = ModelGateway()
            with patch("urllib.request.urlopen", side_effect=fake_urlopen):
                result = gateway.complete("hello")

        self.assertTrue(result["success"])
        self.assertEqual(result["data"]["route"], "conversation")
        self.assertEqual(len(calls), 2)
        self.assertIn("generativelanguage.googleapis.com", calls[0])
        self.assertIn("127.0.0.1:11434", calls[1])

    def test_chat_falls_back_to_local_qwen(self):
        calls = []

        def fake_urlopen(request, timeout):
            calls.append(request.full_url)
            if len(calls) == 1:
                raise urllib.error.HTTPError(
                    request.full_url,
                    429,
                    "Too Many Requests",
                    {},
                    io.BytesIO(b'{"error":"quota"}'),
                )
            return _FakeResponse(
                '{"choices":[{"message":{"content":"LOCAL_QWEN_OK"}}]}'
            )

        with self._env(GEMINI_API_KEY="gem-key"):
            gateway = ModelGateway()
            with patch("urllib.request.urlopen", side_effect=fake_urlopen):
                result = gateway.chat("system", {"message": "hello"})

        self.assertTrue(result["success"])
        self.assertEqual(result["text"], "LOCAL_QWEN_OK")
        self.assertEqual(result["provider"], "local_qwen")
        self.assertEqual(len(calls), 2)


if __name__ == "__main__":
    unittest.main()
