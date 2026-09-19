"""
Project : Vyom AI
Version : 1.0
Module  : Model Gateway

Purpose:
    Central transport gateway between Vyom's reasoning system and an
    external/local OpenAI-compatible AI model endpoint.

IMPORTANT:
    - This module does NOT execute computer commands.
    - This module does NOT modify Vyom's source code.
    - This module only sends reasoning requests and returns structured AI output.
    - API credentials are read from environment variables.
"""

import json
import os
import urllib.error
import urllib.request


class ModelGateway:

    def __init__(self, api_key=None, api_url=None, model=None, timeout=60):
        self.api_key = api_key or os.environ.get("VYOM_AI_API_KEY", "")
        self.api_url = api_url or os.environ.get("VYOM_AI_API_URL", "")
        self.model = model or os.environ.get("VYOM_AI_MODEL", "")
        self.timeout = max(5, int(timeout))

    def is_available(self):
        if not self.api_url or not self.model:
            return False

        local = self.api_url.lower().startswith((
            "http://127.0.0.1",
            "http://localhost",
            "http://[::1]",
        ))
        return bool(self.api_key or local)

    def _system_prompt(self):
        return """
You are the reasoning brain of Vyom AI.

Vyom is a personal autonomous computer agent.

Your job is to:
1. Understand the user's actual goal.
2. Consider the available capabilities.
3. Break complex goals into logical steps.
4. Decide which capability/tool is required.
5. Produce a safe structured plan.
6. Never claim that an action was executed.
7. Never generate instructions to disable security.
8. Never request unnecessary permissions.
9. Never execute arbitrary code.
10. If a required capability does not exist, explicitly report that a new capability is required.

Return ONLY valid JSON.

For multi-step executable goals, use route="mission".
Never include tool implementations, Python code, shell commands, or claims that an action was executed.

Expected structure:
{
    "understood": true,
    "goal": "user goal",
    "language": "hindi|english|hinglish",
    "complexity": "simple|medium|complex",
    "analysis": "short reasoning summary",
    "route": "existing_tools|mission|capability|missing_capability|conversation",
    "capability": "",
    "plan": [
        {
            "step": 1,
            "type": "action",
            "description": "what should happen",
            "capability": "",
            "intent": null
        }
    ],
    "needs_confirmation": false,
    "reason": ""
}

The plan must describe decisions, not pretend that actions already happened.
"""

    def _build_request(self, goal, context=None, capabilities=None, previous_result=None):
        payload = {
            "goal": str(goal or ""),
            "context": context if isinstance(context, dict) else {},
            "capabilities": capabilities if isinstance(capabilities, list) else [],
            "previous_result": previous_result,
        }
        return {
            "model": self.model,
            "messages": [
                {"role": "system", "content": self._system_prompt()},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ],
            "temperature": 0.2,
        }

    def complete(self, goal, context=None, capabilities=None, previous_result=None):
        if not self.is_available():
            return {
                "success": False,
                "available": False,
                "error": "AI model gateway is not configured.",
            }

        data = json.dumps(
            self._build_request(goal, context, capabilities, previous_result),
            ensure_ascii=False,
        ).encode("utf-8")

        request = urllib.request.Request(self.api_url, data=data, method="POST")
        request.add_header("Content-Type", "application/json")

        if self.api_key:
            request.add_header("Authorization", "Bearer " + self.api_key)

        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as error:
            try:
                details = error.read().decode("utf-8")
            except Exception:
                details = str(error)
            return {
                "success": False,
                "available": True,
                "error": f"AI model HTTP error: {error.code} {details}",
            }
        except Exception as error:
            return {
                "success": False,
                "available": True,
                "error": str(error),
            }

        try:
            provider_response = json.loads(raw)
        except Exception as error:
            return {
                "success": False,
                "available": True,
                "error": ("AI model returned invalid JSON.", str(error)),
                "raw": raw,
            }

        return self._extract_response(provider_response)

    def _extract_response(self, response):
        if not isinstance(response, dict):
            return {"success": False, "error": "Invalid model response."}

        choices = response.get("choices", [])
        if choices:
            try:
                content = choices[0].get("message", {}).get("content", "")
            except Exception:
                content = ""

            parsed = self._parse_json(content)
            if parsed is not None:
                return {"success": True, "available": True, "data": parsed}

            return {
                "success": False,
                "available": True,
                "error": "Model response was not valid JSON.",
                "raw": content,
            }

        if "understood" in response or "route" in response or "plan" in response:
            return {"success": True, "available": True, "data": response}

        return {
            "success": False,
            "available": True,
            "error": "Unknown AI model response format.",
        }

    def _parse_json(self, content):
        if not content:
            return None

        text = str(content).strip()

        try:
            return json.loads(text)
        except Exception:
            pass

        if text.startswith("```"):
            lines = text.splitlines()
            if len(lines) >= 3:
                cleaned = "\n".join(lines[1:-1])
                try:
                    return json.loads(cleaned)
                except Exception:
                    pass

        return None
