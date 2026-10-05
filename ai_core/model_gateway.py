"""
Project : Vyom AI
Version : 1.1
Module  : Model Gateway

Purpose:
    Central transport gateway between Vyom's reasoning system and an
    external/local OpenAI-compatible AI model endpoint.

IMPORTANT:
    - This module does NOT execute computer commands.
    - This module does NOT modify Vyom's source code.
    - This module only sends reasoning requests and returns structured AI output.
    - API credentials are read from environment variables.
    - Generic action plans are data-only and must be validated downstream.
"""

import json
import os
import sys
import urllib.error
import urllib.request

from ai_core.logger import log


class ModelGateway:

    @staticmethod
    def _load_runtime_env():
        """Load optional user-local AI settings without shipping secrets in the EXE."""
        candidates = []
        explicit = os.environ.get("VYOM_ENV_FILE", "").strip()
        if explicit:
            candidates.append(explicit)
        executable_dir = os.path.dirname(os.path.abspath(sys.executable))
        module_dir = os.path.dirname(os.path.abspath(__file__))
        candidates.extend([
            os.path.join(executable_dir, "vyom.env"),
            os.path.join(module_dir, "vyom.env"),
            os.path.join(os.getcwd(), "vyom.env"),
            os.path.join(executable_dir, ".env"),
            os.path.join(os.getcwd(), ".env"),
        ])
        seen = set()
        for path in candidates:
            path = os.path.abspath(path)
            if path in seen or not os.path.isfile(path):
                continue
            seen.add(path)
            try:
                with open(path, "r", encoding="utf-8") as handle:
                    for line in handle:
                        value = line.strip()
                        if not value or value.startswith("#") or "=" not in value:
                            continue
                        key, raw = value.split("=", 1)
                        key = key.strip()
                        raw = raw.strip()
                        if not key or key in os.environ:
                            continue
                        if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in {chr(34), chr(39)}:
                            raw = raw[1:-1]
                        os.environ[key] = raw
            except Exception:
                continue

    def __init__(self, api_key=None, api_url=None, model=None, timeout=20):
        self._load_runtime_env()
        self.api_key = api_key or os.environ.get("VYOM_AI_API_KEY", "") or os.environ.get("GEMINI_API_KEY", "")
        self.api_url = api_url or os.environ.get("VYOM_AI_API_URL", "")
        self.model = model or os.environ.get("VYOM_AI_MODEL", "")
        self.enabled = os.environ.get("VYOM_AI_ENABLED", "true").strip().lower() not in {"0", "false", "no", "off"}

        # If no custom OpenAI-compatible endpoint is configured, use the
        # official Gemini OpenAI-compatible REST endpoint when GEMINI_API_KEY
        # is present. No provider secret is stored in source code.
        if not self.api_url and os.environ.get("GEMINI_API_KEY", ""):
            self.api_url = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
        if not self.model and os.environ.get("GEMINI_API_KEY", ""):
            self.model = os.environ.get("GEMINI_MODEL", "gemini-3.6-flash")
        # Keep network reasoning bounded so a stalled provider cannot freeze
        # the voice/executor session on low-resource machines.
        self.timeout = min(20, max(5, int(timeout)))

    def provider_status(self):
        url = str(self.api_url or "").lower()
        if "generativelanguage.googleapis.com" in url:
            provider = "gemini"
        elif url:
            provider = "custom"
        else:
            provider = "none"

        return {
            "provider": provider,
            "enabled": bool(self.enabled),
            "configured": bool(self.api_key or url.startswith(("http://127.0.0.1", "http://localhost", "http://[::1]"))),
            "available": bool(self.is_available()),
            "model": self.model or "",
        }

    def is_available(self):
        if not self.enabled:
            return False
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
10. Never return Python, shell, PowerShell, JavaScript, tool objects, callables, or other executable implementation details.
11. Use the generic action protocol for actions. The action name is a capability operation, not a user command/intent.
12. When an existing capability cannot safely satisfy a requested action, route to "missing_capability" rather than inventing an implementation.
13. Treat the supplied conversation/session context as live working state. A short follow-up can continue the current work instead of starting from a blank state.
14. Distinguish a new goal from a continuation using the user's language and the supplied current state; do not discard the current target merely because a new message arrived.
15. Interpret natural paraphrases, colloquial Hindi/Hinglish, speech-transcription errors, pronouns, ellipsis, and ordinary conversational phrasing by meaning rather than requiring exact command words.
16. Do not treat application names, filenames, user names, or other targets as fixed vocabulary. Infer their role from the sentence and supplied context; keep targets data-driven and generic.
17. Resolve the meaning of the complete utterance before selecting an operation. Do not classify a request from a single keyword or a fixed phrase.
18. Resolve references such as "it", "this", "that", "the one we were using", "उसमें", "इसे", "वो वाला" against the supplied conversation and world state. If a reference has multiple plausible targets, ask for clarification instead of guessing.
19. Treat speech-recognition distortions as uncertain surface text. Infer the intended entity from the whole sentence and context; do not require exact vocabulary or exact spelling.
20. Prefer generic Action Schema operations whenever an advertised capability can satisfy the semantic goal. Use legacy execute_existing_intent only for backward-compatible routes that are explicitly supported; do not create new legacy intent names for new language patterns.
21. A mission may contain both legacy existing-tool steps and generic action steps. Preserve their exact order and dependencies. Legacy steps are compatibility steps; do not invent new legacy intents.
22. For a follow-up that only operates on the current focused window, prefer a generic action and use the current context as the precondition.
23. For natural-language requests, preserve user-provided data exactly in args/target where possible; separate the requested operation from the data being operated on.
24. If the goal requires several actions, generate an ordered mission whose dependencies express the real sequence. Do not collapse multiple semantic steps into one hard-coded command.
25. After a previous execution failure, treat the supplied previous_result and fresh world state as evidence. Re-evaluate the goal and generate a new plan rather than blindly repeating the failed plan.

Return ONLY valid JSON.

For multi-step executable goals, use route="mission".
A mission can mix existing-tool compatibility steps and generic capability actions when both are required. Preserve the sequence exactly.
Never collapse a multi-step request to only the first recognizable action. Every requested stage must remain represented in the ordered plan.
Resolve references such as "it", "this", "that", "usme", "isme", "there", and similar phrases from the supplied context when the reference is unambiguous. Do not invent a target when it is ambiguous.
For natural-language information questions, use route="conversation". Do not turn an information question into a missing capability request.
For a single action that an available capability can support, use route="existing_tools" or "capability" according to the supplied capability information.
The plan describes intended actions only; it must never claim that an action already happened.

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
            "id": "action_1",
            "description": "what should happen",
            "action": "generic_operation_name",
            "capability": "capability_name",
            "target": "target if applicable",
            "args": {},
            "preconditions": [],
            "postconditions": [],
            "depends_on": []
        }
    ],
    "needs_confirmation": false,
    "reason": "",
    "references": [],
    "ambiguities": [],
    "semantic_interpretation": ""
}

Use only JSON-safe values in actions. Do not put executable code in args.
"""

    def _build_request(self, goal, context=None, capabilities=None, previous_result=None):
        payload = {
            "goal": str(goal or ""),
            "context": context if isinstance(context, dict) else {},
            "capabilities": capabilities if isinstance(capabilities, list) else [],
            "previous_result": previous_result,
        }
        request = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": self._system_prompt()},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ],
            "temperature": 0.2,
        }

        # Gemini's OpenAI-compatible endpoint supports bounded reasoning.
        # Low reasoning leaves more response budget for Vyom's structured plan.
        if "generativelanguage.googleapis.com" in str(self.api_url or "").lower():
            request["reasoning_effort"] = "low"

        return request

    def complete(    def complete(self, goal, context=None, capabilities=None, previous_result=None):
        status = self.provider_status()
        log(
            "[AI] REASONING PROVIDER: provider=%s enabled=%s configured=%s available=%s model=%s"
            % (
                status["provider"],
                status["enabled"],
                status["configured"],
                status["available"],
                status["model"] or "none",
            )
        )

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

        log("[AI] REASONING REQUEST START")
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

        log("[AI] REASONING REQUEST HTTP RESPONSE RECEIVED")
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

    def chat(self, system_prompt, user_payload, temperature=0.4):
        """Provider-independent plain-text model call for conversational replies.

        This is intentionally separate from complete(), whose contract is
        strict structured JSON for action reasoning.
        """
        if not self.is_available():
            return {"success": False, "available": False, "error": "AI model gateway is not configured."}

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": str(system_prompt or "")},
                {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
            ],
            "temperature": float(temperature),
        }
        if "generativelanguage.googleapis.com" in str(self.api_url or "").lower():
            payload["reasoning_effort"] = "low"
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
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
            return {"success": False, "available": True, "error": f"AI model HTTP error: {error.code} {details}"}
        except Exception as error:
            return {"success": False, "available": True, "error": str(error)}

        try:
            provider_response = json.loads(raw)
            choices = provider_response.get("choices", [])
            content = choices[0].get("message", {}).get("content", "") if choices else ""
            if content:
                return {"success": True, "available": True, "text": str(content).strip()}
            return {"success": False, "available": True, "error": "AI model returned an empty response."}
        except Exception as error:
            return {"success": False, "available": True, "error": str(error)}

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
                cleaned = "
".join(lines[1:-1]).strip()
                try:
                    return json.loads(cleaned)
                except Exception:
                    pass

        # Tolerate a brief provider preamble/trailing note around a JSON
        # object. The Reasoning Gateway still performs authoritative schema
        # validation after parsing.
        decoder = json.JSONDecoder()
        for index, char in enumerate(text):
            if char != "{":
                continue
            try:
                value, _ = decoder.raw_decode(text[index:])
                if isinstance(value, dict):
                    return value
            except (json.JSONDecodeError, TypeError, ValueError):
                continue

        return None
