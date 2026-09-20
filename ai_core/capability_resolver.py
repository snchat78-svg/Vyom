"""
Project : Vyom AI
Version : 1.0
Module  : Capability Resolver

Purpose:
    Resolve a generic action to an advertised capability provider.

This layer performs selection only. It never executes actions.
"""

from typing import Any, Dict, Optional

from ai_core.capability_registry import CapabilityRegistry


class CapabilityResolver:

    def __init__(self, registry: Optional[CapabilityRegistry] = None):
        self.registry = registry or CapabilityRegistry()

    def resolve(self, action: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(action, dict):
            return {
                "resolved": False,
                "stage": "invalid_action",
                "reason": "Action must be an object.",
            }

        action_name = str(action.get("action") or "").strip().lower()
        capability = str(action.get("capability") or "").strip().lower()

        if not action_name:
            return {
                "resolved": False,
                "stage": "invalid_action",
                "reason": "Action name is missing.",
            }

        if capability:
            provider = self.registry.get(capability)
            if not provider:
                return {
                    "resolved": False,
                    "stage": "missing_capability",
                    "reason": f"Capability '{capability}' is not registered.",
                    "action": action_name,
                    "capability": capability,
                }
            if not provider.get("enabled", False):
                return {
                    "resolved": False,
                    "stage": "capability_disabled",
                    "reason": f"Capability '{capability}' is disabled.",
                    "action": action_name,
                    "capability": capability,
                }
            if action_name not in set(provider.get("actions", [])):
                return {
                    "resolved": False,
                    "stage": "unsupported_action",
                    "reason": (
                        f"Capability '{capability}' does not advertise action '{action_name}'."
                    ),
                    "action": action_name,
                    "capability": capability,
                    "provider": provider,
                }
            return {
                "resolved": True,
                "stage": "capability_resolved",
                "action": action_name,
                "capability": capability,
                "provider": provider,
            }

        providers = self.registry.providers_for_action(action_name)
        if not providers:
            return {
                "resolved": False,
                "stage": "missing_capability",
                "reason": f"No enabled capability advertises action '{action_name}'.",
                "action": action_name,
            }

        provider = providers[0]
        return {
            "resolved": True,
            "stage": "capability_resolved",
            "action": action_name,
            "capability": provider["name"],
            "provider": provider,
        }
