"""Local Qwen provider configuration for Vyom.

The provider intentionally contains no executor/tool logic.  Ollama exposes
Qwen through an OpenAI-compatible local HTTP endpoint; ModelGateway owns the
request/response transport and provider fallback policy.
"""

import os


class LocalQwenProvider:
    """Describe a local Qwen endpoint without adding a new execution path."""

    DEFAULT_API_URL = "http://127.0.0.1:11434/v1/chat/completions"
    DEFAULT_MODEL = "qwen3.5:0.8b"

    def __init__(self, enabled=None, api_url=None, model=None):
        env_enabled = os.environ.get("QWEN_LOCAL_ENABLED", "false")
        if enabled is None:
            enabled = env_enabled.strip().lower() not in {"0", "false", "no", "off"}

        self.enabled = bool(enabled)
        self.api_url = str(
            api_url or os.environ.get("QWEN_LOCAL_API_URL", self.DEFAULT_API_URL)
        ).strip()
        self.model = str(
            model or os.environ.get("QWEN_LOCAL_MODEL", self.DEFAULT_MODEL)
        ).strip()

    @property
    def name(self):
        return "local_qwen"

    def is_local_url(self):
        return self.api_url.lower().startswith(
            ("http://127.0.0.1", "http://localhost", "http://[::1]")
        )

    def is_configured(self):
        return bool(self.enabled and self.api_url and self.model and self.is_local_url())

    def status(self):
        return {
            "provider": self.name,
            "enabled": self.enabled,
            "configured": self.is_configured(),
            "available": self.is_configured(),
            "model": self.model,
            "api_url": self.api_url,
        }
