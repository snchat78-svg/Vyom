"""
Project : Vyom AI
Version : 1.0
Module  : Capability Registry

Purpose:
    Provider metadata registry for generic actions.

Design:
    A capability advertises which generic actions it can support. The
    registry never stores model-produced executable code or callables.
"""

from typing import Any, Dict, Iterable, List, Optional, Set

from ai_core.action_schema import validate_identifier


class CapabilityRegistry:

    def __init__(self):
        self._capabilities: Dict[str, Dict[str, Any]] = {}

    def register(
        self,
        name: str,
        description: str = "",
        actions: Optional[Iterable[str]] = None,
        enabled: bool = True,
        priority: int = 100,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        try:
            normalized_name = validate_identifier(name, "capability")
        except Exception:
            return False

        normalized_actions: Set[str] = set()
        for action in actions or []:
            try:
                normalized_actions.add(validate_identifier(action, "action"))
            except Exception:
                return False

        safe_metadata = {}
        if isinstance(metadata, dict):
            for key, value in metadata.items():
                if isinstance(value, (str, int, float, bool)) or value is None:
                    safe_metadata[str(key)] = value

        self._capabilities[normalized_name] = {
            "name": normalized_name,
            "description": str(description or "").strip(),
            "actions": sorted(normalized_actions),
            "enabled": bool(enabled),
            "priority": int(priority),
            "metadata": safe_metadata,
        }
        return True

    def unregister(self, name: str) -> bool:
        key = str(name or "").strip().lower()
        if key not in self._capabilities:
            return False
        del self._capabilities[key]
        return True

    def get(self, name: str) -> Optional[Dict[str, Any]]:
        key = str(name or "").strip().lower()
        value = self._capabilities.get(key)
        return dict(value) if isinstance(value, dict) else None

    def list_capabilities(self, enabled_only: bool = False) -> List[Dict[str, Any]]:
        values = []
        for item in self._capabilities.values():
            if enabled_only and not item.get("enabled", False):
                continue
            values.append(dict(item))
        values.sort(key=lambda item: (item.get("priority", 100), item.get("name", "")))
        return values

    def supports(self, capability: str, action: str) -> bool:
        item = self.get(capability)
        if not item or not item.get("enabled", False):
            return False
        return str(action or "").strip().lower() in set(item.get("actions", []))

    def providers_for_action(self, action: str, enabled_only: bool = True) -> List[Dict[str, Any]]:
        wanted = str(action or "").strip().lower()
        if not wanted:
            return []
        providers = []
        for item in self.list_capabilities(enabled_only=enabled_only):
            if wanted in set(item.get("actions", [])):
                providers.append(item)
        return providers

