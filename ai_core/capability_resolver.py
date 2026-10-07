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
                # Models may preserve a legacy or semantically related
                # capability label while still selecting a valid generic
                # action. If exactly one enabled provider advertises that
                # action, correct the provider at the resolver boundary rather
                # than turning a safe executable action into a false
                # "missing capability" result.
                alternatives = self.registry.providers_for_action(action_name)
                if len(alternatives) == 1:
                    corrected = alternatives[0]
                    return {
                        "resolved": True,
                        "stage": "capability_resolved_with_correction",
                        "action": action_name,
                        "capability": corrected["name"],
                        "requested_capability": capability,
                        "provider": corrected,
                    }
                return {
                    "resolved": False,
                    "stage": "unsupported_action",
                    "reason": (
                        f"Capability '{capability}' does not advertise action '{action_name}', "
                        "and no unique enabled provider can safely correct it."
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
