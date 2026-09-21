"""
Project : Vyom AI
Version : 1.0
Module  : Capability Executor

Purpose:
    Bridge validated generic actions to registered runtime capability
    providers without converting them into fixed user intents.

Safety:
    - Model output is treated as data only.
    - ActionValidator runs before a provider is called.
    - CapabilityRegistry stores metadata, not executable objects.
    - Runtime provider objects stay inside this executor.
    - No arbitrary code from a model can be executed here.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from ai_core.action_validator import ActionValidator
from ai_core.capability_registry import CapabilityRegistry
from ai_core.capability_resolver import CapabilityResolver


class CapabilityExecutor:
    """Execute a validated generic action through an internal provider."""

    def __init__(
        self,
        registry: Optional[CapabilityRegistry] = None,
        validator: Optional[ActionValidator] = None,
    ):
        self.registry = registry or CapabilityRegistry()
        self.validator = validator or ActionValidator(max_steps=10)
        self.resolver = CapabilityResolver(self.registry)
        self._providers: Dict[str, Any] = {}

    def register(
        self,
        provider: Any,
        enabled: bool = True,
        priority: int = 100,
    ) -> bool:
        if provider is None:
            return False

        name = str(
            getattr(provider, "name", "")
            or getattr(provider, "capability_name", "")
            or ""
        ).strip().lower()
        if not name:
            return False

        supported = getattr(provider, "supported_actions", None)
        actions = supported() if callable(supported) else supported
        if not isinstance(actions, (list, tuple, set)):
            return False

        description = str(
            getattr(provider, "description", "") or ""
        ).strip()

        if not self.registry.register(
            name=name,
            description=description,
            actions=actions,
            enabled=enabled,
            priority=priority,
        ):
            return False

        self._providers[name] = provider
        return True

    def unregister(self, name: str) -> bool:
        key = str(name or "").strip().lower()
        self._providers.pop(key, None)
        return self.registry.unregister(key)

    def list_providers(self):
        return list(self.registry.list_capabilities(enabled_only=True))

    def execute(self, action: Dict[str, Any]) -> Dict[str, Any]:
        validation = self.validator.validate_action(action)
        if not validation.get("valid", False):
            return {
                "success": False,
                "stage": "action_validation_failed",
                "message": validation.get("error", "Invalid action."),
            }

        normalized = validation["action"]
        resolution = self.resolver.resolve(normalized)

        if not resolution.get("resolved", False):
            return {
                "success": False,
                "stage": "capability_resolution_failed",
                "message": resolution.get(
                    "reason", "No capability provider is available."
                ),
                "action": normalized,
                "resolution": resolution,
            }

        capability = str(resolution.get("capability") or "").strip().lower()
        provider = self._providers.get(capability)
        if provider is None:
            return {
                "success": False,
                "stage": "capability_runtime_missing",
                "message": (
                    f"Capability '{capability}' is registered but no runtime provider is bound."
                ),
                "action": normalized,
                "resolution": resolution,
            }

        execute = getattr(provider, "execute", None)
        if not callable(execute):
            return {
                "success": False,
                "stage": "capability_provider_invalid",
                "message": f"Capability provider '{capability}' has no execute method.",
                "action": normalized,
            }

        try:
            result = execute(normalized)
        except Exception as error:
            return {
                "success": False,
                "stage": "capability_execution_error",
                "message": str(error),
                "action": normalized,
                "capability": capability,
            }

        if isinstance(result, dict):
            result = dict(result)
            result.setdefault("action", normalized)
            result.setdefault("capability", capability)
            return result

        return {
            "success": bool(result),
            "stage": "capability_executed" if result else "capability_execution_failed",
            "result": result,
            "action": normalized,
            "capability": capability,
        }
